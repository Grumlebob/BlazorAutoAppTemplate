#!/usr/bin/env bash
set -euo pipefail

echo "Run this script on each fresh Linux Mint node."
echo

echo "username:"
whoami
echo

echo "hostname:"
hostname
echo

echo "default route:"
ip route get 1.1.1.1
echo

DEFAULT_IFACE="$(ip route get 1.1.1.1 | awk '{for (i=1; i<=NF; i++) if ($i == "dev") {print $(i+1); exit}}')"
DEFAULT_IP="$(ip route get 1.1.1.1 | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}')"

echo "likely LAN interface:"
echo "${DEFAULT_IFACE:-unknown}"
echo

echo "likely LAN IP:"
echo "${DEFAULT_IP:-unknown}"
echo

echo "likely LAN MAC:"
if [[ -n "${DEFAULT_IFACE:-}" && -r "/sys/class/net/$DEFAULT_IFACE/address" ]]; then
  cat "/sys/class/net/$DEFAULT_IFACE/address"
else
  echo "unknown"
fi
echo

echo "all addresses:"
ip -brief address
echo

echo "all interfaces and MAC addresses:"
ip link show
