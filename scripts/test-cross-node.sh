#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
cluster_ready
kubectl apply -f "$ROOT/tests/service/network-check.yaml"
kubectl -n network-check wait --for=condition=Ready pod/server pod/client --timeout=180s
server_ip="$(kubectl -n network-check get pod server -o jsonpath='{.status.podIP}')"
service_ip="$(kubectl -n network-check get svc server -o jsonpath='{.spec.clusterIP}')"
for url in "http://$server_ip" "http://$service_ip" "http://server.network-check.svc.cluster.local"; do
  status="$(kubectl -n network-check exec client -- curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "$url")"
  [[ "$status" == 200 ]] || die "$url returned $status"
  echo "$url -> $status"
done
kubectl -n network-check get pods -o wide
echo "Save evidence, then run: kubectl delete namespace network-check"
