#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python3 -m unittest test_single_node.MachineTests.test_valid test_single_node.MachineTests.test_reject_bad_facts test_single_node.MachineTests.test_hostname_guard
