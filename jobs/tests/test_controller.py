"""Behavioral tests for the private local laptop-controller client."""

import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from django.test import SimpleTestCase, override_settings

from jobs.controller import (
    ControllerProtocolError,
    ControllerRejected,
    ControllerUnavailable,
    LaptopController,
    get_laptop_controller,
)


class ControllerStub:
    """A local stand-in for the existing private controller routes."""

    def __init__(self):
        self.token = "token-one"
        self.page_body = None
        self.action_status = 200
        self.action_raw = None
        self.reject_posts = False
        self.created_at = datetime(2026, 10, 22, 21, 0, tzinfo=timezone.utc)
        self.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        if not self.thread.is_alive():
            return
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _handler(self):
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, payload):
                body = json.dumps(payload).encode()
                self._write(status, body, "application/json")

            def _write(self, status, body, content_type):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _record(self, method, body=b""):
                stub.requests.append(
                    {
                        "method": method,
                        "path": self.path,
                        "headers": {
                            key.lower(): value for key, value in self.headers.items()
                        },
                        "body": body,
                    }
                )

            def do_GET(self):
                self._record("GET")
                if self.path != "/":
                    self._send(404, {"error": "Not found"})
                    return
                page = stub.page_body
                if page is None:
                    page = f'<script>const csrf="{stub.token}";</script>'
                self._write(200, page.encode(), "text/html; charset=utf-8")

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length) if length else b""
                self._record("POST", body)
                if stub.reject_posts or self.headers.get("X-CSRF-Token") != stub.token:
                    self._send(403, {"error": "Invalid action token"})
                    return
                if self.path == "/api/wake":
                    self._send(202, {"message": "Wake signal sent"})
                    return
                if self.path != "/api/action":
                    self._send(404, {"error": "Not found"})
                    return
                if stub.action_status != 200:
                    self._send(stub.action_status, {"error": "controller failure"})
                    return
                if stub.action_raw is not None:
                    self._write(200, stub.action_raw, "application/json")
                    return
                try:
                    payload = json.loads(body)
                    action = payload["action"]
                    parameters = payload["parameters"]
                except (KeyError, TypeError, json.JSONDecodeError):
                    self._send(400, {"error": "invalid action"})
                    return
                if action == "create_lease":
                    expires = stub.created_at + timedelta(
                        seconds=parameters["duration_seconds"]
                    )
                    lease = {
                        "lease_id": "lease-one",
                        "created_at": stub.created_at.isoformat(),
                        "expires_at": expires.isoformat(),
                        "remaining_seconds": parameters["duration_seconds"],
                    }
                    result = {"lease": lease}
                elif action == "extend_lease":
                    lease = {
                        "lease_id": parameters["lease_id"],
                        "created_at": stub.created_at.isoformat(),
                        "expires_at": (
                            stub.created_at
                            + timedelta(seconds=parameters["extension_seconds"])
                        ).isoformat(),
                        "remaining_seconds": parameters["extension_seconds"],
                    }
                    result = {"lease": lease}
                elif action == "release_lease":
                    result = {"released": parameters["lease_id"]}
                else:
                    self._send(404, {"error": "unknown action"})
                    return
                self._send(
                    200,
                    {
                        "request_id": payload["request_id"],
                        "module": "power",
                        "action": action,
                        "result": result,
                    },
                )

        return Handler


