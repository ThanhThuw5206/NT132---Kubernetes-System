#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || die "Run on Ubuntu amd64."
need curl
need sha256sum
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
cd "$tmp"
archive="helm-$HELM_VERSION-linux-amd64.tar.gz"
curl -fLsS "https://get.helm.sh/$archive" -o "$archive"
curl -fLsS "https://get.helm.sh/$archive.sha256sum" -o "$archive.sha256sum"
sha256sum --check "$archive.sha256sum"
tar -xzf "$archive"
sudo install -m 0755 linux-amd64/helm /usr/local/bin/helm
helm version --short
