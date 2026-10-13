# SSH Host Trust

Use this procedure when a controller must add a scanned SSH host key to `known_hosts`, including manual LocalCluster and Cloud access. `ssh-keyscan` obtains a candidate key; it does not prove the host's identity. LocalSingleNode uses its authenticated node record; see [Controller SSH](../LocalSingleNode/ControllerSsh.md). [Cloud CD](../../.github/workflows/cd-cloud.yml) currently appends scanned bastion keys on its persistent self-hosted runner without independent fingerprint verification; that workflow does not provide this trust check.

On the control machine, scan the host and print the candidate fingerprint. Keep this terminal open while you check the host console; the exit trap deletes the candidate key.

```bash
set -euo pipefail
host_key_candidate="$(mktemp)"
trap 'rm -f "$host_key_candidate"' EXIT
host="replace-with-hostname-or-ip"
ssh-keyscan -T 10 -t ed25519 -H "$host" > "$host_key_candidate"
test -s "$host_key_candidate"
ssh-keygen -lf "$host_key_candidate"
```

Independently read the Ed25519 host-key fingerprint from the host's own console:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

If the fingerprints differ, stop and do not change `known_hosts`. Append the same scanned key only after the fingerprints match. Skip a host that already has the verified key. Do not remove a changed host key to bypass a mismatch; verify an intentional replacement through the host's own console first.

```bash
mkdir -p ~/.ssh
cat "$host_key_candidate" >> ~/.ssh/known_hosts
```
