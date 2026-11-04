#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
cluster_ready
need tee
need sha256sum
mkdir -p "$ROOT/.generated"
evidence="$(mktemp -d "$ROOT/.generated/net01-XXXXXXXX")"
exec > >(tee "$evidence/run.log") 2>&1
trap 'status=$?; printf "exit_code=%s\n" "$status" >"$evidence/result.txt"' EXIT
echo "NET01 evidence: $evidence"
date -u '+Started UTC: %Y-%m-%dT%H:%M:%SZ'
kubectl config current-context
sha256sum "$ROOT/scripts/test-cross-node.sh" "$ROOT/tests/service/network-check.yaml" "$ROOT/config/versions.env"
kubectl wait --for=condition=Ready node/cp-01 node/wk-01 node/wk-02 --timeout=180s
# Do not adopt a namespace or resource created by somebody else.
for resource in namespace/network-check pod/server pod/client pod/server-reverse pod/client-reverse service/server service/server-reverse; do
  owner="$(kubectl -n network-check get "$resource" --ignore-not-found -o 'jsonpath={.metadata.uid}{"|"}{.metadata.labels.app\.kubernetes\.io/managed-by}')"
  [[ -z "$owner" || "$owner" == *'|nt132-net01' ]] || die "Refusing to overwrite $resource; inspect existing network-check resources first."
done
kubectl apply -f "$ROOT/tests/service/network-check.yaml"
kubectl -n network-check wait --for=condition=Ready pod/server pod/client pod/server-reverse pod/client-reverse --timeout=180s
for suffix in '' '-reverse'; do
  server="server$suffix"
  client="client$suffix"
  server_ip="$(kubectl -n network-check get pod "$server" -o jsonpath='{.status.podIP}')"
  service_ip="$(kubectl -n network-check get svc "$server" -o jsonpath='{.spec.clusterIP}')"
  server_node="$(kubectl -n network-check get pod "$server" -o jsonpath='{.spec.nodeName}')"
  client_node="$(kubectl -n network-check get pod "$client" -o jsonpath='{.spec.nodeName}')"
  [[ -n "$server_node" && -n "$client_node" && "$server_node" != "$client_node" ]] || die "Test pods must be on different nodes."
  [[ -n "$server_ip" && -n "$service_ip" ]] || die "Missing Pod or Service IP."
  echo "$client ($client_node) -> $server ($server_node)"
  for url in "http://$server_ip" "http://$service_ip" "http://$server.network-check.svc.cluster.local"; do
    status="$(kubectl -n network-check exec "$client" -- curl --noproxy '*' -sS --max-time 10 -o /dev/null -w '%{http_code}' "$url")"
    [[ "$status" == 200 ]] || die "$client -> $url returned $status"
    echo "$client -> $url -> $status"
  done
done
kubectl -n network-check get pods -o wide
kubectl -n network-check get svc,endpointslice -o wide
date -u '+Finished UTC: %Y-%m-%dT%H:%M:%SZ'
echo "Six HTTP checks passed. Peer verification is still required for NET01."
echo "Save evidence, then inspect and remove only the fixture: kubectl delete -f tests/service/network-check.yaml"
