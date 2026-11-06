"""Working-tree handover and Kubernetes Service evidence, with no cloud access."""
import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tv3_handover", ROOT / "scripts/tv3.py")
tv3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tv3)
fixture_spec = importlib.util.spec_from_file_location("tv3_fixtures", ROOT / "tests/test_tv3.py")
fixtures = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixtures)


class HandoverTests(unittest.TestCase):
    def test_package_includes_uncommitted_allowlisted_content_and_verifies_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "docs").mkdir()
            (root / "scripts").mkdir()
            (root / "config").mkdir()
            (root / "scripts/new-local.py").write_text("# local uncommitted source\n", encoding="utf-8")
            (root / "config/application.json").write_text('{"private":"not for sharing"}', encoding="utf-8")
            (root / "docs/tv3-package-files.txt").write_text("scripts/new-local.py\n", encoding="utf-8")
            out = root / "output"
            with mock.patch.object(tv3, "ROOT", root), mock.patch.object(tv3, "source_info", return_value={"base_commit": "17aaed9"}), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tv3.package(SimpleNamespace(output=out)), 0)
                with zipfile.ZipFile(out / "tv3-overlay.zip") as archive:
                    self.assertEqual(set(archive.namelist()), {"scripts/new-local.py", "tv3-overlay-manifest.json"})
                    self.assertIn(b"uncommitted", archive.read("scripts/new-local.py"))
                args = SimpleNamespace(manifest=out / "manifest.json")
                self.assertEqual(tv3.verify_package(args), 0)
                (root / "scripts/new-local.py").write_text("# changed after packaging\n", encoding="utf-8")
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(tv3.verify_package(args), 1)

    def test_package_rejects_traversal_and_private_application_config(self):
        for name in ("../outside.txt", "C:/outside.txt", "config/application.json", ".git/config", "private/key.key"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp, mock.patch.object(tv3, "ROOT", pathlib.Path(tmp)):
                listing = pathlib.Path(tmp) / "docs/tv3-package-files.txt"
                listing.parent.mkdir()
                listing.write_text(name + "\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    tv3.package_paths()

    def test_proxy_readiness_accepts_regular_and_native_but_not_completed_init(self):
        regular = {"spec": {"containers": [{"name": "istio-proxy"}]}, "status": {
            "containerStatuses": [{"name": "istio-proxy", "ready": True}]}}
        native = {"spec": {"containers": [{"name": "app"}], "initContainers": [{"name": "istio-proxy", "restartPolicy": "Always"}]},
                  "status": {"initContainerStatuses": [{"name": "istio-proxy", "ready": True}]}}
        self.assertTrue(tv3.proxy_ready(regular))
        self.assertTrue(tv3.proxy_ready(native))
        native["spec"]["initContainers"][0].pop("restartPolicy")
        self.assertFalse(tv3.proxy_ready(native))


class ServiceEvidenceTests(unittest.TestCase):
    def test_empty_endpoint_slice_still_writes_failed_selector_evidence(self):
        # Empty Services can be serialized with null, empty or omitted endpoints.
        for fields in ({"endpoints": None}, {"endpoints": []}, {}):
            def fake_json(context, *args):
                if "service" in args:
                    return {"metadata": {"name": "target", "uid": "service-uid"}, "spec": {
                        "type": "ClusterIP", "clusterIP": "10.96.0.1", "selector": {"app": "missing"},
                        "ports": [{"port": 8081, "targetPort": 9090}]}}
                if "pods" in args:
                    return {"items": []}
                return {"items": [{"metadata": {"name": "empty-slice"}, **fields}]}
            with self.subTest(fields=fields), tempfile.TemporaryDirectory() as tmp, mock.patch.object(tv3, "guard"), \
                 mock.patch.object(tv3, "kjson", side_effect=fake_json), contextlib.redirect_stdout(io.StringIO()):
                cfg = pathlib.Path(tmp) / "input.json"
                tv3.write_json(cfg, fixtures.config())
                args = SimpleNamespace(config=cfg, context="offline-mock", output=pathlib.Path(tmp) / "out")
                self.assertEqual(tv3.service_snapshot(args), 1)
                report = json.loads((args.output / "service-snapshot.json").read_text(encoding="utf-8"))
                self.assertFalse(report["checks_passed"])
                self.assertEqual(report["ready_endpoints"], [])
                self.assertEqual(report["endpoint_slices"][0]["endpoints"], [])
                self.assertIn("Service has no verified Ready endpoint", report["errors"])

    def test_ready_endpoint_must_match_selected_pod_uid_and_address(self):
        for endpoint_uid, expected_exit in [("pod-uid", 0), ("stale-pod-uid", 1)]:
            def fake_json(context, *args):
                if "service" in args:
                    return {"metadata": {"name": "target", "uid": "service-uid"}, "spec": {
                        "type": "ClusterIP", "clusterIP": "10.96.0.1", "selector": {"app": "target"},
                        "ports": [{"port": 8081, "targetPort": 9090}]}}
                if "pods" in args:
                    return {"items": [{"metadata": {"name": "target-pod", "uid": "pod-uid", "labels": {"app": "target"}},
                        "spec": {"nodeName": "wk-02"}, "status": {"podIP": "10.244.2.1", "conditions": [{"type": "Ready", "status": "True"}]}}]}
                return {"items": [{"metadata": {"name": "target-slice"}, "ports": [{"port": 9090}], "endpoints": [{
                    "addresses": ["10.244.2.1"], "conditions": {"ready": True},
                    "targetRef": {"kind": "Pod", "name": "target-pod", "uid": endpoint_uid}}]}]}

            with self.subTest(uid=endpoint_uid), tempfile.TemporaryDirectory() as tmp, mock.patch.object(tv3, "guard"), \
                 mock.patch.object(tv3, "kjson", side_effect=fake_json), contextlib.redirect_stdout(io.StringIO()):
                cfg = pathlib.Path(tmp) / "input.json"
                tv3.write_json(cfg, fixtures.config())
                args = SimpleNamespace(config=cfg, context="offline-mock", output=pathlib.Path(tmp) / "out")
                self.assertEqual(tv3.service_snapshot(args), expected_exit)
                report = json.loads((args.output / "service-snapshot.json").read_text(encoding="utf-8"))
                self.assertEqual(report["service"]["uid"], "service-uid")
                self.assertEqual(report["checks_passed"], expected_exit == 0)
                self.assertEqual(report["pods"][0]["node"], "wk-02")


if __name__ == "__main__":
    unittest.main()
