#!/usr/bin/env bash
set -euo pipefail

echo "hostname:"
hostname
echo

echo "addresses:"
ip -brief address
echo

echo "default route source address:"
ip route get 1.1.1.1
echo

echo "interfaces and MAC addresses:"
ip link show
