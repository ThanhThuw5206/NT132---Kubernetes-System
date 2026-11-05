#!/usr/bin/env bash
# Sourced by scripts; environment config is trusted repository code.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/config/versions.env"
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "Missing command: $1"; }
cluster_ready() {
  need kubectl
  kubectl get --raw=/readyz >/dev/null
  local actual
  actual="$(kubectl get node cp-01 -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')"
  [[ "$actual" == "10.20.0.10" ]] || die "Wrong cluster: cp-01 must have InternalIP 10.20.0.10."
}
lab_nodes() {
  need python3
  local mapping
  mapping="$(kubectl get nodes -o json | python3 "$ROOT/scripts/cluster-nodes.py")" || die "Cannot identify the three lab nodes."
  mapfile -t LAB_NODES <<<"$mapping"
  [[ ${#LAB_NODES[@]} -eq 3 ]] || die "Expected three lab nodes."
}
