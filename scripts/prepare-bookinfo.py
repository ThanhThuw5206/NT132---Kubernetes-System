#!/usr/bin/env python3
"""Prepare a hash-checked Bookinfo baseline offline; never contacts or applies to a cluster."""
import argparse
import copy
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "apps/bookinfo"
COMPONENTS = {"details", "ratings", "reviews", "productpage"}
DEPLOYMENTS = {"details-v1", "ratings-v1", "reviews-v1", "reviews-v2", "reviews-v3", "productpage-v1"}
SOURCE_FILES = {"manifest_yaml": "upstream/bookinfo.yaml",
                "manifest_json": "upstream/bookinfo.list.json", "license": "upstream/LICENSE"}
# Lab starting points, not measured requirements. Proxy resources are additional.
RESOURCES = {
    "details": {"requests": {"cpu": "50m", "memory": "64Mi"}, "limits": {"cpu": "250m", "memory": "128Mi"}},
    "ratings": {"requests": {"cpu": "50m", "memory": "64Mi"}, "limits": {"cpu": "250m", "memory": "128Mi"}},
    "reviews": {"requests": {"cpu": "200m", "memory": "384Mi"}, "limits": {"cpu": "1000m", "memory": "768Mi"}},
    "productpage": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "500m", "memory": "512Mi"}},
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def validate_namespace(namespace):
    if not isinstance(namespace, str) or not re.fullmatch(r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", namespace):
        raise ValueError("Use a DNS-label application namespace.")
    if namespace in {"default", "kube-system", "kube-public", "kube-node-lease", "istio-system", "cattle-system", "rancher-ingress"}:
        raise ValueError("Use a dedicated application namespace, not a system namespace.")


def load_source(source=SOURCE, versions=ROOT / "config/versions.env"):
    """The reviewed lock binds these artifacts; it does not authenticate their author."""
    source = pathlib.Path(source)
    lock = json.loads((source / "source-lock.json").read_text(encoding="utf-8-sig"))
    if lock.get("format") != "nt132-bookinfo-source-v1" or lock.get("license") != "Apache-2.0":
        raise ValueError("Unknown Bookinfo source lock or license.")
    pinned = re.findall(r"^ISTIO_VERSION=([^\s#]+)\s*$", pathlib.Path(versions).read_text(encoding="utf-8-sig"), re.MULTILINE)
    if len(pinned) != 1 or lock.get("istio_version") != pinned[0]:
        raise ValueError("Bookinfo source version does not match config/versions.env; review and update artifacts together.")
    if set(lock.get("files", {})) != set(SOURCE_FILES):
        raise ValueError("Bookinfo source lock must contain the reviewed YAML, JSON and license.")
    contents = {}
    for role, name in SOURCE_FILES.items():
        entry = lock["files"][role]
        if entry.get("path") != name:
            raise ValueError("Unexpected source artifact path: " + role)
        path = source / name
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError("Unsafe source artifact: " + name)
        data = path.read_bytes()
        if sha256(data) != entry.get("sha256"):
            raise ValueError("Source SHA256 mismatch: " + name)
        contents[role] = data
    if lock["files"]["manifest_json"].get("derived_from") != SOURCE_FILES["manifest_yaml"]:
        raise ValueError("The normalized JSON must name its upstream YAML source.")
    manifest = json.loads(contents["manifest_json"])
    validate_manifest(manifest)
    return manifest, lock


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get("apiVersion") != "v1" or manifest.get("kind") != "List":
        raise ValueError("Expected a normalized Kubernetes v1/List.")
    items = manifest.get("items")
    if not isinstance(items, list) or len(items) != 14:
        raise ValueError("Expected exactly the 14 upstream Bookinfo resources.")
    expected = {("Service", name) for name in COMPONENTS}
    expected |= {("ServiceAccount", "bookinfo-" + name) for name in COMPONENTS}
    expected |= {("Deployment", name) for name in DEPLOYMENTS}
    actual = [(item.get("kind"), item.get("metadata", {}).get("name")) for item in items]
    if len(set(actual)) != len(actual) or set(actual) != expected:
        raise ValueError("Unexpected or duplicate Bookinfo resource topology.")
    for item in items:
        kind, name = item["kind"], item["metadata"]["name"]
        if "namespace" in item["metadata"]:
            raise ValueError("Upstream resources must not embed a namespace.")
        if kind == "ServiceAccount":
            if item.get("apiVersion") != "v1":
                raise ValueError("Unexpected ServiceAccount API version.")
            continue
        if kind == "Service":
            spec = item["spec"]
            ports = spec.get("ports", [])
            if (item.get("apiVersion") != "v1" or spec.get("selector") != {"app": name}
                    or spec.get("type", "ClusterIP") != "ClusterIP" or len(ports) != 1
                    or ports[0].get("port") != 9080 or ports[0].get("targetPort", 9080) != 9080
                    or ports[0].get("name") != "http"):
                raise ValueError("Unexpected Bookinfo Service selector or port: " + name)
            continue
        component, version = name.rsplit("-", 1)
        template = item["spec"]["template"]
        labels = {"app": component, "version": version}
        pod = template["spec"]
        containers = pod.get("containers", [])
        image = "registry.istio.io/release/examples-bookinfo-" + name + ":1.20.3"
        if (item.get("apiVersion") != "apps/v1" or item["spec"].get("selector") != {"matchLabels": labels}
                or template["metadata"].get("labels") != labels
                or pod.get("serviceAccountName") != "bookinfo-" + component
                or len(containers) != 1 or containers[0].get("name") != component
                or containers[0].get("image") != image or containers[0].get("ports") != [{"containerPort": 9080}]
                or pod.get("initContainers")):
            raise ValueError("Unexpected Bookinfo workload identity, image or port: " + name)


def resources(namespace, manifest):
    """Keep upstream identities/volumes and overlay only the documented lab settings."""
    validate_namespace(namespace)
    validate_manifest(manifest)
    workload = copy.deepcopy(manifest)
    for item in workload["items"]:
        item["metadata"]["namespace"] = namespace
        if item["kind"] == "Service":
            item["spec"]["type"] = "ClusterIP"
            item["spec"]["ports"][0]["targetPort"] = 9080
        if item["kind"] != "Deployment":
            continue
        name = item["metadata"]["name"]
        item["spec"]["replicas"] = 0 if name in {"reviews-v1", "reviews-v3"} else 1
        template = item["spec"]["template"]
        # The injector rewrites these health probes when this baseline later joins the mesh.
        template["metadata"].setdefault("annotations", {})["sidecar.istio.io/rewriteAppHTTPProbers"] = "true"
        container = template["spec"]["containers"][0]
        container["resources"] = copy.deepcopy(RESOURCES[container["name"]])
        # All four exact-release sources expose a local /health endpoint independent of downstreams.
        for key, settings in {
                "startupProbe": {"periodSeconds": 5, "failureThreshold": 60},
                "readinessProbe": {"periodSeconds": 5, "failureThreshold": 3},
                "livenessProbe": {"periodSeconds": 10, "failureThreshold": 3}}.items():
            container[key] = {"httpGet": {"path": "/health", "port": 9080}, "timeoutSeconds": 2, **settings}
    namespace_resource = {"apiVersion": "v1", "kind": "Namespace", "metadata": {
        "name": namespace, "labels": {"istio-injection": "disabled", "app.kubernetes.io/managed-by": "nt132-bookinfo"}}}
    return {"namespace-baseline.json": namespace_resource, "workloads.json": workload}


def prepare(namespace="bookinfo", output=None, source=SOURCE, versions=ROOT / "config/versions.env"):
    manifest, lock = load_source(source, versions)
    values = resources(namespace, manifest)  # Validate everything before creating an output directory.
    if output:
        out = pathlib.Path(output)
        out.mkdir(parents=True, exist_ok=False)
    else:
        parent = ROOT / ".generated"
        parent.mkdir(exist_ok=True)
        out = pathlib.Path(tempfile.mkdtemp(prefix="bookinfo-", dir=parent))
    for name, value in values.items():
        (out / name).write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    report = {
        "format": "nt132-bookinfo-preparation-v1", "created": dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).isoformat(timespec="seconds"),
        "scope": "Local manifest preparation only; no cluster validation, apply or cloud changes",
        "namespace": namespace, "injection_baseline": "disabled", "istio_version": lock["istio_version"],
        "source_lock_sha256": sha256((pathlib.Path(source) / "source-lock.json").read_bytes()),
        "sources": lock["files"],
        "outputs": {name: sha256((out / name).read_bytes()) for name in values},
        "deployments": [{"name": item["metadata"]["name"], "replicas": item["spec"]["replicas"],
                         "image": item["spec"]["template"]["spec"]["containers"][0]["image"],
                         "resources": item["spec"]["template"]["spec"]["containers"][0]["resources"]}
                        for item in values["workloads.json"]["items"] if item["kind"] == "Deployment"],
        "notes": ["Only apply namespace-baseline.json and workloads.json in the agreed cloud session, not this report.",
                  "Baseline namespace disables injection; enable injection and restart workloads only after mesh readiness.",
                  "Do not reapply the disabled namespace or replica overlay to an existing mesh/scale experiment.",
                  "Resource values are lab starting points; measure RAM/startup and include proxy/system resources.",
                  "A health probe does not replace a successful business request or EndpointSlice evidence."]}
    (out / "preparation.json").write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default="bookinfo")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--output", type=pathlib.Path, help="New directory only; default .generated/bookinfo-*")
    mode.add_argument("--check", action="store_true", help="Verify locked source and planned baseline in memory without writing output")
    args = parser.parse_args(argv)
    try:
        if args.check:
            manifest, lock = load_source()
            resources(args.namespace, manifest)
            print("Verified 14 Bookinfo resources for Istio " + lock["istio_version"] + "; baseline only, not cloud acceptance")
        else:
            print(prepare(args.namespace, args.output))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
