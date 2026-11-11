"""Exercise NET01 orchestration with a fake kubectl; never talks to a cluster."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
if not BASH and os.name == "nt":
    candidate = pathlib.Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
    if candidate.exists():
        BASH = str(candidate)

MOCK = r'''#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >>"$MOCK_CALLS"
case "$*" in
  *'get --raw=/readyz'*) echo ok ;;
  *"get node cp-01 -o jsonpath="*) echo 10.20.0.10 ;;
  *'get nodes -o json'*)
    echo '{"items":[{"metadata":{"name":"cp-01"},"status":{"addresses":[{"type":"InternalIP","address":"10.20.0.10"}]}},{"metadata":{"name":"wk-01.zone.c.project.internal"},"status":{"addresses":[{"type":"InternalIP","address":"10.20.0.11"}]}},{"metadata":{"name":"wk-02.zone.c.project.internal"},"status":{"addresses":[{"type":"InternalIP","address":"10.20.0.12"}]}}]}' ;;
  *'config current-context'*) echo MOCK-OFFLINE-NOT-CLOUD ;;
  *'wait --for=condition=Degraded=False tigerastatus/calico'*)
    if [[ "${MOCK_SCENARIO:-}" == calico-degraded ]]; then exit 1; fi ;;
  *'--ignore-not-found'*)
    if [[ "${MOCK_SCENARIO:-}" == foreign ]]; then echo 'uid|somebody-else'; fi ;;
  *'get pod server-reverse -o jsonpath={.status.podIP}'*) echo 10.244.2.1 ;;
  *'get pod server -o jsonpath={.status.podIP}'*) echo 10.244.1.1 ;;
  *'get svc server-reverse -o jsonpath={.spec.clusterIP}'*) echo 10.96.0.2 ;;
  *'get svc server -o jsonpath={.spec.clusterIP}'*) echo 10.96.0.1 ;;
  *'jsonpath={.spec.nodeName}'*)
    if [[ "${MOCK_SCENARIO:-}" == same-node ]]; then echo wk-01.zone.c.project.internal
    elif [[ "$*" == *'get pod server-reverse '* || "$*" == *'get pod client '* ]]; then echo wk-02.zone.c.project.internal
    else echo wk-01.zone.c.project.internal; fi ;;
  *'exec '*' -- curl '*)
    if [[ "${MOCK_SCENARIO:-}" == dns-failure && "$*" == *svc.cluster.local* ]]; then echo 'MOCK DNS resolution failed' >&2; echo 000; exit 6; fi
    if [[ "${MOCK_SCENARIO:-}" == transient && ! -f "$MOCK_RETRY_MARKER" ]]; then
      : >"$MOCK_RETRY_MARKER"
      echo 'MOCK kube-proxy warming up' >&2
      echo 000
      exit 7
    fi
    echo 200 ;;
esac
'''


@unittest.skipUnless(BASH, "Bash not available")
class CrossNodeTests(unittest.TestCase):
    def run_scenario(self, scenario, script="test-cross-node.sh"):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for folder in ("scripts", "config", "bin", "tests/service"):
                (root / folder).mkdir(parents=True)
            for name in ("test-cross-node.sh", "03-install-calico.sh", "lib.sh", "cluster-nodes.py"):
                shutil.copyfile(ROOT / "scripts" / name, root / "scripts" / name)
            shutil.copyfile(ROOT / "config/versions.env", root / "config/versions.env")
            shutil.copyfile(ROOT / "tests/service/network-check.yaml", root / "tests/service/network-check.yaml")
            fake = root / "bin/kubectl"
            fake.write_text(MOCK, encoding="utf-8", newline="\n")
            fake.chmod(0o755)
            fake_curl = root / "bin/curl"
            fake_curl.write_text('#!/usr/bin/env bash\nwhile [[ $# -gt 0 ]]; do if [[ "$1" == -o ]]; then shift; printf "# offline fake manifest\\n" >"$1"; fi; shift; done\n', encoding="utf-8", newline="\n")
            fake_curl.chmod(0o755)
            fake_python = root / "bin/python3"
            # Windows Python emits CRLF; emulate Linux python3 output for Bash mapfile.
            fake_python.write_text('#!/usr/bin/env bash\nset -o pipefail\n"$MOCK_PYTHON" "$@" | tr -d "\\r"\n', encoding="utf-8", newline="\n")
            fake_python.chmod(0o755)
            fake_sleep = root / "bin/sleep"
            fake_sleep.write_text('#!/usr/bin/env bash\nexit 0\n', encoding="utf-8", newline="\n")
            fake_sleep.chmod(0o755)
            calls = root / "calls.txt"
            env = dict(os.environ, MOCK_SCENARIO=scenario, MOCK_CALLS=calls.as_posix(),
                       MOCK_PYTHON=pathlib.Path(sys.executable).as_posix(), MOCK_RETRY_MARKER=(root / "retry-marker").as_posix())
            # Bash prepends a POSIX path itself, avoiding Windows PATH conversion ambiguity.
            proc = subprocess.run([BASH, "-c", 'root="$1"; if command -v cygpath >/dev/null; then root="$(cygpath -u "$root")"; fi; export PATH="$root/bin:$PATH"; bash "$root/scripts/$2"',
                                   "offline-net01", root.as_posix(), script], env=env, capture_output=True, text=True, timeout=30)
            return proc, calls.read_text(encoding="utf-8") if calls.exists() else ""

    def test_six_http_requests_in_both_directions(self):
        proc, calls = self.run_scenario("success")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(calls.count(" -- curl "), 6)
        self.assertIn("client (wk-02.zone.c.project.internal) -> server (wk-01.zone.c.project.internal)", proc.stdout)
        self.assertIn("client-reverse (wk-01.zone.c.project.internal) -> server-reverse (wk-02.zone.c.project.internal)", proc.stdout)
        self.assertIn("label node wk-01.zone.c.project.internal nt132.lab/worker=wk-01 --overwrite", calls)
        self.assertIn("label node wk-02.zone.c.project.internal nt132.lab/worker=wk-02 --overwrite", calls)
        self.assertIn("node/wk-01.zone.c.project.internal node/wk-02.zone.c.project.internal", calls)

    def test_foreign_resource_is_not_applied_over(self):
        proc, calls = self.run_scenario("foreign")
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("apply -f", calls)
        self.assertIn("Refusing to overwrite", proc.stderr + proc.stdout)

    def test_dns_failure_cannot_report_success(self):
        proc, calls = self.run_scenario("dns-failure")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(" -- curl ", calls)
        self.assertNotIn("Six HTTP checks passed", proc.stdout)
        self.assertIn("attempt 12/12: curl_exit=6 http=000", proc.stdout)
        self.assertIn("MOCK DNS resolution failed", proc.stdout + proc.stderr)

    def test_transient_connection_failure_is_retried_and_logged(self):
        proc, calls = self.run_scenario("transient")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(calls.count(" -- curl "), 7)
        self.assertIn("attempt 1/12: curl_exit=7 http=000", proc.stdout)
        self.assertIn("attempt 2/12: curl_exit=0 http=200", proc.stdout)
        self.assertIn("MOCK kube-proxy warming up", proc.stdout + proc.stderr)

    def test_both_directions_use_stable_worker_aliases_in_fixture(self):
        fixture = (ROOT / "tests/service/network-check.yaml").read_text(encoding="utf-8")
        self.assertEqual(fixture.count("nt132.lab/worker: wk-01"), 2)
        self.assertEqual(fixture.count("nt132.lab/worker: wk-02"), 2)
        self.assertNotIn("kubernetes.io/hostname:", fixture)

    def test_same_node_cannot_pass_as_cross_node(self):
        proc, calls = self.run_scenario("same-node")
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn(" -- curl ", calls)
        self.assertIn("different nodes", proc.stderr + proc.stdout)

    def test_calico_install_waits_for_available_and_no_progress_or_degradation(self):
        proc, calls = self.run_scenario("success", "03-install-calico.sh")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        for condition in ("Available=True", "Progressing=False", "Degraded=False"):
            self.assertIn("wait --for=condition=" + condition + " tigerastatus/calico --timeout=300s", calls)

    def test_calico_degraded_cannot_report_install_success(self):
        proc, calls = self.run_scenario("calico-degraded", "03-install-calico.sh")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Degraded=False", calls)


if __name__ == "__main__":
    unittest.main()
