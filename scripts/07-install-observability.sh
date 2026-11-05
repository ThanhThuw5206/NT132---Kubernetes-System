#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
cluster_ready
need curl
dir="$ROOT/.cache/observability"
mkdir -p "$dir"
for name in prometheus kiali; do
  curl -fLsS "https://raw.githubusercontent.com/istio/istio/$ISTIO_VERSION/samples/addons/$name.yaml" -o "$dir/$name.yaml"
  kubectl apply -f "$dir/$name.yaml"
  kubectl -n istio-system rollout status "deployment/$name" --timeout=300s
done
echo "Lab addons only. Kiali uses port-forward; generate traffic to populate its graph."
