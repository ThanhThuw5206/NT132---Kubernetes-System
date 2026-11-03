#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
cluster_ready
kubectl wait --for=condition=Ready node/cp-01 node/wk-01 node/wk-02 --timeout=180s
kubectl -n kube-system rollout status deploy/coredns --timeout=180s
kubectl -n cattle-system rollout status deploy/rancher --timeout=180s
kubectl -n istio-system rollout status deploy/istiod --timeout=180s
kubectl -n istio-system rollout status deploy/istio-ingressgateway --timeout=180s
kubectl get nodes -o wide
kubectl -n cattle-system get ingress
kubectl -n istio-system get svc istio-ingressgateway -o wide
kubectl get pods -A --field-selector=status.phase=Pending
echo "Also perform the DNS/TLS test and external HTTP tests in docs/deploy-cloud.md."
