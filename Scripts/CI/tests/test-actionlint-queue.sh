#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -x "$1" ]]; then
  echo "usage: test-actionlint-queue.sh <actionlint-executable>" >&2
  exit 2
fi

actionlint_bin="$(realpath "$1")"
fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/workflow-actionlint-queue.XXXXXX")"
trap 'rm -rf -- "$fixture_root"' EXIT

cat > "$fixture_root/valid.yml" <<'YAML'
name: queued deployment
on:
  workflow_dispatch:
concurrency:
  group: deploy
  queue: max
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: true
YAML

cat > "$fixture_root/invalid-value.yml" <<'YAML'
name: invalid queue value
on:
  workflow_dispatch:
concurrency:
  group: deploy
  queue: forever
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: true
YAML

cat > "$fixture_root/invalid-cancel.yml" <<'YAML'
name: invalid cancel and queue combination
on:
  workflow_dispatch:
concurrency:
  group: deploy
  queue: max
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: true
YAML

"$actionlint_bin" "$fixture_root/valid.yml"
if "$actionlint_bin" "$fixture_root/invalid-value.yml"; then
  echo "actionlint accepted an unsupported queue value" >&2
  exit 1
fi
if "$actionlint_bin" "$fixture_root/invalid-cancel.yml"; then
  echo "actionlint accepted queue: max with cancel-in-progress: true" >&2
  exit 1
fi

echo "actionlint queue fixtures passed"
