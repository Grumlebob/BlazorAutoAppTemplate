#!/usr/bin/env bash
set -euo pipefail

actionlint_commit="644076a59742c2d1540ebd4686eab3c308f0e562"
temp_root="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/workflow-actionlint.XXXXXX")"
trap 'rm -rf -- "$temp_root"' EXIT

actionlint_source="$temp_root/source"
actionlint_bin="$actionlint_source/actionlint"

git clone --filter=blob:none --no-checkout --depth=1 https://github.com/rhysd/actionlint.git "$actionlint_source"
git -C "$actionlint_source" fetch --depth=1 origin "$actionlint_commit"
git -C "$actionlint_source" checkout --detach "$actionlint_commit"
test "$(git -C "$actionlint_source" rev-parse HEAD)" = "$actionlint_commit"

if command -v go >/dev/null 2>&1; then
  (cd "$actionlint_source" && go build -o "$actionlint_bin" ./cmd/actionlint)
else
  docker run --rm --volume "$actionlint_source:/source" --workdir /source golang:1.27.1 \
    go build -buildvcs=false -o /source/actionlint ./cmd/actionlint
fi
"$actionlint_bin" -color
bash Scripts/CI/tests/test-actionlint-queue.sh "$actionlint_bin"
