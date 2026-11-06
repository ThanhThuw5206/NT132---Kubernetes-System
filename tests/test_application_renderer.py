import copy
import importlib.util
import json
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

    def test_legacy_config_preserves_its_single_prefix_route(self):
        self.cfg["public_path_prefix"] = "/catalog"
        matches = renderer.resources(self.cfg)["route.json"]["spec"]["http"][0]["match"]
        self.assertEqual(matches, [{"uri": {"prefix": "/catalog"}}])

    def test_rejects_ambiguous_or_nonliteral_public_routes_and_unknown_config(self):
        for matches in ([], {}, [None], [{"regex": ".*"}],
                        [{"exact": "/a", "prefix": "/a"}],
                        [{"exact": "https://example.test/a"}], [{"prefix": "/a?b"}],
                        [{"exact": "/a#b"}], [{"prefix": "/a*"}],
                        [{"prefix": "/a\\b"}], [{"exact": "/a b"}],
                        [{"exact": "/a\x00b"}], [{"exact": True}],
                        [{"exact": "/a"}, {"exact": "/a"}]):
            cfg = copy.deepcopy(self.cfg)
            cfg["public_http_matches"] = matches
            with self.subTest(matches=matches), self.assertRaises(ValueError):
                renderer.resources(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["public_http_match"] = [{"exact": "/a"}]
        with self.assertRaises(ValueError):
            renderer.resources(cfg)
        del cfg["public_http_match"]
        del cfg["public_path_prefix"]
        with self.assertRaises(ValueError):
            renderer.resources(cfg)

    def test_bookinfo_routes_cover_ui_assets_and_api_without_exposing_other_paths(self):
        cfg = json.loads((ROOT / "apps/bookinfo/application.bookinfo.json").read_text(encoding="utf-8"))
        values = renderer.resources(cfg)
        route = values["route.json"]["spec"]["http"][0]
        matches = [match["uri"] for match in route["match"]]

        def is_routed(path):
            return any(path == match["exact"] if "exact" in match
                       else path.startswith(match["prefix"]) for match in matches)

        for path in ("/productpage", "/static/img/izzy.png", "/login", "/logout",
                     "/api/v1/products", "/api/v1/products/0", "/api/v1/products/0/reviews"):
            with self.subTest(path=path):
                self.assertTrue(is_routed(path))
        for path in ("/", "/health", "/metrics", "/admin", "/productpage-other", "/static-other/file",
                     "/login-other", "/api/v1/products-other", "/ratings/0"):
            with self.subTest(path=path):
                self.assertFalse(is_routed(path))
        self.assertNotIn({"prefix": "/"}, matches)
        self.assertEqual(route["route"][0]["destination"], {
            "host": "productpage.bookinfo.svc.cluster.local", "port": {"number": 9080}})
        auth = values["authorization.json"]["spec"]["rules"][0]
        self.assertEqual(auth["from"][0]["source"]["principals"],
                         ["cluster.local/ns/bookinfo/sa/bookinfo-reviews"])
        self.assertEqual(auth["to"][0]["operation"], {"methods": ["GET"], "paths": ["/ratings/0"]})
        network = values["network-policy.json"]["spec"]
        self.assertEqual(network["podSelector"], {"matchLabels": {"app": "ratings"}})
        self.assertEqual(network["ingress"][0], {
            "from": [{"podSelector": {"matchLabels": {"app": "reviews"}}}],
            "ports": [{"protocol": "TCP", "port": 9080}]})

if __name__ == "__main__":
    unittest.main()
