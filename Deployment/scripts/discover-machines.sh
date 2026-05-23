#!/usr/bin/env bash
set -euo pipefail

DEFAULT_IFACE="$(ip route get 1.1.1.1 | awk '{for (i=1; i<=NF; i++) if ($i == "dev") {print $(i+1); exit}}')"
DEFAULT_IP="$(ip route get 1.1.1.1 | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}')"
DEFAULT_MAC=""

if [[ -n "${DEFAULT_IFACE:-}" && -r "/sys/class/net/$DEFAULT_IFACE/address" ]]; then
  DEFAULT_MAC="$(cat "/sys/class/net/$DEFAULT_IFACE/address")"
fi

echo "username: $(whoami)"
echo "hostname: $(hostname)"
echo "lan_ip: ${DEFAULT_IP:-unknown}"
echo "lan_mac: ${DEFAULT_MAC:-unknown}"
