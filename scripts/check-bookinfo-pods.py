#!/usr/bin/env python3
"""Check a saved/piped Bookinfo PodList; never contacts Kubernetes or changes resources."""
import argparse
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tv3_readiness", ROOT / "scripts/tv3.py")
tv3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tv3)
EXPECTED = {"details-v1": ("details", "v1"), "productpage-v1": ("productpage", "v1"),
            "reviews-v2": ("reviews", "v2"), "ratings-v1": ("ratings", "v1")}


def validate_pods(payload):
    if (not isinstance(payload, dict) or payload.get("kind") not in {"PodList", "List"}
            or not isinstance(payload.get("items"), list)):
        raise ValueError("Expected a Kubernetes PodList JSON object with an items array.")
    for pod in payload["items"]:
        if not isinstance(pod, dict):
            raise ValueError("Every PodList item must be a Pod object.")
        for field in ("metadata", "spec"):
            if not isinstance(pod.get(field), dict):
                raise ValueError("Every Pod needs an object for " + field + ".")
        meta = pod["metadata"]
        if any(not isinstance(meta.get(field), str) or not meta[field] for field in ("name", "namespace")):
            raise ValueError("Every Pod needs a name and namespace.")
        if not isinstance(meta.get("labels", {}), dict):
            raise ValueError("Pod labels must be an object.")
        for field in ("containers", "initContainers"):
            values = pod["spec"].get(field, [])
            if not isinstance(values, list) or any(
                not isinstance(value, dict) or not isinstance(value.get("name"), str) for value in values
            ):
                raise ValueError("Pod " + field + " must be a list of named containers.")
        status = pod.get("status", {})
        if not isinstance(status, dict):
            raise ValueError("Pod status must be an object.")
        for field in ("containerStatuses", "initContainerStatuses"):
            values = status.get(field, [])
            if not isinstance(values, list) or any(
                not isinstance(value, dict) or not isinstance(value.get("name"), str)
                or type(value.get("ready", False)) is not bool for value in values
            ):
                raise ValueError("Pod " + field + " needs named entries with boolean readiness.")
        conditions = status.get("conditions", [])
        if not isinstance(conditions, list) or any(
            not isinstance(value, dict) or not isinstance(value.get("type"), str)
            or not isinstance(value.get("status"), str) for value in conditions
        ):
            raise ValueError("Pod conditions must contain string type and status fields.")
    return payload["items"]


def evaluate(payload, baseline=False, namespace="bookinfo"):
    pods = validate_pods(payload)
    report = {"namespace": namespace, "mode": "baseline" if baseline else "mesh",
              "scope": "Pod readiness only; application HTTP/Service/policy evidence is still required",
              "ready": False, "apps": {name: {"ready": False, "pods": []} for name in EXPECTED},
              "ignored_terminating_pods": [], "errors": []}
    for pod in pods:
        meta, status = pod["metadata"], pod.get("status", {})
        if meta["namespace"] != namespace:
            continue
        name = meta["name"]
        if meta.get("deletionTimestamp"):
            report["ignored_terminating_pods"].append(name)
            continue
        labels = meta.get("labels", {})
        containers = pod["spec"].get("containers", []) + pod["spec"].get("initContainers", [])
        has_proxy = any(container["name"] == "istio-proxy" for container in containers)
        if baseline and has_proxy:
            report["errors"].append(name + ": baseline must not contain istio-proxy.")
        if labels.get("app") == "reviews" and labels.get("version") in {"v1", "v3"}:
            report["errors"].append(name + ": active reviews-v1/v3 must be scaled to zero.")
        for workload, (app, version) in EXPECTED.items():
            if labels.get("app") != app or labels.get("version") != version:
                continue
            app_ready = any(container["name"] == app for container in pod["spec"].get("containers", [])) and any(
                container["name"] == app and container.get("ready", False)
                for container in status.get("containerStatuses", [])
            )
            proxy_ready = bool(tv3.proxy_ready(pod))
            ready = (status.get("phase") == "Running" and tv3.is_ready(pod) and app_ready
                     and (not has_proxy if baseline else proxy_ready))
            report["apps"][workload]["pods"].append({
                "name": name, "phase": status.get("phase"), "pod_ready": tv3.is_ready(pod),
                "app_ready": app_ready, "proxy_present": has_proxy, "proxy_ready": proxy_ready, "ready": ready})
            if not ready:
                report["errors"].append(name + ": expected Running, Pod/app Ready and "
                                        + ("no proxy." if baseline else "a Ready Istio proxy."))
    for workload, entry in report["apps"].items():
        entry["ready"] = bool(entry["pods"]) and all(pod["ready"] for pod in entry["pods"])
        if not entry["pods"]:
            report["errors"].append(workload + ": no active Pod with the expected app/version labels.")
    report["ready"] = not report["errors"] and all(entry["ready"] for entry in report["apps"].values())
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true", help="Require app readiness without istio-proxy")
    parser.add_argument("--namespace", default="bookinfo")
    args = parser.parse_args(argv)
    try:
        report = evaluate(json.loads(sys.stdin.read().lstrip("\ufeff")), args.baseline, args.namespace)
    except (ValueError, TypeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
