#!/usr/bin/env bash
set -euo pipefail

# Called inside the deployment lock before retrieving a release. An existing
# native controller can lack this app's directory until its first modern release.
root="${1:?usage: prepare-release-pin-root.sh <configured-deploy-root>}"
[[ "$root" == /* && "$root" != / && "$root" == "$(realpath -m -- "$root")" ]] || {
  echo "Release pin deployment root must be an absolute canonical path without symlinks." >&2
  exit 1
}

if [[ ! -e "$root" ]]; then
  sudo -n install -d -o "$(id -un)" -g "$(id -gn)" -m 0750 -- "$root"
fi

[[ -d "$root" && ! -L "$root" && -w "$root" && -x "$root" && "$(stat -c %u -- "$root")" == "$(id -u)" ]] || {
  echo "Release pin deployment root is not an owned writable directory; existing ownership was preserved." >&2
  exit 1
}
