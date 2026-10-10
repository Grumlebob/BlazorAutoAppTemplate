"""Create or check one owned public tunnel without exposing credentials."""
from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

API_ROOT = "https://api.cloudflare.com/client/v4"


def hostname(value):
    if not isinstance(value, str) or len(value) > 253 or value != value.lower():
        raise ValueError("Use a lowercase public DNS hostname")
    labels = value.split(".")
    if len(labels) < 2 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", item) for item in labels):
        raise ValueError("Invalid public DNS hostname")
    return value


def validate_config(config):
    expected = {"account_id", "zone_name", "tunnel_name", "public_hostname", "origin_port"}
    if not isinstance(config, dict) or set(config) != expected:
        raise ValueError("Cloudflare config has missing or unknown keys")
    if not re.fullmatch(r"[0-9a-f]{32}", str(config["account_id"])):
        raise ValueError("Invalid Cloudflare account ID")
    zone = hostname(config["zone_name"])
    site = hostname(config["public_hostname"])
    if not site.endswith("." + zone):
        raise ValueError("Public hostname must be a subdomain of the configured zone")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", str(config["tunnel_name"])):
        raise ValueError("Tunnel name must be a lowercase slug")
    if type(config["origin_port"]) is not int or not 1024 <= config["origin_port"] <= 65535:
        raise ValueError("Origin port must be an integer from 1024 through 65535")
    return config


def protected_read(path):
    flags = os.O_RDONLY | os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Credential/state files must be owned by the current user with mode 0600")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = None
            return handle.read()
    finally:
        if descriptor is not None:
            os.close(descriptor)


def private_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Refusing symlink credential/state output")
    if path.exists():
        protected_read(path)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Cloudflare API redirects are refused")


