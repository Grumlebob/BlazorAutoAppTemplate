#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python3 -m unittest test_single_node.MachineTests.test_inventory_exact test_single_node.MachineTests.test_detect_and_preserve_install_user
