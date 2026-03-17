"""
PortalHTTPClient - Complete HTTP client for DroidRun Portal.

Communicates with Portal's HTTP server (default port 8080) using Bearer token auth.
Supports all GET and POST endpoints defined in the Portal local API.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

import httpx

from .exceptions import (
    PortalAuthError,
    PortalConnectionError,
    PortalResponseError,
    PortalTimeoutError,
)

logger = logging.getLogger("droidrun_agent")


class PortalHTTPClient:
    """
    Async HTTP client for DroidRun Portal.

    Usage::

        async with PortalHTTPClient(
            "http://192.168.1.100:8080", token="TOKEN"
        ) as client:
            await client.ping()
            state = await client.get_state_full()
            await client.tap(200, 400)
    """

    def __init__(self, base_url: str, token: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._headers = {"Authorization": f"Bearer {token}"}
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Create the underlying HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers,
                timeout=self.timeout,
            )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> PortalHTTPClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            await self.connect()
        assert self._client is not None
        return self._client

    def _unwrap(self, data: dict[str, Any]) -> Any:
        """Extract value from Portal response envelope
        (``{result: ...}`` or ``{data: ...}``)."""
        key = "result" if "result" in data else "data" if "data" in data else None
        if key is None:
            return data
        value = data[key]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return value

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        auth: bool = True,
        raw: bool = False,
    ) -> Any:
        """Send GET request and return parsed response."""
        client = await self._ensure_client()
        headers = self._headers if auth else {}
        try:
            resp = await client.get(path, params=params, headers=headers)
        except httpx.ConnectError as exc:
            raise PortalConnectionError(f"Cannot connect to {self.base_url}{path}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise PortalTimeoutError(f"GET {path} timed out: {exc}") from exc

        if resp.status_code in (401, 403):
            raise PortalAuthError(f"Auth failed for GET {path}: HTTP {resp.status_code}")
        if resp.status_code != 200:
            raise PortalResponseError(f"GET {path} returned HTTP {resp.status_code}: {resp.text}")

        if raw:
            return resp.content

        data = resp.json()
        if isinstance(data, dict):
            return self._unwrap(data)
        return data

    async def _post(self, path: str, form: dict[str, Any]) -> Any:
        """Send POST request with form-encoded body and return parsed response."""
        client = await self._ensure_client()
        # Remove None values from form data
        form_data = {k: v for k, v in form.items() if v is not None}
        try:
            resp = await client.post(path, data=form_data)
        except httpx.ConnectError as exc:
            raise PortalConnectionError(f"Cannot connect to {self.base_url}{path}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise PortalTimeoutError(f"POST {path} timed out: {exc}") from exc

        if resp.status_code in (401, 403):
            raise PortalAuthError(f"Auth failed for POST {path}: HTTP {resp.status_code}")
        if resp.status_code != 200:
            raise PortalResponseError(f"POST {path} returned HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        if isinstance(data, dict):
            return self._unwrap(data)
        return data

    # ------------------------------------------------------------------
    # GET endpoints
    # ------------------------------------------------------------------

    async def ping(self) -> dict[str, Any]:
        """Health check (no auth required)."""
        return await self._get("/ping", auth=False)

    async def get_a11y_tree(self) -> dict[str, Any]:
        """Get simplified accessibility tree."""
        return await self._get("/a11y_tree")

    async def get_a11y_tree_full(self, *, filter: bool = True) -> dict[str, Any]:
        """Get full accessibility tree. Set filter=False to keep small elements."""
        params = {"filter": str(filter).lower()}
        return await self._get("/a11y_tree_full", params=params)

    async def get_state(self) -> dict[str, Any]:
        """Get simplified UI state."""
        return await self._get("/state")

    async def get_state_full(self, *, filter: bool = True) -> dict[str, Any]:
        """Get full UI state (a11y tree + phone state).
        Set filter=False to keep small elements."""
        params = {"filter": str(filter).lower()}
        return await self._get("/state_full", params=params)

    async def get_phone_state(self) -> dict[str, Any]:
        """Get phone state info."""
        return await self._get("/phone_state")

    async def get_version(self) -> str:
        """Get Portal app version string."""
        result = await self._get("/version")
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return result.get("version", str(result))
        return str(result)

    async def get_packages(self) -> list[dict[str, Any]]:
        """Get list of launchable packages."""
        result = await self._get("/packages")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "packages" in result:
            return result["packages"]
        return []

    async def take_screenshot(self, *, hide_overlay: bool = True) -> bytes:
        """
        Take device screenshot. Returns PNG bytes.

        The HTTP endpoint returns base64-encoded PNG inside a JSON envelope.
        """
        params: dict[str, Any] = {}
        if not hide_overlay:
            params["hideOverlay"] = "false"

        max_retries = 3
        for attempt in range(max_retries + 1):
            client = await self._ensure_client()
            try:
                resp = await client.get("/screenshot", params=params)
            except httpx.ConnectError as exc:
                raise PortalConnectionError(f"Screenshot connect error: {exc}") from exc
            except httpx.TimeoutException as exc:
                raise PortalTimeoutError(f"Screenshot timed out: {exc}") from exc

            if resp.status_code in (401, 403):
                raise PortalAuthError(f"Screenshot auth failed: HTTP {resp.status_code}")
            if resp.status_code != 200:
                error_text = resp.text
                if "interval too short" in error_text.lower() and attempt < max_retries:
                    await asyncio.sleep(0.5)
                    continue
                raise PortalResponseError(f"Screenshot failed: HTTP {resp.status_code}")

            break

        content_type = resp.headers.get("content-type", "")

        # Binary PNG response
        if "image/" in content_type or "octet-stream" in content_type:
            return resp.content

        # JSON envelope with base64 PNG
        data = resp.json()
        inner = self._unwrap(data) if isinstance(data, dict) else data
        if isinstance(inner, str):
            return base64.b64decode(inner)

        raise PortalResponseError(f"Unexpected screenshot response format: {type(inner)}")

    # ------------------------------------------------------------------
    # POST endpoints
    # ------------------------------------------------------------------

    async def tap(self, x: int, y: int) -> dict[str, Any]:
        """Tap screen coordinates."""
        return await self._post("/tap", {"x": x, "y": y})

    async def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: int | None = None,
    ) -> dict[str, Any]:
        """Swipe from (start_x, start_y) to (end_x, end_y).
        Duration in ms (optional)."""
        return await self._post(
            "/swipe",
            {
                "startX": start_x,
                "startY": start_y,
                "endX": end_x,
                "endY": end_y,
                "duration": duration,
            },
        )

    async def global_action(self, action: int) -> dict[str, Any]:
        """Execute accessibility global action by Android action ID."""
        return await self._post("/global", {"action": action})

    async def start_app(
        self,
        package: str,
        activity: str | None = None,
        stop_before_launch: bool = False,
    ) -> dict[str, Any]:
        """Launch an app by package name."""
        return await self._post(
            "/app",
            {
                "package": package,
                "activity": activity,
                "stopBeforeLaunch": str(stop_before_launch).lower(),
            },
        )

    async def stop_app(self, package: str) -> dict[str, Any]:
        """Best-effort stop an app."""
        return await self._post("/app/stop", {"package": package})

    async def input_text(self, text: str, clear: bool = True) -> dict[str, Any]:
        """Input text via Portal keyboard. Text is base64-encoded automatically."""
        encoded = base64.b64encode(text.encode()).decode()
        return await self._post(
            "/keyboard/input",
            {
                "base64_text": encoded,
                "clear": str(clear).lower(),
            },
        )

    async def clear_input(self) -> dict[str, Any]:
        """Clear focused input field."""
        return await self._post("/keyboard/clear", {})

    async def press_key(self, key_code: int) -> dict[str, Any]:
        """Send an Android key code."""
        return await self._post("/keyboard/key", {"key_code": key_code})

    async def set_overlay_offset(self, offset: int) -> dict[str, Any]:
        """Set overlay vertical offset in pixels."""
        return await self._post("/overlay_offset", {"offset": offset})

    async def set_socket_port(self, port: int) -> dict[str, Any]:
        """Update the HTTP server port."""
        return await self._post("/socket_port", {"port": port})
