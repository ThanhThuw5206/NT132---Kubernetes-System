import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location(
    "cluster_nodes", pathlib.Path(__file__).resolve().parents[1] / "scripts/cluster-nodes.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ClusterNodeTests(unittest.TestCase):
    def payload(self):
        return {"items": [
            {"metadata": {"name": name}, "status": {"addresses": [
                {"type": "InternalIP", "address": ip}]}}
            for name, ip in [("cp-01", "10.20.0.10"),
                             ("wk-01.zone.c.project.internal", "10.20.0.11"),
                             ("wk-02.zone.c.project.internal", "10.20.0.12")]]}

    def test_fqdn_and_unordered_nodes(self):
        payload = self.payload()
        payload["items"].reverse()
        self.assertEqual(module.resolve(payload),
                         ["cp-01", "wk-01.zone.c.project.internal", "wk-02.zone.c.project.internal"])

    def test_missing_and_duplicate_ip_rejected(self):
        payload = self.payload()
        payload["items"].pop()
        with self.assertRaises(ValueError):
            module.resolve(payload)
        payload = self.payload()
        payload["items"].append(payload["items"][1])
        with self.assertRaises(ValueError):
            module.resolve(payload)

    def test_external_ip_is_not_used(self):
        payload = self.payload()
        payload["items"][1]["status"]["addresses"][0]["type"] = "ExternalIP"
        with self.assertRaises(ValueError):
            module.resolve(payload)
