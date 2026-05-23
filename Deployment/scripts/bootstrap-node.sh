#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <node-main|node-app1|node-app2|node-db>" >&2
  exit 1
}

[[ $# -eq 1 ]] || usage
NODE_NAME="$1"

case "$NODE_NAME" in
  node-main|node-app1|node-app2|node-db) ;;
  *) usage ;;
esac

package_installed() {
  dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "install ok installed"
}

target_masked() {
  [[ "$(systemctl is-enabled "$1" 2>/dev/null || true)" == "masked" ]]
}

if [[ "$(hostname)" != "$NODE_NAME" ]]; then
  sudo hostnamectl set-hostname "$NODE_NAME" >/dev/null
fi

if ! package_installed openssh-server; then
  sudo apt-get update -qq >/dev/null
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openssh-server >/dev/null
fi

if ! systemctl is-enabled --quiet ssh; then
  sudo systemctl enable ssh >/dev/null
fi

if ! systemctl is-active --quiet ssh; then
  sudo systemctl start ssh >/dev/null
fi

for target in sleep.target suspend.target hibernate.target hybrid-sleep.target; do
  if ! target_masked "$target"; then
    sudo systemctl mask "$target" >/dev/null
  fi
done

DEFAULT_ROUTE="$(ip route get 1.1.1.1)"
LAN_IP="$(awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}' <<< "$DEFAULT_ROUTE")"
LAN_IFACE="$(awk '{for (i=1; i<=NF; i++) if ($i == "dev") {print $(i+1); exit}}' <<< "$DEFAULT_ROUTE")"
LAN_MAC=""

if [[ -n "$LAN_IFACE" && -r "/sys/class/net/$LAN_IFACE/address" ]]; then
  LAN_MAC="$(cat "/sys/class/net/$LAN_IFACE/address")"
fi

[[ -n "$LAN_IP" ]] || LAN_IP="unknown"
[[ -n "$LAN_MAC" ]] || LAN_MAC="unknown"

echo "username: $(whoami)"
echo "hostname: $(hostname)"
echo "lan_ip: $LAN_IP"
echo "lan_mac: $LAN_MAC"
