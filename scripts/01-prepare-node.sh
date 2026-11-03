#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
[[ $EUID -eq 0 ]] || die "Run: sudo bash scripts/01-prepare-node.sh"
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || die "This script targets Ubuntu 24.04."
[[ "$(uname -m)" == x86_64 ]] || die "This configuration targets amd64."
case "$(hostname -s)" in cp-01|wk-01|wk-02) ;; *) die "Unexpected hostname.";; esac
exec 9>/run/nt132-prepare.lock
flock -n 9 || die "Another node preparation is running."
if [[ -f /etc/kubernetes/kubelet.conf ]]; then
  echo "Node already joined. No package/runtime changes performed."
  kubelet --version
  systemctl is-active containerd kubelet
  exit 0
fi
apt-get -o DPkg::Lock::Timeout=180 update
apt-get -o DPkg::Lock::Timeout=180 install -y ca-certificates curl gpg containerd python3 openssl git
swapoff -a
[[ -e /etc/fstab.nt132-backup ]] || cp -a /etc/fstab /etc/fstab.nt132-backup
sed -i '/^[^#].*[[:space:]]swap[[:space:]]/ s/^/# nt132 /' /etc/fstab
cat >/etc/modules-load.d/nt132.conf <<'EOF'
overlay
br_netfilter
EOF
modprobe overlay
modprobe br_netfilter
cat >/etc/sysctl.d/99-nt132.conf <<'EOF'
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
sysctl --system
# Preserve an existing file once, then install the known fresh-node configuration.
mkdir -p /etc/containerd
if [[ -f /etc/containerd/config.toml && ! -f /etc/containerd/config.toml.nt132-backup ]]; then
  cp -a /etc/containerd/config.toml /etc/containerd/config.toml.nt132-backup
fi
containerd config default >/etc/containerd/config.toml
grep -q 'SystemdCgroup = false' /etc/containerd/config.toml || die "Unexpected containerd schema; inspect config before continuing."
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
systemctl enable --now containerd
systemctl restart containerd
mkdir -p /etc/apt/keyrings
curl --fail --silent --show-error --location "https://pkgs.k8s.io/core:/stable:/$K8S_MINOR/deb/Release.key" |
  gpg --dearmor --yes -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/$K8S_MINOR/deb/ /" >/etc/apt/sources.list.d/kubernetes.list
apt-get -o DPkg::Lock::Timeout=180 update
apt-get -o DPkg::Lock::Timeout=180 install -y \
  kubelet="$K8S_PACKAGE_VERSION" kubeadm="$K8S_PACKAGE_VERSION" kubectl="$K8S_PACKAGE_VERSION"
apt-mark hold kubelet kubeadm kubectl
systemctl enable kubelet
containerd --version
kubeadm version -o short
echo "Prepared. Run init only on cp-01; workers use the private join command."
