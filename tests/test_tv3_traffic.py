"""Local HTTP response and interruption regression tests; never calls cloud."""
import contextlib
import http.server
import importlib.util
import io
import json
import pathlib
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tv3_traffic", ROOT / "scripts/tv3.py")
tv3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tv3)


class HTTPResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                if self.path == "/slow":
                    self.send_header("Content-Length", "6")
                    self.end_headers()
                    for _ in range(6):
                        self.wfile.write(b"x")
                        self.wfile.flush()
                        time.sleep(0.03)
                elif self.path == "/badchunk":
                    self.send_header("Transfer-Encoding", "chunked")
                    self.end_headers()
                    self.wfile.write(b"Z\r\n")
                    self.wfile.flush()
                    self.close_connection = True
                elif self.path == "/short":
                    self.send_header("Content-Length", "10")
                    self.end_headers()
                    self.wfile.write(b"short")
                    self.wfile.flush()
                    self.close_connection = True
                else:
                    self.send_header("Content-Length", str(1024 * 1024 + 1))
                    self.end_headers()
                    self.close_connection = True

            def log_message(self, *args):
                pass

        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, timeout=1):
        opener = tv3.urllib.request.build_opener(tv3.NoRedirect())
        return tv3.request_status(opener, "http://127.0.0.1:" + str(self.server.server_port) + path, timeout)

    def test_malformed_chunked_response_is_an_error_instead_of_a_crash(self):
        status, error = self.request("/badchunk")
        self.assertIsNone(status)
        self.assertIn("truncated", error)

    def test_truncated_content_length_cannot_count_as_http_200(self):
        status, error = self.request("/short")
        self.assertIsNone(status)
        self.assertIn("truncated", error)

    def test_oversized_body_is_not_reported_as_fully_validated(self):
        status, error = self.request("/large")
        self.assertIsNone(status)
        self.assertIn("1 MiB", error)

    def test_slow_streaming_can_outlast_the_socket_inactivity_timeout(self):
        started = time.monotonic()
        status, error = self.request("/slow", timeout=0.12)
        elapsed = time.monotonic() - started
        self.assertEqual(status, 200)
        self.assertIsNone(error)
        self.assertGreater(elapsed, 0.12)


class TrafficReportTests(unittest.TestCase):
    def test_interrupt_during_request_keeps_evidence_and_returns_130(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(tv3, "request_status", side_effect=KeyboardInterrupt), \
             contextlib.redirect_stdout(io.StringIO()):
            out = pathlib.Path(tmp) / "traffic"
            args = SimpleNamespace(url="http://127.0.0.1/", duration=1, interval=1, timeout=1, output=out)
            self.assertEqual(tv3.traffic(args), 130)
            report = json.loads((out / "traffic.json").read_text(encoding="utf-8"))
            self.assertTrue(report["interrupted"])
            self.assertFalse(report["completed"])
            self.assertFalse(report["all_http_200"])
            self.assertIn("finished", report)

    def test_protocol_failure_is_saved_as_failed_traffic_evidence(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(tv3.time, "monotonic", side_effect=[0, 0, 2, 2]), \
             mock.patch.object(tv3, "request_status", return_value=(None, "HTTP protocol error")), \
             contextlib.redirect_stdout(io.StringIO()):
            out = pathlib.Path(tmp) / "traffic"
            args = SimpleNamespace(url="http://127.0.0.1/", duration=1, interval=1, timeout=1, output=out)
            self.assertEqual(tv3.traffic(args), 1)
            report = json.loads((out / "traffic.json").read_text(encoding="utf-8"))
            self.assertTrue(report["completed"])
            self.assertFalse(report["all_http_200"])
            self.assertEqual(report["requests"][0]["error"], "HTTP protocol error")


if __name__ == "__main__":
    unittest.main()
