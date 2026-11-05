#!/usr/bin/env python3
"""Add a marked Rancher rewrite, preserving unrelated CoreDNS config."""
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

def kubectl(*args, data=None):
    return subprocess.run(
        ["kubectl", *args], input=data, text=True, check=True,
        stdout=subprocess.PIPE,
    ).stdout

cm = json.loads(kubectl("-n", "kube-system", "get", "cm", "coredns", "-o", "json"))
core = cm["data"]["Corefile"]
begin = "# BEGIN NT132 RANCHER"
end = "# END NT132 RANCHER"
snippet = """    # BEGIN NT132 RANCHER
    rewrite stop {
        name exact rancher.nt132.test rancher-ingress.rancher-ingress.svc.cluster.local
        answer auto
    }
    # END NT132 RANCHER
"""
if begin in core:
    if snippet not in core or core.count(begin) != 1 or core.count(end) != 1:
        sys.exit("Existing NT132 block differs. Inspect Corefile before changing it.")
    print("Rancher DNS block already matches.")
    sys.exit(0)
if core.count(".:53 {") != 1:
    sys.exit("Expected one .:53 server block; inspect CoreDNS manually.")
updated = core.replace(".:53 {", ".:53 {\n" + snippet, 1)
backup = pathlib.Path.home() / ".nt132-private" / "backups"
backup.mkdir(parents=True, exist_ok=True, mode=0o700)
target = backup / ("coredns-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
target.write_text(json.dumps(cm, indent=2), encoding="utf-8")
# Compare resourceVersion and Corefile before patching to avoid overwriting concurrent edits.
patch = [
    {"op": "test", "path": "/metadata/resourceVersion", "value": cm["metadata"]["resourceVersion"]},
    {"op": "test", "path": "/data/Corefile", "value": core},
    {"op": "replace", "path": "/data/Corefile", "value": updated},
]
kubectl("-n", "kube-system", "patch", "cm", "coredns", "--type=json", "-p", json.dumps(patch))
print("Saved backup:", target)
print("Verify CoreDNS logs and Rancher DNS from a Pod before proceeding.")
