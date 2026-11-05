import contextlib
import copy
import http.server
import importlib.util
import io
import json
import pathlib
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tv3", ROOT / "scripts/tv3.py")
tv3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tv3)


def config():
    return {
        "namespace": "lab-app", "entry_service": "entry", "entry_service_port": 8080,
        "public_path_prefix": "/", "target_service": "target", "target_service_port": 8081,
        "target_port": 9090, "target_labels": {"app": "target"},
        "allowed_caller_labels": {"app": "caller"}, "allowed_service_account": "caller-sa",
        "trust_domain": "cluster.local", "allowed_http_methods": ["GET"],
        "allowed_http_paths": ["/health"], "permit_prometheus_scrape": True,
    }


class TV3Tests(unittest.TestCase):
    def test_selector_lab_never_reuses_the_original_service_name(self):
        cfg = config()
        cfg["target_service"] = "a" * 63
        original = copy.deepcopy(cfg)
        values = tv3.selector_resources(cfg)
        for service in values.values():
            self.assertLessEqual(len(service["metadata"]["name"]), 63)
            self.assertNotEqual(service["metadata"]["name"], cfg["target_service"])
            self.assertEqual(service["spec"]["ports"][0]["port"], 8081)
            self.assertEqual(service["spec"]["ports"][0]["targetPort"], 9090)
            self.assertNotIn("clusterIP", service["spec"])
        self.assertNotEqual(values["selector-broken.json"]["spec"]["selector"], cfg["target_labels"])
        self.assertEqual(values["selector-fixed.json"]["spec"]["selector"], cfg["target_labels"])
        self.assertEqual(cfg, original)

    def test_invalid_config_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "input.json"
            out = pathlib.Path(tmp) / "out"
            cfg = config()
            cfg["target_service"] = "REPLACE_ME"
            tv3.write_json(source, cfg)
            with self.assertRaises(ValueError):
                tv3.render(SimpleNamespace(config=source, output=out))
            self.assertFalse(out.exists())

    def test_render_writes_individual_layers_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "input.json"
            out = pathlib.Path(tmp) / "out"
            tv3.write_json(source, config())
            args = SimpleNamespace(config=source, output=out)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tv3.render(args), 0)
            for name in ("network-policy.json", "authorization.json", "mtls.json", "selector-broken.json", "selector-fixed.json"):
                self.assertIn("apiVersion", json.loads((out / name).read_text(encoding="utf-8")))
            with self.assertRaises(FileExistsError):
                tv3.render(args)

    def test_network_block_never_accepts_missing_tool_dns_or_api_failure(self):
        ok_dns = {"exit_code": 0, "stdout": "10.0.0.1 target"}
        for code in (1, 6, 35, 60, 124, 126, 127):
            self.assertFalse(tv3.probe_match("network-block", ok_dns, {"exit_code": code, "stdout": "000"}))
        for code in (7, 28):
            self.assertTrue(tv3.probe_match("network-block", ok_dns, {"exit_code": code, "stdout": "000"}))
            self.assertFalse(tv3.probe_match("network-block", {"exit_code": 1, "stdout": ""}, {"exit_code": code, "stdout": "000"}))
        self.assertFalse(tv3.probe_match("403", ok_dns, {"exit_code": 0, "stdout": "200"}))
        self.assertTrue(tv3.probe_match("403", ok_dns, {"exit_code": 0, "stdout": "403"}))

    def test_traffic_rejects_credentials_placeholders_and_query_strings(self):
        for value in ("file:///tmp/data", "http://user:pass@localhost/", "http://localhost/?token=abc",
                      "http://localhost/#secret", "http://localhost/REPLACE_ME", "http://local host/"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                tv3.validate_url(value)
        self.assertEqual(tv3.validate_url("http://127.0.0.1:8080/productpage"), "http://127.0.0.1:8080/productpage")

    def test_guard_rejects_the_wrong_cluster_before_runtime_operations(self):
        with mock.patch.object(tv3, "kubectl", return_value={"exit_code": 0, "stdout": "ok"}), \
             mock.patch.object(tv3, "kjson", return_value={"status": {"addresses": [{"type": "InternalIP", "address": "10.1.0.10"}]}}):
            with self.assertRaisesRegex(ValueError, "Wrong cluster"):
                tv3.guard("other")

    def test_subprocess_uses_explicit_context_and_no_shell(self):
        with mock.patch.object(tv3, "command", return_value={"exit_code": 0}) as run:
            tv3.kubectl("nt132", "get", "nodes")
            self.assertEqual(run.call_args.args[0], ["kubectl", "--context", "nt132", "--request-timeout=20s", "get", "nodes"])

    def test_snapshot_does_not_require_rancher_or_accept_stale_rollout_status(self):
        for observed, expected_exit in [(2, 0), (1, 1)]:
            def fake_json(context, *args):
                if args == ("get", "nodes"):
                    return {"items": [{"metadata": {"name": name}, "status": {
                        "conditions": [{"type": "Ready", "status": "True"}], "nodeInfo": {},
                        "addresses": [{"type": "InternalIP", "address": ip}]}}
                        for name, ip in [("cp-01", "10.20.0.10"), ("wk-01.zone.c.project.internal", "10.20.0.11"),
                                         ("wk-02.zone.c.project.internal", "10.20.0.12")]]}
                if args == ("get", "tigerastatus"):
                    return {"items": [{"metadata": {"name": "calico"}, "status": {
                        "conditions": [{"type": "Available", "status": "True"}]}}]}
                self.assertNotIn("rancher", args)
                return {"metadata": {"generation": 2}, "spec": {"replicas": 1, "template": {"spec": {
                    "containers": [{"image": "test:offline"}]}}}, "status": {
                    "observedGeneration": observed, "updatedReplicas": 1, "availableReplicas": 1}}

            with self.subTest(observed=observed), tempfile.TemporaryDirectory() as tmp, \
                 mock.patch.object(tv3, "guard"), mock.patch.object(tv3, "kjson", side_effect=fake_json), \
                 mock.patch.object(tv3, "command", return_value={"exit_code": 0, "stdout": "v3.19.0"}), \
                 contextlib.redirect_stdout(io.StringIO()):
                args = SimpleNamespace(context="mock-offline", output=pathlib.Path(tmp) / "snapshot")
                self.assertEqual(tv3.snapshot(args), expected_exit)
                report = json.loads((args.output / "snapshot.json").read_text(encoding="utf-8"))
                self.assertEqual(report["checks_passed"], expected_exit == 0)
                self.assertEqual(report["node_aliases"]["wk-01"], "wk-01.zone.c.project.internal")

    def test_probe_requires_a_ready_target_before_accepting_network_block(self):
        for ready, expected_exit in [(False, 1), (True, 0)]:
            def fake_json(context, *args):
                if "pod" in args:
                    return {"metadata": {"uid": "offline-uid", "labels": {"app": "control"}},
                            "spec": {"serviceAccountName": "control", "containers": [{"name": "debug"}, {"name": "istio-proxy"}]},
                            "status": {"containerStatuses": [{"name": "istio-proxy", "ready": True}]}}
                if "endpointslices" in args:
                    return {"items": [{"metadata": {"name": "target-slice"}, "endpoints": [
                        {"conditions": {"ready": ready}, "addresses": ["10.244.1.1"]}]}]}
                return {"items": []}

            with self.subTest(ready=ready), tempfile.TemporaryDirectory() as tmp, \
                 mock.patch.object(tv3, "guard"), mock.patch.object(tv3, "kjson", side_effect=fake_json), \
                 mock.patch.object(tv3, "kubectl", side_effect=[{"exit_code": 0, "stdout": "10.96.0.1 target"},
                                                             {"exit_code": 28, "stdout": "000", "stderr": "timeout"}]), \
                 contextlib.redirect_stdout(io.StringIO()):
                source = pathlib.Path(tmp) / "config.json"
                tv3.write_json(source, config())
                args = SimpleNamespace(config=source, context="mock-offline", pod="control", container="debug", path="/health",
                                       expect="network-block", output=pathlib.Path(tmp) / "probe")
                self.assertEqual(tv3.probe(args), expected_exit)
                report = json.loads((args.output / "probe.json").read_text(encoding="utf-8"))
                self.assertEqual(report["matched_expectation"], ready)
                self.assertIn("namespace_policies", report)

    def test_traffic_records_http_failure_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(tv3.time, "monotonic", side_effect=[0, 0, 2, 2]), \
             mock.patch.object(tv3, "request_status", return_value=(503, None)), contextlib.redirect_stdout(io.StringIO()):
            out = pathlib.Path(tmp) / "traffic"
            args = SimpleNamespace(url="http://127.0.0.1/", duration=1, interval=1, timeout=1, output=out)
            self.assertEqual(tv3.traffic(args), 1)
            report = json.loads((out / "traffic.json").read_text(encoding="utf-8"))
            self.assertFalse(report["all_http_200"])
            self.assertEqual(report["requests"][0]["status"], 503)
            self.assertTrue(report["started"].endswith("+07:00"))


class TrafficIntegrationTests(unittest.TestCase):
    def test_real_http_statuses_and_redirects_are_not_hidden(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/ok")
                else:
                    self.send_response(200 if self.path == "/ok" else 403)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            opener = tv3.urllib.request.build_opener(tv3.NoRedirect())
            for path, expected in [("/ok", 200), ("/denied", 403), ("/redirect", 302)]:
                status, error = tv3.request_status(opener, "http://127.0.0.1:" + str(server.server_port) + path, 1)
                self.assertEqual(status, expected)
                self.assertIsNone(error)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
