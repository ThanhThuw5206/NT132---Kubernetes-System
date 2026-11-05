import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("renderer", ROOT / "scripts/render-application.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

class ApplicationRendererTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "namespace": "test-app", "entry_service": "entry", "entry_service_port": 8080,
            "public_path_prefix": "/", "target_service": "target", "target_service_port": 8081,
            "target_port": 9090, "target_labels": {"app": "target"}, "allowed_caller_labels": {"app": "caller"},
            "allowed_service_account": "caller-account", "trust_domain": "cluster.local",
            "allowed_http_methods": ["GET"], "allowed_http_paths": ["/health"],
            "permit_prometheus_scrape": True,
        }

    def test_service_port_and_pod_port_stay_distinct(self):
        values = renderer.resources(self.cfg)
        rule = values["network-policy.json"]["spec"]["ingress"][0]
        self.assertEqual(rule["ports"][0]["port"], 9090)
        route = values["route.json"]["spec"]["http"][0]["route"][0]
        self.assertEqual(route["destination"]["port"]["number"], 8080)

    def test_identity_and_same_namespace_selector(self):
        values = renderer.resources(self.cfg)
        auth = values["authorization.json"]["spec"]["rules"][0]
        self.assertEqual(auth["from"][0]["source"]["principals"], ["cluster.local/ns/test-app/sa/caller-account"])
        source = values["network-policy.json"]["spec"]["ingress"][0]["from"][0]
        self.assertEqual(source, {"podSelector": {"matchLabels": {"app": "caller"}}})

    def test_metrics_exception_requires_both_namespace_and_pod_selector(self):
        rules = renderer.resources(self.cfg)["network-policy.json"]["spec"]["ingress"]
        source = rules[1]["from"][0]
        self.assertIn("namespaceSelector", source)
        self.assertIn("podSelector", source)
        self.cfg["permit_prometheus_scrape"] = False
        self.assertEqual(len(renderer.resources(self.cfg)["network-policy.json"]["spec"]["ingress"]), 1)

    def test_rejects_placeholder_system_namespace_boolean_port_and_empty_selector(self):
        for field, value in [("namespace", "REPLACE_ME"), ("namespace", "kube-system"),
                             ("target_port", True), ("target_labels", {}),
                             ("public_path_prefix", "https://invalid"), ("trust_domain", "*"),
                             ("allowed_http_methods", ["*"])]:
            cfg = copy.deepcopy(self.cfg)
            cfg[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                renderer.resources(cfg)

    def test_traffic_route_does_not_reference_source_workload(self):
        values = renderer.resources(self.cfg)
        self.assertEqual(values["gateway.json"]["spec"]["selector"], {"istio": "ingressgateway"})
        self.assertEqual(values["route.json"]["spec"]["gateways"], ["application-gateway"])

if __name__ == "__main__":
    unittest.main()
