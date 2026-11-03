#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
[[ "$(hostname -s)" == cp-01 ]] || die "Run on cp-01."
need kubeadm
if [[ -e /etc/kubernetes/admin.conf ]]; then
  echo "Existing control plane detected; checking API."
else
  sudo kubeadm config validate --config "$ROOT/cluster/bootstrap/kubeadm.yaml"
  sudo kubeadm config images pull --config "$ROOT/cluster/bootstrap/kubeadm.yaml"
  sudo kubeadm init --config "$ROOT/cluster/bootstrap/kubeadm.yaml"
fi
mkdir -p "$HOME/.kube"
sudo install -m 600 -o "$(id -u)" -g "$(id -g)" /etc/kubernetes/admin.conf "$HOME/.kube/config"
kubectl get --raw=/readyz
kubectl get nodes -o wide
echo
echo "Next: sudo kubeadm token create --ttl 2h --print-join-command"
echo "Send the resulting command privately. Each worker runs it with sudo."
