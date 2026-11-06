#!/usr/bin/env python3
"""TV3 lab helpers. Rendering/traffic work without kubectl; never installs resources."""
import argparse
import datetime as dt
import hashlib
import http.client
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_COMMIT = "17aaed9"
spec = importlib.util.spec_from_file_location("application_renderer", ROOT / "scripts/render-application.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
nodes_spec = importlib.util.spec_from_file_location("cluster_nodes", ROOT / "scripts/cluster-nodes.py")
cluster_nodes = importlib.util.module_from_spec(nodes_spec)
nodes_spec.loader.exec_module(cluster_nodes)


def timestamp():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).isoformat(timespec="seconds")


def read_config(path):
    cfg = json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
    renderer.validate(cfg)
    return cfg


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def new_run(output=None):
    if output:
        path = pathlib.Path(output)
        path.mkdir(parents=True, exist_ok=False)
        return path
    parent = ROOT / ".generated"
    parent.mkdir(exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(prefix="tv3-", dir=parent))


def source_info():
    """Identify the working tree, including changes that git archive HEAD omits."""
    head = command(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    return {"base_commit": BASE_COMMIT, "head": head.get("stdout") if head["exit_code"] == 0 else None,
            "tv3_sha256": hashlib.sha256((ROOT / "scripts/tv3.py").read_bytes()).hexdigest()}


def package_paths():
    listing = ROOT / "docs/tv3-package-files.txt"
    names = [line.strip() for line in listing.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate entry in package file list")
    for name in names:
        relative = pathlib.PurePosixPath(name)
        path = ROOT / relative
        if (not relative.parts or relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name
                or relative.parts[0] in {".git", ".cache", ".generated", ".kube", ".ssh", "secrets", "private"}
                or path.suffix in {".key", ".pem", ".p12", ".pfx", ".tfvars", ".tfstate", ".kubeconfig"}
                or path.name in {"admin.conf", "super-admin.conf", ".env"}
                or (relative.parts[0] == "config" and name not in {"config/versions.env", "config/application.example.json"})
                or not path.resolve().is_relative_to(ROOT.resolve()) or path.is_symlink() or not path.is_file()):
            raise ValueError("Missing or unsafe package source: " + name)
    return names


def package(args):
    names = package_paths()  # Explicit allowlist; never glob the working tree.
    contents = {name: (ROOT / name).read_bytes() for name in names}
    manifest = {"format": "nt132-tv3-overlay-v1", "created": timestamp(), "source": source_info(),
                "scope": "Local source overlay only; no cloud acceptance results or credentials",
                "files": [{"path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                          for name, data in contents.items()]}
    out = new_run(args.output)
    write_json(out / "manifest.json", manifest)
    with zipfile.ZipFile(out / "tv3-overlay.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if name.endswith(".sh") else 0o100644) << 16
            archive.writestr(info, data)
        archive.writestr("tv3-overlay-manifest.json", (out / "manifest.json").read_bytes())
    sums = "".join(hashlib.sha256((out / name).read_bytes()).hexdigest() + "  " + name + "\n"
                   for name in ("tv3-overlay.zip", "manifest.json"))
    (out / "SHA256SUMS").write_text(sums, encoding="utf-8")
    print(out)
    return 0


def verify_package(args):
    """After extraction, verify the overlay files in this repo against its manifest."""
    manifest = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
    if manifest.get("format") != "nt132-tv3-overlay-v1":
        raise ValueError("Unknown overlay manifest format")
    if not manifest.get("files") or len({e["path"] for e in manifest["files"]}) != len(manifest["files"]):
        raise ValueError("Overlay file list must be nonempty and unique")
    errors = []
    for entry in manifest["files"]:
        relative = pathlib.PurePosixPath(entry["path"])
        path = ROOT / relative
        if (relative.is_absolute() or ".." in relative.parts or "\\" in entry["path"] or ":" in entry["path"]
                or not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file() or path.is_symlink()):
            errors.append("Missing/unsafe file: " + entry["path"])
        elif hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            errors.append("Changed file: " + entry["path"])
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Verified " + str(len(manifest["files"])) + " source files; base commit " + manifest["source"]["base_commit"])
    return 0


def selector_resources(cfg):
    renderer.validate(cfg)
    digest = hashlib.sha256((cfg["namespace"] + "/" + cfg["target_service"]).encode()).hexdigest()[:12]
    name = "tv3-selector-" + digest
    if name == cfg["target_service"]:
        name += "-lab"
    base = {
        "apiVersion": "v1", "kind": "Service",
        "metadata": {"name": name, "namespace": cfg["namespace"],
                     "labels": {"app.kubernetes.io/managed-by": "nt132-tv3"}},
        "spec": {"type": "ClusterIP", "selector": cfg["target_labels"],
                 "ports": [{"name": "http", "port": cfg["target_service_port"],
                            "targetPort": cfg["target_port"], "protocol": "TCP"}]},
    }
    broken = json.loads(json.dumps(base))
    broken["spec"]["selector"] = {"nt132.test/no-backend": "tv3-selector-test"}
    return {"selector-broken.json": broken, "selector-fixed.json": base}


def render(args):
    cfg = read_config(args.config)  # Validate before creating any output.
    values = renderer.resources(cfg)
    values.update(selector_resources(cfg))
    out = new_run(args.output)
    for name, value in values.items():
        write_json(out / name, value)
    write_json(out / "inputs.json", cfg)
    print(out)
    return 0


def command(argv, timeout=35):
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return {"exit_code": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "Local command timeout"}
    except FileNotFoundError:
        return {"exit_code": 127, "stdout": "", "stderr": "Missing command: " + argv[0]}


def kubectl(context, *args):
    return command(["kubectl", "--context", context, "--request-timeout=20s", *args])


def kjson(context, *args):
    result = kubectl(context, *args, "-o", "json")
    if result["exit_code"]:
        raise ValueError(result["stderr"] or "kubectl failed")
    return json.loads(result["stdout"])


def guard(context):
    ready = kubectl(context, "get", "--raw=/readyz")
    if ready["exit_code"] or ready["stdout"] != "ok":
        raise ValueError("API not ready: " + ready["stderr"])
    cp = kjson(context, "get", "node", "cp-01")
    addresses = cp.get("status", {}).get("addresses", [])
    if not any(x["type"] == "InternalIP" and x["address"] == "10.20.0.10" for x in addresses):
        raise ValueError("Wrong cluster: cp-01 must have InternalIP 10.20.0.10")


def is_ready(node):
    return any(c["type"] == "Ready" and c["status"] == "True"
               for c in node.get("status", {}).get("conditions", []))


def proxy_ready(pod):
    regular = any(c["name"] == "istio-proxy" for c in pod["spec"].get("containers", []))
    native = any(c["name"] == "istio-proxy" and c.get("restartPolicy") == "Always"
                 for c in pod["spec"].get("initContainers", []))
    status = pod.get("status", {})
    return ((regular and any(c["name"] == "istio-proxy" and c.get("ready") for c in status.get("containerStatuses", [])))
            or (native and any(c["name"] == "istio-proxy" and c.get("ready") for c in status.get("initContainerStatuses", []))))


def snapshot(args):
    guard(args.context)
    out = new_run(args.output)
    report = {"test": "TV3-preflight", "time": timestamp(), "context": args.context,
              "source": source_info(),
              "scope": "Readiness only; NET01/OBS01/SEC03/SVC04 still require requests and peer verification",
              "nodes": [], "checks": [], "errors": [],
              "pins": dict(line.split("=", 1) for line in (ROOT / "config/versions.env").read_text().splitlines()
                           if line and not line.startswith("#")),
              "helm": command(["helm", "version", "--short"])}
    nodes = kjson(args.context, "get", "nodes")["items"]
    for node in nodes:
        info = node.get("status", {}).get("nodeInfo", {})
        report["nodes"].append({"name": node["metadata"]["name"], "ready": is_ready(node),
                                "internal_ips": [a["address"] for a in node.get("status", {}).get("addresses", [])
                                                 if a.get("type") == "InternalIP"],
                                "versions": {k: info.get(k) for k in
                                             ("kubeletVersion", "containerRuntimeVersion", "osImage", "kernelVersion")}})
    try:
        resolved = cluster_nodes.resolve({"items": nodes})
        report["node_aliases"] = dict(zip(("cp-01", "wk-01", "wk-02"), resolved))
        expected = set(resolved)
        actual_ready = {n["name"] for n in report["nodes"] if n["ready"]}
        if not expected <= actual_ready:
            report["errors"].append("NotReady lab nodes: " + ", ".join(sorted(expected - actual_ready)))
    except ValueError as exc:
        report["errors"].append("Cannot identify lab nodes by InternalIP: " + str(exc))
    for ns, name in [("kube-system", "coredns"), ("istio-system", "istiod"),
                     ("istio-system", "istio-ingressgateway"), ("istio-system", "prometheus"),
                     ("istio-system", "kiali")]:
        try:
            deployment = kjson(args.context, "-n", ns, "get", "deployment", name)
            status = deployment.get("status", {})
            desired = deployment["spec"].get("replicas", 1)
            ok = (desired > 0 and status.get("observedGeneration", 0) >= deployment["metadata"]["generation"]
                  and status.get("updatedReplicas", 0) == desired and status.get("availableReplicas", 0) >= desired)
            report["checks"].append({"namespace": ns, "deployment": name, "ready": ok,
                                     "images": [c["image"] for c in deployment["spec"]["template"]["spec"]["containers"]]})
            if not ok:
                report["errors"].append(ns + "/" + name + " rollout incomplete")
        except ValueError as exc:
            report["errors"].append(ns + "/" + name + ": " + str(exc))
    try:
        calico = kjson(args.context, "get", "tigerastatus")["items"]
        report["calico"] = [{"name": x["metadata"]["name"], "conditions": x.get("status", {}).get("conditions", [])}
                             for x in calico]
        if not calico or any(not any(c["type"] == "Available" and c["status"] == "True" for c in x["conditions"])
                             or any(c["type"] in {"Degraded", "Progressing"} and c["status"] == "True" for c in x["conditions"])
                             for x in report["calico"]):
            report["errors"].append("Calico not fully available")
    except ValueError as exc:
        report["errors"].append("Calico: " + str(exc))
    report["checks_passed"] = not report["errors"]
    write_json(out / "snapshot.json", report)
    print(out)
    return 0 if report["checks_passed"] else 1


def pod_summary(pod):
    status = pod.get("status", {})
    return {"name": pod["metadata"]["name"], "uid": pod["metadata"]["uid"],
            "labels": pod["metadata"].get("labels", {}), "node": pod["spec"].get("nodeName"),
            "ip": status.get("podIP"), "ready": is_ready(pod),
            "service_account": pod["spec"].get("serviceAccountName", "default")}


def service_snapshot(args):
    cfg = read_config(args.config)
    name = getattr(args, "service", None) or cfg["target_service"]
    checked = dict(cfg, target_service=name)
    renderer.validate(checked)
    guard(args.context)
    svc = kjson(args.context, "-n", cfg["namespace"], "get", "service", name)
    selector = svc["spec"].get("selector", {})
    selected = ",".join(key + "=" + value for key, value in sorted(selector.items()))
    pods = kjson(args.context, "-n", cfg["namespace"], "get", "pods", "-l", selected)["items"] if selector else []
    slices = kjson(args.context, "-n", cfg["namespace"], "get", "endpointslices", "-l", "kubernetes.io/service-name=" + name)["items"]
    summaries = [pod_summary(p) for p in pods]
    by_uid = {p["uid"]: p for p in summaries}
    errors = []
    ready_endpoints = []
    for item in slices:
        for endpoint in item.get("endpoints") or []:
            if endpoint.get("conditions", {}).get("ready") is not True:
                continue
            ref = endpoint.get("targetRef", {})
            pod = by_uid.get(ref.get("uid"))
            mapped = (pod is not None and ref.get("kind") == "Pod" and ref.get("name") == pod["name"]
                      and pod["ready"] and pod["ip"] in endpoint.get("addresses", []))
            ready_endpoints.append({"slice": item["metadata"]["name"], "addresses": endpoint.get("addresses", []),
                                    "target_ref": ref, "matches_ready_selected_pod": mapped})
            if not mapped:
                errors.append("Ready endpoint does not map to a Ready selected Pod: " + item["metadata"]["name"])
    if not selector:
        errors.append("Service has no selector")
    if not ready_endpoints:
        errors.append("Service has no verified Ready endpoint")
    report = {"test": "Service-evidence", "time": timestamp(), "source": source_info(), "context": args.context,
              "namespace": cfg["namespace"], "service": {"name": name, "uid": svc["metadata"]["uid"],
                  "type": svc["spec"].get("type"), "cluster_ip": svc["spec"].get("clusterIP"), "selector": selector,
                  "ports": svc["spec"].get("ports", [])}, "pods": summaries, "ready_endpoints": ready_endpoints,
              "endpoint_slices": [{"name": e["metadata"]["name"], "endpoints": e.get("endpoints") or [],
                                    "ports": e.get("ports", [])} for e in slices],
              "checks_passed": not errors, "errors": errors,
              "note": "Capture before/after TV2 restart/scale or SVC04 repair; HTTP/DNS and peer verification still required"}
    out = new_run(args.output)
    write_json(out / "service-snapshot.json", report)
    print(out)
    return 0 if report["checks_passed"] else 1


def validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment
            or "REPLACE_ME" in url or any(c.isspace() for c in url)):
        raise ValueError("Use a real http(s) URL without credentials, query, fragment or whitespace")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Invalid URL port")
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_status(opener, url, timeout):
    try:
        with opener.open(url, timeout=timeout) as response:
            # Read the complete lab response, with a size cap, without saving its body.
            # urllib timeout is a socket inactivity timeout, not a wall-clock deadline.
            limit = 1024 * 1024
            declared = response.getheader("Content-Length")
            expected = int(declared) if declared is not None else None
            if expected is not None and (expected < 0 or expected > limit):
                return None, "Response body length is invalid or exceeds the 1 MiB limit"
            body = response.read(limit + 1)
            if len(body) > limit:
                return None, "Response body exceeds the 1 MiB limit; not validated"
            if expected is not None and len(body) != expected:
                return None, "HTTP response body was truncated"
            return response.status, None
    except urllib.error.HTTPError as exc:
        exc.close()
        return exc.code, None
    except http.client.IncompleteRead:
        return None, "HTTP response body or chunk framing was truncated"
    except http.client.HTTPException as exc:
        return None, "HTTP protocol error: " + type(exc).__name__
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, str(exc)
    except (ValueError, UnicodeError) as exc:
        return None, "Invalid HTTP response or URL: " + type(exc).__name__


def traffic(args):
    validate_url(args.url)
    if not (1 <= args.duration <= 600 and 0.1 <= args.interval <= 60 and 1 <= args.timeout <= 30):
        raise ValueError("duration 1..600s, interval 0.1..60s, timeout 1..30s required")
    out = new_run(args.output)
    opener = urllib.request.build_opener(NoRedirect())
    started = time.monotonic()
    report = {"test": "OBS01-traffic", "url": args.url, "started": timestamp(),
              "note": "HTTP alone does not establish an internal mesh edge; verify Prometheus/Kiali",
              "timeout_semantics": "Socket inactivity timeout; slow streaming can exceed duration plus timeout",
              "interrupted": False, "requests": []}
    completed = False
    try:
        while time.monotonic() - started < args.duration:
            status, error = request_status(opener, args.url, args.timeout)
            report["requests"].append({"time": timestamp(), "status": status, "error": error})
            remaining = args.duration - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(min(args.interval, remaining))
        completed = True
    except KeyboardInterrupt:
        report["interrupted"] = True
    finally:
        report["finished"] = timestamp()
        report["completed"] = completed
        report["all_http_200"] = completed and bool(report["requests"]) and all(x["status"] == 200 for x in report["requests"])
        write_json(out / "traffic.json", report)
        print(out)
    return 130 if report["interrupted"] else (0 if report["all_http_200"] else 1)


def probe_match(expected, dns, response):
    if dns["exit_code"] != 0 or not dns["stdout"]:
        return False  # Missing DNS tooling/DNS failure is never a successful policy test.
    if expected == "network-block":
        return response["exit_code"] in {7, 28} and response["stdout"] == "000"
    return response["exit_code"] == 0 and response["stdout"] == expected


def probe(args):
    cfg = read_config(args.config)
    if "GET" not in cfg["allowed_http_methods"]:
        raise ValueError("This probe implements the GET lab; agree a GET API with TV2 first")
    if args.path not in cfg["allowed_http_paths"] or "*" in args.path:
        raise ValueError("--path must be an explicit path in allowed_http_paths")
    guard(args.context)
    pod = kjson(args.context, "-n", cfg["namespace"], "get", "pod", args.pod)
    containers = pod["spec"]["containers"] + pod["spec"].get("ephemeralContainers", [])
    if args.container == "istio-proxy" or not any(c["name"] == args.container for c in containers):
        raise ValueError("Choose the app/debug container with curl and getent, not istio-proxy")
    if not proxy_ready(pod):
        raise ValueError("Probe source must have a Ready sidecar for C1-C4")
    host = cfg["target_service"] + "." + cfg["namespace"] + ".svc.cluster.local"
    url = "http://" + host + ":" + str(cfg["target_service_port"]) + args.path
    validate_url(url)
    out = new_run(args.output)
    policies = {}
    root_policies = {}
    root_namespace = getattr(args, "mesh_root_namespace", "istio-system")
    evidence_errors = []
    for kind in ("networkpolicies", "authorizationpolicies.security.istio.io", "peerauthentications.security.istio.io"):
        try:
            policies[kind] = [{"name": p["metadata"]["name"], "spec": p["spec"]}
                              for p in kjson(args.context, "-n", cfg["namespace"], "get", kind)["items"]]
        except ValueError as exc:
            evidence_errors.append("Cannot read application policies: " + str(exc))
    for kind in ("authorizationpolicies.security.istio.io", "peerauthentications.security.istio.io"):
        try:
            root_policies[kind] = [{"name": p["metadata"]["name"], "spec": p["spec"]}
                                  for p in kjson(args.context, "-n", root_namespace, "get", kind)["items"]]
        except ValueError as exc:
            evidence_errors.append("Cannot read mesh root policies: " + str(exc))
    endpoints = kjson(args.context, "-n", cfg["namespace"], "get", "endpointslices",
                      "-l", "kubernetes.io/service-name=" + cfg["target_service"])
    has_ready_endpoint = any(e.get("conditions", {}).get("ready") is True
                             for s in endpoints["items"] for e in (s.get("endpoints") or []))
    prefix = ["-n", cfg["namespace"], "exec", args.pod, "-c", args.container, "--"]
    dns = kubectl(args.context, *prefix, "getent", "hosts", host)
    result = kubectl(args.context, *prefix, "curl", "--noproxy", "*", "-sS", "--max-time", "10", "-o", "/dev/null", "-w", "%{http_code}", url)
    report = {"time": timestamp(), "context": args.context, "namespace": cfg["namespace"],
              "source": source_info(), "phase": getattr(args, "phase", None),
              "pod": args.pod, "uid": pod["metadata"]["uid"], "labels": pod["metadata"].get("labels", {}),
              "source_node": pod["spec"].get("nodeName"), "source_ip": pod.get("status", {}).get("podIP"),
              "service_account": pod["spec"].get("serviceAccountName", "default"), "container": args.container,
              "url": url, "expected": args.expect, "dns": dns, "response": result,
              "namespace_policies": policies,
              "mesh_root_namespace": root_namespace, "root_policies": root_policies, "evidence_errors": evidence_errors,
              "endpoint_slices": [{"name": e["metadata"]["name"], "endpoints": e.get("endpoints") or [],
                                    "ports": e.get("ports", [])} for e in endpoints["items"]],
              "target_has_ready_endpoint": has_ready_endpoint,
              "matched_expectation": not evidence_errors and has_ready_endpoint and probe_match(args.expect, dns, result),
              "upstream_error_observed": result["exit_code"] == 0 and result["stdout"] in {"503", "504"},
              "note": "Record active policies and baseline/recovery; matching a timeout alone does not identify its cause"}
    write_json(out / "probe.json", report)
    print(out)
    return 0 if report["matched_expectation"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("package", help="Offline: package explicit local source files, including uncommitted TV3 changes")
    p.set_defaults(func=package)
    p = sub.add_parser("verify-package", help="Offline: after extraction, verify source files against overlay manifest")
    p.add_argument("manifest", type=pathlib.Path)
    p.set_defaults(func=verify_package)
    p = sub.add_parser("render", help="Offline: generate per-layer policies and isolated selector lab")
    p.add_argument("config", type=pathlib.Path)
    p.set_defaults(func=render)
    p = sub.add_parser("snapshot", help="Read-only: capture TV3 readiness and runtime versions; no Rancher dependency")
    p.add_argument("--context", required=True)
    p.set_defaults(func=snapshot)
    p = sub.add_parser("service-snapshot", help="Read-only: record Service, selected Pods and EndpointSlice before/after a change")
    p.add_argument("config", type=pathlib.Path)
    p.add_argument("--context", required=True)
    p.add_argument("--service", help="Optional isolated SVC04 Service; default target_service from config")
    p.set_defaults(func=service_snapshot)
    p = sub.add_parser("traffic", help="Generate bounded HTTP GET traffic and record status/time")
    p.add_argument("url")
    p.add_argument("--duration", type=float, default=180)
    p.add_argument("--interval", type=float, default=1)
    p.add_argument("--timeout", type=float, default=10)
    p.set_defaults(func=traffic)
    p = sub.add_parser("probe", help="Record one DNS + HTTP test from an existing mesh source")
    p.add_argument("config", type=pathlib.Path)
    p.add_argument("--context", required=True)
    p.add_argument("--pod", required=True)
    p.add_argument("--container", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--expect", choices=["200", "403", "network-block"], required=True)
    p.add_argument("--phase", help="Evidence label such as C1, C3, C3-recovered; never grants acceptance automatically")
    p.add_argument("--mesh-root-namespace", default="istio-system")
    p.set_defaults(func=probe)
    for child in sub.choices.values():
        if child.get_default("func") is not verify_package:
            child.add_argument("--output", type=pathlib.Path, help="New directory only; default .generated/tv3-*")
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
