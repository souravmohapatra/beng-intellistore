"""Client for the existing private laptop controller.

The controller is a local service. Its page supplies a rotating action token;
wake and lease requests use that token in ``X-CSRF-Token``. The controller
already owns the secured connection to the laptop agent, so this client never
handles the agent credential or a user login.
"""

from __future__ import annotations

import json
import re
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings


MAX_LEASE_LIFETIME = timedelta(hours=8)
DEFAULT_TIMEOUT_SECONDS = 5.0
_MAX_PAGE_BYTES = 2 * 1024 * 1024
_ACTION_TOKEN = re.compile(r'const\s+csrf\s*=\s*"([^"]+)"')


class ControllerError(RuntimeError):
    """Base class for a controller integration failure."""


class ControllerUnavailable(ControllerError):
    """The controller could not be reached or returned an unusable response."""


class ControllerRejected(ControllerError):
    """The controller rejected an operation."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


class ControllerProtocolError(ControllerError):
    """The controller response did not match the observed local contract."""


@dataclass(frozen=True)
class ControllerLease:
    lease_id: str
    created_at: datetime
    expires_at: datetime


class LaptopController:
    """Minimal client for the controller's existing wake and power actions."""

    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("controller URL must be an absolute http(s) URL")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._action_token: str | None = None
        self._token_lock = threading.Lock()

    def request_wake(self) -> None:
        self._post("/api/wake")
        return None

    def create_lease(self, duration_seconds: int) -> ControllerLease:
        result = self._action(
            "create_lease", {"duration_seconds": duration_seconds}
        )
        return self._lease_from(result)

    def extend_lease(self, lease_id: str, extension_seconds: int) -> ControllerLease:
        result = self._action(
            "extend_lease",
            {"lease_id": lease_id, "extension_seconds": extension_seconds},
        )
        return self._lease_from(result)

    def release_lease(self, lease_id: str) -> str:
        result = self._action("release_lease", {"lease_id": lease_id})
        released = result.get("released")
        if not isinstance(released, str) or not released:
            raise ControllerProtocolError("controller did not confirm the lease release")
        return released

    def _action(self, action: str, parameters: dict) -> dict:
        payload = {
            "module": "power",
            "action": action,
            "request_id": f"store-{secrets.token_hex(12)}",
            "parameters": parameters,
        }
        response = self._post("/api/action", payload)
        if not isinstance(response, dict):
            raise ControllerProtocolError("controller returned an invalid action response")
        result = response.get("result")
        if not isinstance(result, dict):
            raise ControllerProtocolError("controller returned no action result")
        return result

    @staticmethod
    def _lease_from(result: dict) -> ControllerLease:
        lease = result.get("lease")
        if not isinstance(lease, dict):
            raise ControllerProtocolError("controller returned no lease")
        lease_id = lease.get("lease_id")
        if not isinstance(lease_id, str) or not lease_id:
            raise ControllerProtocolError("controller returned an invalid lease identity")
        try:
            created_at = datetime.fromisoformat(lease["created_at"])
            expires_at = datetime.fromisoformat(lease["expires_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerProtocolError("controller returned invalid lease times") from exc
        if (
            created_at.tzinfo is None
            or expires_at.tzinfo is None
            or expires_at <= created_at
        ):
            raise ControllerProtocolError("controller returned invalid lease times")
        return ControllerLease(lease_id, created_at, expires_at)

    def _current_token(self) -> str:
        with self._token_lock:
            if self._action_token is None:
                self._action_token = self._fetch_token()
            return self._action_token

    def _fetch_token(self) -> str:
        request = Request(f"{self.base_url}/", method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read(_MAX_PAGE_BYTES)
        except HTTPError as exc:
            raise ControllerRejected(
                f"controller page rejected (HTTP {exc.code})", exc.code
            ) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise ControllerUnavailable("controller unavailable") from exc
        match = _ACTION_TOKEN.search(body.decode("utf-8", "replace"))
        if match is None:
            raise ControllerProtocolError("controller action token not found")
        return match.group(1)

    def _post(self, path: str, payload: dict | None = None) -> dict | None:
        token = self._current_token()
        try:
            return self._post_once(path, payload, token)
        except ControllerRejected as exc:
            if exc.status != 403:
                raise
        with self._token_lock:
            self._action_token = None
        return self._post_once(path, payload, self._current_token())

    def _post_once(self, path: str, payload: dict | None, token: str):
        body = (
            b""
            if payload is None
            else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method="POST",
            headers={
                "X-CSRF-Token": token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            raise ControllerRejected(
                f"controller request rejected (HTTP {exc.code})", exc.code
            ) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise ControllerUnavailable("controller unavailable") from exc
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ControllerProtocolError("controller returned invalid JSON") from exc


_controllers: dict[tuple[str, float], LaptopController] = {}
_controllers_lock = threading.Lock()


def get_laptop_controller():
    """Return an injected controller or a cached client for the configured URL."""
    configured = getattr(settings, "LAPTOP_CONTROLLER", None)
    if configured is not None:
        return configured
    url = str(getattr(settings, "LAPTOP_CONTROLLER_URL", "")).strip()
    if not url:
        return None
    timeout = float(
        getattr(settings, "LAPTOP_CONTROLLER_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    )
    key = (url, timeout)
    with _controllers_lock:
        controller = _controllers.get(key)
        if controller is None:
            controller = LaptopController(url, timeout)
            _controllers[key] = controller
        return controller
