#!/usr/bin/env python3
"""Render application-owned integration only after TV2 supplies real values."""
import argparse
import json
import pathlib
import re
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIELDS = {
    "namespace", "entry_service", "entry_service_port", "public_path_prefix",
    "target_service", "target_service_port", "target_port", "target_labels",
    "allowed_caller_labels", "allowed_service_account", "trust_domain",
    "allowed_http_methods", "allowed_http_paths", "permit_prometheus_scrape",
}

def validate(cfg):
    if not isinstance(cfg, dict) or set(cfg) != FIELDS:
        raise ValueError("Application config keys must exactly match application.example.json.")
    if "REPLACE_ME" in json.dumps(cfg):
        raise ValueError("TV2 must replace every REPLACE_ME before rendering.")
    dns_label = r"[a-z][a-z0-9-]{0,61}[a-z0-9]|[a-z]"
    for field in ("namespace", "entry_service", "target_service", "allowed_service_account"):
        if not isinstance(cfg[field], str) or not re.fullmatch(dns_label, cfg[field]):
            raise ValueError("Invalid DNS label: " + field)
    if cfg["namespace"] in {"default", "kube-system", "istio-system", "cattle-system", "rancher-ingress"}:
        raise ValueError("Use a dedicated application namespace.")
    for field in ("entry_service_port", "target_service_port", "target_port"):
        if type(cfg[field]) is not int or not 1 <= cfg[field] <= 65535:
            raise ValueError("Invalid TCP port: " + field)
    label_part = r"[A-Za-z0-9]([A-Za-z0-9_.-]{0,61}[A-Za-z0-9])?"
    for field in ("target_labels", "allowed_caller_labels"):
        labels = cfg[field]
        if not isinstance(labels, dict) or not labels:
            raise ValueError("Labels must be a nonempty mapping: " + field)
        for key, value in labels.items():
            if not isinstance(key, str) or not re.fullmatch(label_part, key):
                raise ValueError("Use simple unprefixed label keys: " + field)
            if not isinstance(value, str) or not re.fullmatch(label_part, value):
                raise ValueError("Invalid label value: " + field)
    if cfg["target_labels"] == cfg["allowed_caller_labels"]:
        raise ValueError("Caller and target must have distinct selectors for this lab.")
    domain = cfg["trust_domain"]
    if not isinstance(domain, str) or len(domain) > 253 or any(
        not re.fullmatch(dns_label, part) for part in domain.split(".")
    ):
        raise ValueError("Invalid trust domain.")
    paths = cfg["allowed_http_paths"]
    if not isinstance(paths, list) or not paths:
        raise ValueError("At least one allowed HTTP path is required.")
    for value in [cfg["public_path_prefix"], *paths]:
        if not isinstance(value, str) or not value.startswith("/") or any(c.isspace() for c in value):
            raise ValueError("Paths must start with / and contain no whitespace.")
    methods = cfg["allowed_http_methods"]
    if not isinstance(methods, list) or not methods or not set(methods) <= {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
        raise ValueError("Specify explicit HTTP methods.")
    if type(cfg["permit_prometheus_scrape"]) is not bool:
        raise ValueError("permit_prometheus_scrape must be a boolean.")

def resources(cfg):
    validate(cfg)
    ns = cfg["namespace"]
    def obj(api, kind, name, spec):
        return {"apiVersion": api, "kind": kind,
                "metadata": {"name": name, "namespace": ns}, "spec": spec}
    selector = {"matchLabels": cfg["target_labels"]}
    principal = cfg["trust_domain"] + "/ns/" + ns + "/sa/" + cfg["allowed_service_account"]
    rules = [{"from": [{"podSelector": {"matchLabels": cfg["allowed_caller_labels"]}}],
              "ports": [{"protocol": "TCP", "port": cfg["target_port"]}]}]
    if cfg["permit_prometheus_scrape"]:
        rules.append({
            "from": [{
                "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "istio-system"}},
                "podSelector": {"matchLabels": {"app": "prometheus"}},
            }],
            "ports": [{"protocol": "TCP", "port": 15020}, {"protocol": "TCP", "port": 15090}],
        })
    return {
        "namespace.json": {"apiVersion": "v1", "kind": "Namespace",
            "metadata": {"name": ns, "labels": {"istio-injection": "enabled"}}},
        "gateway.json": obj("networking.istio.io/v1", "Gateway", "application-gateway", {
            "selector": {"istio": "ingressgateway"},
            "servers": [{"port": {"number": 80, "name": "http", "protocol": "HTTP"}, "hosts": ["*"]}],
        }),
        "route.json": obj("networking.istio.io/v1", "VirtualService", "application-route", {
            "hosts": ["*"], "gateways": ["application-gateway"],
            "http": [{"match": [{"uri": {"prefix": cfg["public_path_prefix"]}}],
                      "route": [{"destination": {"host": cfg["entry_service"] + "." + ns + ".svc.cluster.local",
                                                "port": {"number": cfg["entry_service_port"]}}}]}],
        }),
        "mtls.json": obj("security.istio.io/v1", "PeerAuthentication", "target-strict", {
            "selector": selector, "mtls": {"mode": "STRICT"},
        }),
        "authorization.json": obj("security.istio.io/v1", "AuthorizationPolicy", "target-from-caller", {
            "selector": selector, "action": "ALLOW",
            "rules": [{"from": [{"source": {"principals": [principal]}}],
                       "to": [{"operation": {"methods": cfg["allowed_http_methods"], "paths": cfg["allowed_http_paths"]}}]}],
        }),
        "network-policy.json": obj("networking.k8s.io/v1", "NetworkPolicy", "target-ingress", {
            "podSelector": selector, "policyTypes": ["Ingress"], "ingress": rules,
        }),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=pathlib.Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8-sig"))
    manifests = resources(cfg)  # Validate everything before writing.
    parent = ROOT / ".generated"
    parent.mkdir(exist_ok=True)
    # Each render is isolated; failures cannot replace a previously rendered set.
    out = pathlib.Path(tempfile.mkdtemp(prefix="application-", dir=parent))
    for name, value in manifests.items():
        (out / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    (out / "inputs.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
