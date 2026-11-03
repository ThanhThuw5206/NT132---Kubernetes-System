#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
cluster_ready
case "${1:-}" in
  rancher) exec kubectl -n rancher-ingress port-forward svc/rancher-ingress 8443:443 --address=127.0.0.1 ;;
  app) exec kubectl -n istio-system port-forward svc/istio-ingressgateway 8080:80 --address=127.0.0.1 ;;
  kiali) exec kubectl -n istio-system port-forward svc/kiali 20001:20001 --address=127.0.0.1 ;;
  *) die "Usage: bash scripts/09-port-forward.sh rancher|app|kiali (one SSH terminal per command)" ;;
esac
