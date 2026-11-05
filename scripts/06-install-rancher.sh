#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
cluster_ready
need helm
need openssl
need python3
helm repo add traefik https://traefik.github.io/charts --force-update
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable --force-update
helm repo update traefik rancher-stable
helm upgrade --install rancher-ingress traefik/traefik \
  -n rancher-ingress --create-namespace --version "$TRAEFIK_CHART_VERSION" \
  -f "$ROOT/management/rancher/traefik-values.yaml" --wait --timeout 5m
tls="$HOME/.nt132-private/tls"
mkdir -p "$tls"
chmod 700 "$HOME/.nt132-private" "$tls"
umask 077
# Never silently rotate a CA if the local key material is incomplete or missing.
count=0
for file in ca.key ca.crt tls.key tls.crt; do
  [[ ! -e "$tls/$file" ]] || count=$((count + 1))
done
if [[ "$count" -eq 0 ]]; then
  if kubectl -n cattle-system get secret tls-ca >/dev/null 2>&1; then
    die "Cluster has a CA but this user has no local keys. Restore the original TLS files."
  fi
  openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 90 \
    -keyout "$tls/ca.key" -out "$tls/ca.crt" -subj "/CN=NT132 Lab CA" \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign"
  openssl req -newkey rsa:2048 -nodes -keyout "$tls/tls.key" -out "$tls/rancher.csr" \
    -subj "/CN=rancher.nt132.test"
  cat >"$tls/server.ext" <<'EOF'
subjectAltName=DNS:rancher.nt132.test
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF
  openssl x509 -req -in "$tls/rancher.csr" -CA "$tls/ca.crt" -CAkey "$tls/ca.key" \
    -CAcreateserial -out "$tls/tls.crt" -days 90 -sha256 -extfile "$tls/server.ext"
elif [[ "$count" -ne 4 ]]; then
  die "Partial TLS files in $tls. Restore all four original files before retry."
fi
openssl verify -CAfile "$tls/ca.crt" "$tls/tls.crt"
cert_key="$(openssl x509 -in "$tls/tls.crt" -pubkey -noout)"
private_key="$(openssl pkey -in "$tls/tls.key" -pubout)"
[[ "$cert_key" == "$private_key" ]] || die "TLS certificate and private key do not match."
if kubectl -n cattle-system get secret tls-ca >/dev/null 2>&1; then
  existing_ca="$(kubectl -n cattle-system get secret tls-ca -o jsonpath='{.data.cacerts\.pem}' | base64 -d)"
  [[ "$existing_ca" == "$(cat "$tls/ca.crt")" ]] || die "Cluster CA differs; investigate instead of rotating it."
fi
openssl x509 -in "$tls/tls.crt" -noout -checkend 86400
openssl x509 -in "$tls/tls.crt" -noout -checkhost rancher.nt132.test
kubectl create namespace cattle-system --dry-run=client -o yaml | kubectl apply -f -
kubectl -n cattle-system create secret tls tls-rancher-ingress \
  --cert="$tls/tls.crt" --key="$tls/tls.key" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n cattle-system create secret generic tls-ca \
  --from-file=cacerts.pem="$tls/ca.crt" --dry-run=client -o yaml | kubectl apply -f -
python3 "$ROOT/scripts/configure-rancher-dns.py"
helm upgrade --install rancher rancher-stable/rancher -n cattle-system \
  --version "$RANCHER_CHART_VERSION" -f "$ROOT/management/rancher/values.yaml" --wait --timeout 10m
kubectl -n cattle-system get pods,svc,ingress
echo "Agent server URL: https://rancher.nt132.test (no :8443). Browser uses SSH forwarding on :8443."
echo "CA path: $tls/ca.crt"
