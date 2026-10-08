#!/usr/bin/env bash
# Report-only capacity gate for the self-hosted CI runner on node-main.
# node-main's Docker daemon and disks are shared with other apps, so CI never
# prunes here. When space is low it fails with guidance; an operator runs the
# scoped maintenance described in Deployment/LocalCluster/HowToDeployLocalCluster.md.
set -euo pipefail

capacity_status=0
bash Deployment/LocalCluster/Scripts/check-node-main-capacity.sh || capacity_status=$?
case "$capacity_status" in
  0) ;;
  2)
    echo "::error::node-main is below its /opt capacity reserve. Inspect with 'bash Deployment/LocalCluster/Scripts/prune-docker-residue.sh --dry-run' on node-main, then run a reviewed, scoped cleanup. CI does not prune shared hosts." >&2
    docker system df || true
    exit 2
    ;;
  *) exit "$capacity_status" ;;
esac
df -h /opt
df -Pi /opt
