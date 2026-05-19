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

sudo hostnamectl set-hostname "$NODE_NAME"
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh

sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

echo
echo "node bootstrap complete"
echo "username: $(whoami)"
echo "hostname: $(hostname)"
echo
echo "addresses:"
ip -brief address
echo
echo "default route probe:"
ip route get 1.1.1.1
echo
echo "network interfaces and MAC addresses:"
ip -brief link
