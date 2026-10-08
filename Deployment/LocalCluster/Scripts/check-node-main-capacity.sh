#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/localcluster-capacity-thresholds.sh"
# Capture separately: read/here-string would hide a failing df command.
if ! free_mb="$(df -Pm /opt | awk 'NR == 2 {print $4}')" \
  || ! inode_counts="$(df -Pi /opt | awk 'NR == 2 {print $2, $4}')"; then
  echo "Cannot query /opt byte/inode capacity; refusing to guess." >&2
  exit 1
fi
read -r total_inodes free_inodes <<< "$inode_counts"
if [[ ! "$free_mb" =~ ^[0-9]+$ || ! "$total_inodes" =~ ^[0-9]+$ || ! "$free_inodes" =~ ^[0-9]+$ ]] \
  || (( total_inodes == 0 || free_inodes > total_inodes )); then
  echo "Cannot establish /opt byte/inode capacity; refusing to guess." >&2
  exit 1
fi
free_inode_percent=$((free_inodes * 100 / total_inodes))
echo "/opt capacity: free_mb=$free_mb free_inode_percent=$free_inode_percent"
if (( free_mb < LOCALCLUSTER_LOAD_BALANCER_MIN_FREE_MB \
  || free_inode_percent < LOCALCLUSTER_LOAD_BALANCER_MIN_FREE_INODE_PERCENT )); then
  echo "Required /opt reserve: ${LOCALCLUSTER_LOAD_BALANCER_MIN_FREE_MB}MiB and ${LOCALCLUSTER_LOAD_BALANCER_MIN_FREE_INODE_PERCENT}% free inodes." >&2
  exit 2
fi
