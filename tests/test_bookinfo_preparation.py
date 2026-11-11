import copy
import hashlib
import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_bookinfo", ROOT / "scripts/prepare-bookinfo.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class BookinfoPreparationTests(unittest.TestCase):
    def test_locked_source_baseline_preserves_identity_and_six_deployments(self):
        source, lock = prepare.load_source()
        before = copy.deepcopy(source)
        values = prepare.resources("bookinfo", source)
        self.assertEqual(source, before)
        self.assertEqual(lock["istio_version"], "1.30.7")
        self.assertEqual(values["namespace-baseline.json"]["metadata"]["labels"]["istio-injection"], "disabled")
        workload = values["workloads.json"]
        self.assertEqual(len(workload["items"]), 14)
        deployments = {item["metadata"]["name"]: item for item in workload["items"] if item["kind"] == "Deployment"}
        self.assertEqual(set(deployments), prepare.DEPLOYMENTS)
        self.assertEqual({name for name, value in deployments.items() if value["spec"]["replicas"] == 1},
                         {"details-v1", "ratings-v1", "reviews-v2", "productpage-v1"})
        for name, item in deployments.items():
            with self.subTest(name=name):
                pod = item["spec"]["template"]["spec"]
                self.assertNotIn("initContainers", pod)
                self.assertEqual(len(pod["containers"]), 1)
                component = name.rsplit("-", 1)[0]
                self.assertEqual(pod["serviceAccountName"], "bookinfo-" + component)
                self.assertEqual(item["metadata"]["namespace"], "bookinfo")
                for probe_name in ("startupProbe", "readinessProbe", "livenessProbe"):
                    self.assertEqual(pod["containers"][0][probe_name]["httpGet"], {"path": "/health", "port": 9080})
                self.assertGreaterEqual(pod["containers"][0]["startupProbe"]["failureThreshold"]
                                        * pod["containers"][0]["startupProbe"]["periodSeconds"], 180)
                self.assertEqual(pod["containers"][0]["resources"], prepare.RESOURCES[component])
                self.assertEqual(item["spec"]["template"]["metadata"]["annotations"]["sidecar.istio.io/rewriteAppHTTPProbers"], "true")
        for item in workload["items"]:
            if item["kind"] == "Service":
                self.assertEqual(item["spec"]["ports"][0]["targetPort"], 9080)

    def test_tampered_artifact_and_changed_version_are_rejected(self):
        for role in ("manifest_yaml", "manifest_json", "license"):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                source = root / "bookinfo"
                shutil.copytree(prepare.SOURCE, source)
                artifact = source / prepare.SOURCE_FILES[role]
                artifact.write_bytes(artifact.read_bytes() + b"\nchanged")
                with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                    prepare.prepare(output=root / "must-not-exist", source=source)
                self.assertFalse((root / "must-not-exist").exists())
        with tempfile.TemporaryDirectory() as tmp:
            version_file = pathlib.Path(tmp) / "versions.env"
            version_file.write_text("ISTIO_VERSION=0.0.0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                prepare.load_source(versions=version_file)

    def test_unexpected_topology_and_identity_cannot_be_rendered(self):
        source, _ = prepare.load_source()
        altered = copy.deepcopy(source)
        altered["items"][-1]["spec"]["template"]["spec"]["serviceAccountName"] = "default"
        with self.assertRaisesRegex(ValueError, "identity"):
            prepare.resources("bookinfo", altered)
        duplicate = copy.deepcopy(source)
        duplicate["items"][-1] = duplicate["items"][0]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            prepare.resources("bookinfo", duplicate)

    def test_preparation_report_hashes_and_output_non_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "generated"
            prepare.prepare(output=out)
            report = json.loads((out / "preparation.json").read_text(encoding="utf-8"))
            self.assertIn("no cluster validation", report["scope"])
            self.assertEqual(report["injection_baseline"], "disabled")
            self.assertEqual(set(report["outputs"]), {"namespace-baseline.json", "workloads.json"})
            for name, expected in report["outputs"].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), expected)
            original = (out / "workloads.json").read_bytes()
            with self.assertRaises(FileExistsError):
                prepare.prepare(output=out)
            self.assertEqual((out / "workloads.json").read_bytes(), original)
            for name in ("kube-system", "default", "Not-A-Namespace"):
                with self.subTest(namespace=name), self.assertRaises(ValueError):
                    prepare.prepare(namespace=name, output=pathlib.Path(tmp) / "invalid")
                self.assertFalse((pathlib.Path(tmp) / "invalid").exists())


if __name__ == "__main__":
    unittest.main()