class LaptopControllerTests(SimpleTestCase):
    def setUp(self):
        self.stub = ControllerStub().start()
        self.addCleanup(self.stub.stop)
        self.controller = LaptopController(self.stub.url, timeout=2)

    def posts(self, path=None):
        return [
            request
            for request in self.stub.requests
            if request["method"] == "POST"
            and (path is None or request["path"] == path)
        ]

    def test_wake_fetches_the_page_token_and_posts_without_leaking_it(self):
        self.controller.request_wake()

        self.assertEqual(
            [request["method"] for request in self.stub.requests],
            ["GET", "POST"],
        )
        post = self.posts("/api/wake")[0]
        self.assertEqual(post["headers"]["x-csrf-token"], "token-one")
        self.assertEqual(post["body"], b"")
        self.assertNotIn("token-one", repr(self.controller))

    def test_lease_actions_use_the_existing_power_contract(self):
        lease = self.controller.create_lease(1200)
        extended = self.controller.extend_lease(lease.lease_id, 600)
        released = self.controller.release_lease(lease.lease_id)

        self.assertEqual(lease.lease_id, "lease-one")
        self.assertEqual(lease.created_at, self.stub.created_at)
        self.assertEqual(
            lease.expires_at, self.stub.created_at + timedelta(seconds=1200)
        )
        self.assertEqual(extended.expires_at, self.stub.created_at + timedelta(seconds=600))
        self.assertEqual(released, "lease-one")

        actions = [
            json.loads(post["body"])
            for post in self.posts("/api/action")
        ]
        self.assertEqual(
            [action["action"] for action in actions],
            ["create_lease", "extend_lease", "release_lease"],
        )
        self.assertTrue(all(action["module"] == "power" for action in actions))
        self.assertEqual(actions[0]["parameters"], {"duration_seconds": 1200})
        self.assertEqual(
            actions[1]["parameters"],
            {"lease_id": "lease-one", "extension_seconds": 600},
        )
        self.assertEqual(actions[2]["parameters"], {"lease_id": "lease-one"})
        for action in actions:
            self.assertRegex(action["request_id"], r"^[A-Za-z0-9._:-]{1,128}$")

    def test_stale_action_token_is_refreshed_once(self):
        self.controller.request_wake()
        self.stub.token = "token-two"

        self.controller.request_wake()

        self.assertEqual(
            [request["path"] for request in self.stub.requests],
            ["/", "/api/wake", "/api/wake", "/", "/api/wake"],
        )
        self.assertEqual(
            self.posts("/api/wake")[2]["headers"]["x-csrf-token"], "token-two"
        )

    def test_repeated_rejection_does_not_leak_the_action_token(self):
        self.stub.token = "secret-token-value"
        self.stub.reject_posts = True
        with self.assertRaises(ControllerRejected) as caught:
            self.controller.create_lease(60)

        self.assertEqual(caught.exception.status, 403)
        self.assertNotIn("secret-token-value", str(caught.exception))

    def test_malformed_action_encoding_is_a_protocol_error(self):
        self.stub.action_raw = b"\xff\xfe"

        with self.assertRaises(ControllerProtocolError):
            self.controller.create_lease(60)

    def test_controller_server_error_is_a_rejection(self):
        self.stub.action_status = 503

        with self.assertRaises(ControllerRejected) as caught:
            self.controller.create_lease(60)

        self.assertEqual(caught.exception.status, 503)

    def test_malformed_page_is_a_protocol_error(self):
        self.stub.page_body = "<html>no action token</html>"

        with self.assertRaises(ControllerProtocolError):
            self.controller.request_wake()

    def test_unreachable_controller_raises_unavailable(self):
        self.stub.stop()
        controller = LaptopController(self.stub.url, timeout=0.5)

        with self.assertRaises(ControllerUnavailable):
            controller.request_wake()


class ConfiguredControllerTests(SimpleTestCase):
    def test_controller_is_only_created_when_a_private_url_is_configured(self):
        with override_settings(LAPTOP_CONTROLLER=None, LAPTOP_CONTROLLER_URL=""):
            self.assertIsNone(get_laptop_controller())

        injected = object()
        with override_settings(LAPTOP_CONTROLLER=injected):
            self.assertIs(get_laptop_controller(), injected)

        stub = ControllerStub().start()
        self.addCleanup(stub.stop)
        with override_settings(LAPTOP_CONTROLLER=None, LAPTOP_CONTROLLER_URL=stub.url):
            controller = get_laptop_controller()
            self.assertIsInstance(controller, LaptopController)
            self.assertIs(get_laptop_controller(), controller)
