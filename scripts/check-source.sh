#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
for file in scripts/*.sh; do bash -n "$file"; done
python3 -m unittest discover -s tests -v
terraform -chdir=infra/gcp fmt -check
terraform -chdir=infra/gcp validate
terraform -chdir=infra/gcp test
echo "Source checks passed. This does not verify a running Google Cloud cluster."
