#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
cluster_ready
need helm
helm repo add istio https://istio-release.storage.googleapis.com/charts --force-update
helm repo update istio
helm upgrade --install istio-base istio/base -n istio-system --create-namespace \
  --version "$ISTIO_VERSION" --wait --timeout 5m
helm upgrade --install istiod istio/istiod -n istio-system \
  --version "$ISTIO_VERSION" -f "$ROOT/mesh/istio/istiod-values.yaml" --wait --timeout 5m
helm upgrade --install istio-ingressgateway istio/gateway -n istio-system \
  --version "$ISTIO_VERSION" -f "$ROOT/mesh/istio/gateway-values.yaml" --wait --timeout 5m
kubectl -n istio-system get deploy,svc,pods -o wide
echo "Gateway HTTP NodePort: 30080. Application routes must be supplied by TV2."