class Api:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, path, body=None, allow_missing=False):
        request = urllib.request.Request(
            API_ROOT + path, method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                envelope = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404 and allow_missing:
                return {"result": None}
            # Responses can include submitted values. Never print response bodies.
            raise ValueError(f"Cloudflare API returned HTTP {error.code}; request outcome may be uncertain") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            raise ValueError("Cloudflare API request failed; request outcome may be uncertain") from None
        if not isinstance(envelope, dict) or envelope.get("success") is not True:
            raise ValueError("Cloudflare API rejected the request; inspect account permissions")
        return envelope

    def get(self, path, allow_missing=False):
        return self.request("GET", path, allow_missing=allow_missing)["result"]

    def listing(self, path, filters=None):
        result = []
        for page in range(1, 10001):
            query = urllib.parse.urlencode({**(filters or {}), "page": page, "per_page": 100})
            envelope = self.request("GET", path + "?" + query)
            items = envelope.get("result")
            if not isinstance(items, list):
                raise ValueError("Unexpected Cloudflare list response")
            result.extend(items)
            pages = envelope.get("result_info", {}).get("total_pages")
            if (pages is not None and page >= pages) or (pages is None and len(items) < 100):
                return result
        raise ValueError("Cloudflare pagination exceeded the safe limit")


class Provisioner:
    def __init__(self, api, config, state_path):
        self.api = api
        self.config = validate_config(config)
        self.path = Path(state_path)
        self.identity = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        self.state = json.loads(protected_read(self.path)) if self.path.exists() or self.path.is_symlink() else {}
        if self.state and self.state.get("identity") != self.identity:
            raise ValueError("Ownership state belongs to different configuration; use a separate state file")

    def save(self, **values):
        self.state.update(identity=self.identity, **values)
        private_write(self.path, json.dumps(self.state, sort_keys=True) + "\n")

    def reconcile(self, apply=False, token_output=None):
        c = self.config
        zones = self.api.listing("/zones", {"name": c["zone_name"], "account.id": c["account_id"]})
        if len(zones) != 1 or zones[0].get("status") != "active":
            raise ValueError("Exactly one active zone in the configured account is required")
        zone = zones[0]
        zone_id = zone["id"]
        if not re.fullmatch(r"[0-9a-f]{32}", zone_id) or zone.get("account", {}).get("id") != c["account_id"]:
            raise ValueError("Zone identity does not match the configured account")
        tunnel_base = f'/accounts/{c["account_id"]}/cfd_tunnel'
        dns_base = f"/zones/{zone_id}/dns_records"
        tunnels = self.api.listing(tunnel_base, {"name": c["tunnel_name"], "is_deleted": "false"})
        tunnels = [item for item in tunnels if item.get("name") == c["tunnel_name"] and not item.get("deleted_at")]
        records = self.api.listing(dns_base, {"name": c["public_hostname"]})
        if any(item.get("name") != c["public_hostname"] for item in records) or len(records) > 1:
            raise ValueError("Unexpected or multiple DNS records at the requested hostname")
        tunnel_id = self.state.get("tunnel_id")
        if not tunnel_id:
            if tunnels:
                raise ValueError("Tunnel name exists without recorded ownership; inspect it, do not adopt automatically")
            if records:
                raise ValueError("DNS hostname already exists without recorded ownership")
            if self.state.get("pending") == "create-tunnel":
                raise ValueError("Tunnel creation outcome is uncertain; inspect the account before clearing the pending state")
            if not apply:
                raise ValueError("Tunnel and DNS are not provisioned")
            self.save(zone_id=zone_id, pending="create-tunnel")
            tunnel = self.api.request("POST", tunnel_base, {
                "name": c["tunnel_name"], "config_src": "cloudflare",
                "tunnel_secret": base64.b64encode(os.urandom(32)).decode(),
            })["result"]
            tunnel_id = str(uuid.UUID(tunnel["id"]))
            self.save(tunnel_id=tunnel_id, pending=None)
            tunnels = [tunnel]
        if len(tunnels) != 1 or tunnels[0].get("id") != tunnel_id:
            raise ValueError("Recorded tunnel ownership does not match account inventory")
        if tunnels[0].get("config_src") == "local" or tunnels[0].get("remote_config") is False:
            raise ValueError("The owned tunnel must be remotely managed")
        desired = {"ingress": [
            {"hostname": c["public_hostname"], "service": f'http://127.0.0.1:{c["origin_port"]}'},
            {"service": "http_status:404"},
        ]}
        current_result = self.api.get(tunnel_base + "/" + tunnel_id + "/configurations", allow_missing=True)
        current = current_result.get("config", {}) if isinstance(current_result, dict) else {}
        # Cloudflare adds empty defaults when returning remotely managed configuration.
        current = {key: value for key, value in current.items()
                   if not (key == "originRequest" and value == {})
                   and not (key == "warp-routing" and value in ({}, {"enabled": False}))}
        for entry in current.get("ingress", []):
            if entry.get("originRequest") == {}:
                entry.pop("originRequest")
        entries = current.get("ingress", [])
        for entry in entries:
            if entry not in desired["ingress"]:
                raise ValueError("Owned tunnel has conflicting ingress; preserve it and inspect before proceeding")
        if any(key != "ingress" for key in current):
            raise ValueError("Tunnel has extra settings; preserve them and inspect before proceeding")
        if current != desired:
            if not apply:
                raise ValueError("Tunnel ingress differs from the requested configuration")
            self.save(pending="configure-tunnel")
            self.api.request("PUT", tunnel_base + "/" + tunnel_id + "/configurations", {"config": desired})
            self.save(pending=None)
        target = tunnel_id + ".cfargotunnel.com"
        record = records[0] if records else None
        desired_dns = {"type": "CNAME", "name": c["public_hostname"], "content": target, "proxied": True, "ttl": 1}
        if record:
            if (record.get("type") != "CNAME" or record.get("content") != target
                    or record.get("proxied") is not True):
                raise ValueError("DNS hostname conflicts with the owned tunnel; replacement is refused")
            if not self.state.get("dns_id") and self.state.get("pending") != "create-dns":
                raise ValueError("DNS record has no recorded ownership")
            if self.state.get("dns_id") and self.state["dns_id"] != record["id"]:
                raise ValueError("DNS record ID changed; inspect ownership")
            if apply:
                self.save(dns_id=record["id"], pending=None)
        else:
            if self.state.get("dns_id") or self.state.get("pending") == "create-dns":
                raise ValueError("Owned DNS record is missing or creation is uncertain; inspect before proceeding")
            if not apply:
                raise ValueError("Public DNS record is missing")
            self.save(pending="create-dns")
            record = self.api.request("POST", dns_base, desired_dns)["result"]
            self.save(dns_id=record["id"], pending=None)
        if apply and token_output:
            token = self.api.get(tunnel_base + "/" + tunnel_id + "/token")
            if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9+/=_-]+", token) or len(token) < 32:
                raise ValueError("Invalid connector token response")
            private_write(token_output, token + "\n")
        return {"account_id": c["account_id"], "zone_id": zone_id, "tunnel_id": tunnel_id,
                "dns_id": record["id"], "hostname": c["public_hostname"],
                "origin": desired["ingress"][0]["service"], "tunnel_status": tunnels[0].get("status", "unknown")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--connector-token-file", type=Path)
    parser.add_argument("--apply", action="store_true", help="Create only resources owned by this configuration")
    args = parser.parse_args(argv)
    try:
        if args.apply and not args.connector_token_file:
            raise ValueError("--apply requires a protected --connector-token-file output")
        paths = [args.config, args.token_file, args.state, args.connector_token_file]
        paths = [item.absolute() for item in paths if item]
        if len(set(paths)) != len(paths):
            raise ValueError("Configuration, credentials and state must use distinct files")
        config = validate_config(json.loads(args.config.read_text()))
        token = protected_read(args.token_file).strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,}", token):
            raise ValueError("Invalid API token file")
        args.state.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_path = args.state.with_name(args.state.name + ".lock")
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = Provisioner(Api(token), config, args.state).reconcile(args.apply, args.connector_token_file)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        # No exception dumps: a malformed API response or credential file can contain secrets.
        print("Cloudflare setup failed; configuration, credentials, ownership or API state needs inspection.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
