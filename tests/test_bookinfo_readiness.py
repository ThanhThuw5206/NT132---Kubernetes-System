import contextlib
import copy
import importlib.util
import io
import json
import pathlib
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bookinfo_readiness", ROOT / "scripts/check-bookinfo-pods.py")
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


def pods(mode="mesh", native=False):
    items = []
    for workload, (app, version) in readiness.EXPECTED.items():
        pod = {"metadata": {"name": workload + "-pod", "namespace": "bookinfo",
                            "labels": {"app": app, "version": version}},
               "spec": {"containers": [{"name": app}]},
               "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}],
                          "containerStatuses": [{"name": app, "ready": True}]}}
        if mode == "mesh":
            if native:
                pod["spec"]["initContainers"] = [{"name": "istio-proxy", "restartPolicy": "Always"}]
                pod["status"]["initContainerStatuses"] = [{"name": "istio-proxy", "ready": True}]
            else:
                pod["spec"]["containers"].append({"name": "istio-proxy"})
                pod["status"]["containerStatuses"].append({"name": "istio-proxy", "ready": True})
        items.append(pod)
    return {"apiVersion": "v1", "kind": "PodList", "items": items}


class BookinfoReadinessTests(unittest.TestCase):
    def test_regular_and_native_proxy_pass_without_fixed_container_count(self):
        for native in (False, True):
            with self.subTest(native=native):
                payload = pods(native=native)
                report = readiness.evaluate(payload)
                self.assertTrue(report["ready"])
                self.assertEqual(len(payload["items"][0]["spec"]["containers"]), 1 if native else 2)
                self.assertTrue(all(app["ready"] for app in report["apps"].values()))

    def test_unready_app_proxy_pod_and_nonrunning_phase_cannot_pass(self):
        for change in ("app", "proxy", "condition", "phase"):
            with self.subTest(change=change):
                payload = pods(native=True)
                pod = payload["items"][0]
                if change == "app":
                    pod["status"]["containerStatuses"][0]["ready"] = False
                elif change == "proxy":
                    pod["status"]["initContainerStatuses"][0]["ready"] = False
                elif change == "condition":
                    pod["status"]["conditions"][0]["status"] = "False"
                else:
                    pod["status"]["phase"] = "Pending"
                self.assertFalse(readiness.evaluate(payload)["ready"])
        payload = pods()
        payload["items"][0]["status"]["containerStatuses"][1]["ready"] = False
        self.assertFalse(readiness.evaluate(payload)["ready"])
        payload = pods(native=True)
        payload["items"][0]["spec"]["initContainers"][0]["restartPolicy"] = "OnFailure"
        self.assertFalse(readiness.evaluate(payload)["ready"])

    def test_missing_app_and_active_unwanted_reviews_fail(self):
        payload = pods()
        del payload["items"][0]
        self.assertIn("details-v1", " ".join(readiness.evaluate(payload)["errors"]))
        for version in ("v1", "v3"):
            with self.subTest(version=version):
                payload = pods()
                other = copy.deepcopy(payload["items"][2])
                other["metadata"]["name"] = "reviews-" + version + "-pod"
                other["metadata"]["labels"]["version"] = version
                payload["items"].append(other)
                self.assertFalse(readiness.evaluate(payload)["ready"])

    def test_terminating_pods_are_excluded_and_other_namespaces_do_not_count(self):
        payload = pods()
        old = copy.deepcopy(payload["items"][0])
        old["metadata"].update(name="old-pod", deletionTimestamp="2026-11-06T00:00:00Z")
        old["status"]["conditions"][0]["status"] = "False"
        payload["items"].append(old)
        report = readiness.evaluate(payload)
        self.assertTrue(report["ready"])
        self.assertEqual(report["ignored_terminating_pods"], ["old-pod"])
        payload["items"][0]["metadata"]["namespace"] = "other"
        self.assertFalse(readiness.evaluate(payload)["ready"])
        self.assertFalse(readiness.evaluate({"kind": "PodList", "items": [old]})["ready"])

    def test_baseline_requires_no_proxy_in_regular_or_init_containers(self):
        self.assertTrue(readiness.evaluate(pods(mode="baseline"), baseline=True)["ready"])
        for native in (False, True):
            with self.subTest(native=native):
                self.assertFalse(readiness.evaluate(pods(native=native), baseline=True)["ready"])
        payload = pods(mode="baseline")
        unknown = copy.deepcopy(pods()["items"][0])
        unknown["metadata"]["name"] = "debug"
        unknown["metadata"]["labels"] = {"app": "debug"}
        payload["items"].append(unknown)
        self.assertFalse(readiness.evaluate(payload, baseline=True)["ready"])

    def test_cli_json_summary_unmet_exit_and_malformed_input(self):
        for payload, args, expected in ((pods(native=True), [], 0), (pods(mode="baseline"), [], 1),
                                        (pods(mode="baseline"), ["--baseline"], 0),
                                        ({"kind": "PodList", "items": "invalid"}, [], 2)):
            with self.subTest(expected=expected), mock.patch.object(readiness.sys, "stdin", io.StringIO(json.dumps(payload))), \
                    contextlib.redirect_stdout(output := io.StringIO()), contextlib.redirect_stderr(error := io.StringIO()):
                self.assertEqual(readiness.main(args), expected)
                if expected == 2:
                    self.assertEqual(output.getvalue(), "")
                    self.assertIn("ERROR:", error.getvalue())
                else:
                    self.assertEqual(json.loads(output.getvalue())["ready"], expected == 0)
        with mock.patch.object(readiness.sys, "stdin", io.StringIO("not JSON")), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(readiness.main([]), 2)
        malformed = pods()
        malformed["items"][0]["status"]["containerStatuses"][0]["ready"] = "false"
        with self.assertRaises(ValueError):
            readiness.evaluate(malformed)
        custom = pods()
        for pod in custom["items"]:
            pod["metadata"]["namespace"] = "app-lab"
        with mock.patch.object(readiness.sys, "stdin", io.StringIO(json.dumps(custom))), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(readiness.main(["--namespace", "app-lab"]), 0)


if __name__ == "__main__":
    unittest.main()
