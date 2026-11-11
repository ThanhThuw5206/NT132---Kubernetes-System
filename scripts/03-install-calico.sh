#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
cluster_ready
lab_nodes
kubectl get node "${LAB_NODES[@]}" >/dev/null
need curl
mkdir -p "$ROOT/.cache/calico"
cd "$ROOT/.cache/calico"
for file in operator-crds.yaml tigera-operator.yaml; do
  curl -fLsS "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/$file" -o "$file"
done
kubectl apply --server-side -f operator-crds.yaml
kubectl wait --for=condition=Established crd/installations.operator.tigera.io --timeout=120s
kubectl wait --for=condition=Established crd/apiservers.operator.tigera.io --timeout=120s
kubectl apply -f tigera-operator.yaml
kubectl apply -f "$ROOT/cluster/calico/installation.yaml"
kubectl apply -f "$ROOT/cluster/calico/apiserver.yaml"
kubectl -n tigera-operator rollout status deploy/tigera-operator --timeout=300s
echo "Workers must join before the following readiness checks can complete."
kubectl wait --for=condition=Ready nodes --all --timeout=600s
kubectl -n kube-system rollout status deploy/coredns --timeout=300s
kubectl wait --for=condition=Available=True tigerastatus/calico --timeout=300s
kubectl wait --for=condition=Progressing=False tigerastatus/calico --timeout=300s
kubectl wait --for=condition=Degraded=False tigerastatus/calico --timeout=300s
for component in apiserver tiers; do
  kubectl wait --for=create "tigerastatus/$component" --timeout=300s
  for condition in Available=True Progressing=False Degraded=False; do
    kubectl wait --for="condition=$condition" "tigerastatus/$component" --timeout=300s
  done
done
kubectl wait --for=create apiservice/v3.projectcalico.org --timeout=300s
kubectl wait --for=condition=Available=True apiservice/v3.projectcalico.org --timeout=300s
kubectl get nodes -o wide
kubectl get tigerastatus
