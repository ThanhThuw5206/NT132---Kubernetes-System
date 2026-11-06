#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
need curl
[[ "$ISTIO_VERSION" == "1.30.7" ]] || die "Review the Prometheus lab patch before changing ISTIO_VERSION from 1.30.7."
patch="$ROOT/observability/prometheus-lab-patch.json"
[[ -f "$patch" ]] || die "Missing Prometheus lab patch: $patch"
cluster_ready
dir="$ROOT/.cache/observability"
mkdir -p "$dir"
for name in prometheus kiali; do
  curl -fLsS --connect-timeout 15 --max-time 120 "https://raw.githubusercontent.com/istio/istio/$ISTIO_VERSION/samples/addons/$name.yaml" -o "$dir/$name.yaml"
  kubectl --request-timeout=30s apply -f "$dir/$name.yaml"
  if [[ "$name" == "prometheus" ]]; then
    # Keep the reviewed addon flags and bound resources/storage for the 3-VM lab.
    kubectl --request-timeout=30s -n istio-system patch deployment prometheus --type=strategic --patch-file "$patch"
  fi
  kubectl --request-timeout=330s -n istio-system rollout status "deployment/$name" --timeout=300s
done
echo "Lab addons only. Kiali uses port-forward; generate traffic to populate its graph."
