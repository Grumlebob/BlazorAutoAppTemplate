#!/usr/bin/env bash

# Shared disk thresholds used by deploy preflight and preflight cleanup.
# shellcheck disable=SC2034
LOCALCLUSTER_LOAD_BALANCER_MIN_FREE_MB="20480"
# shellcheck disable=SC2034
LOCALCLUSTER_LOAD_BALANCER_MIN_FREE_INODE_PERCENT="5"
# shellcheck disable=SC2034
LOCALCLUSTER_APP_SERVERS_MIN_FREE_MB="2048"
# shellcheck disable=SC2034
LOCALCLUSTER_NODE_DB_MIN_FREE_MB="4096"
