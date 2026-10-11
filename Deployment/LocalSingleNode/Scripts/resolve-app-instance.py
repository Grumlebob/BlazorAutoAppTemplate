"""Resolve protected application configuration before release download or node mutation."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import sys

LIB = Path(__file__).resolve().parent / "lib"
sys.path.insert(0, str(LIB))
from ls_settings import ETC, ROOT, TARGET, settings

sys.path.insert(0, str(ROOT / "Scripts/Frontend"))
from resolve_frontend_profile import acceptance_profile_for_frontend
sys.path.insert(0, str(ROOT / "Deployment/Common/Scripts/Component/lib"))
from release_settings import load_release_settings


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate instance configuration key")
        result[key] = value
    return result


def validate_additional(config: dict, primary: dict, selected_profile: str) -> tuple[dict, str, dict]:
    if not isinstance(config, dict) or set(config) != {"schema_version", "frontend_profile", "settings", "public"}:
        raise ValueError("instance configuration keys differ from schema")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("unsupported instance schema")
    profile = config["frontend_profile"]
    acceptance_profile_for_frontend(profile)
    if profile == selected_profile:
        raise ValueError("additional instance must use the other frontend")
    candidate = config["settings"]
    if not isinstance(candidate, dict) or set(candidate) != set(primary):
        raise ValueError("instance settings keys differ from primary schema")
    # Validate with the ordinary production parser; JSON literals are scalar YAML values.
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "settings.yml"
        path.write_text(settings_yaml(candidate), encoding="utf-8")
        candidate = settings(path)
    if candidate["app_name"] == primary["app_name"]:
        raise ValueError("additional app must have a distinct identity")
    roots = [Path(item[key]) for item in (primary, candidate) for key in ("deploy_root", "backup_root")]
    for index, root in enumerate(roots):
        for other in roots[index + 1:]:
            if root == other or root in other.parents or other in root.parents:
                raise ValueError("application and backup roots must be disjoint")
    port_keys = ("app_port", "postgres_port", "redis_port", "lan_http_port")
    if {primary[key] for key in port_keys} & {candidate[key] for key in port_keys}:
        raise ValueError("additional service ports overlap the primary app")
    if ipaddress.ip_network(primary["docker_subnet"]).overlaps(ipaddress.ip_network(candidate["docker_subnet"])):
        raise ValueError("additional subnet overlaps the primary app")
    if {name.casefold() for name in primary["lan_hostnames"]} & {name.casefold() for name in candidate["lan_hostnames"]}:
        raise ValueError("additional LAN names overlap the primary app")
    public = config["public"]
    if not isinstance(public, dict) or (public and set(public) != {"hostname", "tunnel_id", "origin_port"}):
        raise ValueError("instance public configuration keys differ from schema")
    if public:
        # Token/account binding remains the existing public_config validator's responsibility.
        import uuid
        hostname = public["hostname"]
        if not isinstance(hostname, str) or len(hostname) > 253 or hostname != hostname.lower() or "." not in hostname:
            raise ValueError("invalid instance public hostname")
        if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in hostname.split(".")):
            raise ValueError("invalid instance public hostname")
        if str(uuid.UUID(public["tunnel_id"])) != public["tunnel_id"]:
            raise ValueError("invalid instance tunnel identity")
        port = public["origin_port"]
        if type(port) is not int or not 1024 <= port <= 65535 or port in {item[key] for item in (primary, candidate) for key in port_keys}:
            raise ValueError("invalid or colliding instance public origin port")
    return candidate, profile, public


def settings_yaml(values: dict) -> str:
    return "".join(f"{key}: {json.dumps(value)}\n" for key, value in values.items())


def write_private(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(content)


def verify_owned(config: dict, source: str, etc: Path = ETC) -> None:
    marker = etc / f"localsinglenode/apps/{config['app_name']}.json"
    for path in (marker.parent, marker):
        identity = path.lstat()
        if stat.S_ISLNK(identity.st_mode) or identity.st_uid != 0 or identity.st_mode & 0o022:
            raise ValueError("application ownership marker must be protected and root-owned")
    if not marker.is_file():
        raise ValueError("application ownership marker must be a regular file")
    recorded = json.loads(marker.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if (not isinstance(recorded, dict) or not isinstance(recorded.get("source_repo_url"), str)
            or recorded["source_repo_url"].casefold() != source.casefold()
            or recorded.get("deploy_root") != config["deploy_root"]
            or recorded.get("backup_root") != config["backup_root"]):
        raise ValueError("application ownership marker does not match the selected instance")


def mask(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in {"schema_version", "frontend_profile", "backup_keep_days", "observability_enabled"}:
                mask(item)
    elif isinstance(value, list):
        for item in value:
            mask(item)
    elif type(value) in (str, int) and str(value):
        escaped = str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::add-mask::{escaped}")


def resolve(instance: str, payload: str, selected_profile: str, selected_acceptance: str,
            release: dict, primary: dict, temporary: Path) -> dict[str, str]:
    if acceptance_profile_for_frontend(selected_profile) != selected_acceptance:
        raise ValueError("selected frontend and acceptance profile disagree")
    if instance not in ("primary", "additional"):
        raise ValueError("unknown application instance")
    config, profile, public = primary, selected_profile, {}
    if instance == "additional":
        config, profile, public = validate_additional(json.loads(payload, object_pairs_hook=unique_object), primary, selected_profile)
    suffix = "" if instance == "primary" else "-" + profile.lower()
    image = release["app_image"] + suffix
    extra = {**config, "app_image": image}
    values = {
        "APP_INSTANCE": instance, "APP_NAME": config["app_name"], "APP_IMAGE": image,
        "MIGRATION_BUNDLE_NAME": release["migration_bundle_name"],
        "MIGRATION_ARTIFACT_NAME": release["migration_artifact_name"] + suffix,
        "FRONTEND_PROFILE": profile, "ACCEPTANCE_PROFILE": acceptance_profile_for_frontend(profile),
        "INSTANCE_EXTRA_VARS_FILE": str(temporary / "instance-vars.json"),
        "LOCALSINGLENODE_SETTINGS_FILE": "",
    }
    if instance == "additional":
        path = temporary / "instance-settings.yml"
        write_private(path, settings_yaml(config))
        extra["instance_settings_file"] = str(path)
        values.update(LOCALSINGLENODE_SETTINGS_FILE=str(path),
                      INSTANCE_PUBLIC_HOSTNAME=public.get("hostname", ""),
                      INSTANCE_PUBLIC_TUNNEL_ID=public.get("tunnel_id", ""),
                      INSTANCE_PUBLIC_ORIGIN_PORT=str(public.get("origin_port", "")))
    write_private(Path(values["INSTANCE_EXTRA_VARS_FILE"]), json.dumps(extra) + "\n")
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-additional", action="store_true",
                        help="validate a new additional instance while requiring the primary app's native ownership")
    args = parser.parse_args(argv)
    try:
        instance = os.environ.get("INPUT_APP_INSTANCE", "primary")
        if args.prepare_additional and instance != "additional":
            raise ValueError("existing-node preparation is only for an additional app")
        if instance == "additional":
            additional_environment = os.environ.get("ADDITIONAL_INSTANCE_ENVIRONMENT", "")
            primary_environment = os.environ.get("PRIMARY_INSTANCE_ENVIRONMENT", "") or "localsinglenode"
            if not additional_environment or additional_environment.casefold() == primary_environment.casefold():
                raise ValueError("additional instance requires its own protected GitHub environment")
        payload = os.environ.get("APP_INSTANCE_CONFIG", "")
        if instance == "additional":
            mask(json.loads(payload, object_pairs_hook=unique_object))
        values = resolve(instance, payload, os.environ["FRONTEND_PROFILE"], os.environ["ACCEPTANCE_PROFILE"],
                         load_release_settings(ROOT / "Deployment/Common/release.yml"),
                         settings(TARGET / "inventory/group_vars/all.yml"), Path(os.environ["RUNNER_TEMP"]))
        config = json.loads(Path(values["INSTANCE_EXTRA_VARS_FILE"]).read_text(encoding="utf-8"))
        source = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
        primary = settings(TARGET / "inventory/group_vars/all.yml")
        verify_owned(primary if args.prepare_additional else config, source)
        if args.prepare_additional:
            values["READINESS_CANDIDATE"] = json.dumps({
                "expected_host": os.environ["LOCALSINGLENODE_HOST"],
                "source_repo_url": source,
                "settings_yaml": Path(values["LOCALSINGLENODE_SETTINGS_FILE"]).read_text(encoding="utf-8"),
            })
        with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as output:
            for key, value in values.items():
                output.write(f"{key}={value}\n")
        print("Application instance and release identities validated.")
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, SyntaxError):
        print("Invalid application instance configuration or unsafe output; no configuration was printed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
