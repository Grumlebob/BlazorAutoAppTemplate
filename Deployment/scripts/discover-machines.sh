#!/usr/bin/env bash
set -euo pipefail

DEFAULT_ROUTE="$(ip route get 1.1.1.1 2>/dev/null || true)"
if [[ -z "$DEFAULT_ROUTE" ]]; then
  echo "discover-machines failed: could not detect the default LAN route." >&2
  echo "Connect the node to the LAN, confirm internet access, then rerun this script." >&2
  exit 1
fi

LAN_IP="$(awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}' <<< "$DEFAULT_ROUTE")"
LAN_IFACE="$(awk '{for (i=1; i<=NF; i++) if ($i == "dev") {print $(i+1); exit}}' <<< "$DEFAULT_ROUTE")"
LAN_MAC=""

if [[ -n "$LAN_IFACE" && -r "/sys/class/net/$LAN_IFACE/address" ]]; then
  LAN_MAC="$(cat "/sys/class/net/$LAN_IFACE/address")"
fi

if [[ -z "$LAN_IP" ]]; then
  echo "discover-machines failed: could not detect this node's LAN IP address." >&2
  echo "Run 'ip -brief address' and check the active network interface before rerunning." >&2
  exit 1
fi

if [[ -z "$LAN_MAC" ]]; then
  echo "discover-machines failed: could not detect the MAC address for interface '$LAN_IFACE'." >&2
  echo "Run 'cat /sys/class/net/<interface>/address' for the active LAN interface before rerunning." >&2
  exit 1
fi

echo "username: $(whoami)"
echo "hostname: $(hostname)"
echo "lan_ip: $LAN_IP"
echo "lan_mac: $LAN_MAC"
