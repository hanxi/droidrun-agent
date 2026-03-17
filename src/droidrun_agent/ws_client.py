"""
PortalWSClient - Complete WebSocket client for DroidRun Portal.

Communicates with Portal's WebSocket server (default port 8081)
using JSON-RPC style messages.
Supports all methods defined in the Portal local API,
including binary screenshot frames.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from .exceptions import (
    PortalConnectionError,
    PortalResponseError,
    PortalTimeoutError,
)

logger = logging.getLogger("droidrun_agent")


class PortalWSClient:
    """
    Async WebSocket client for DroidRun Portal.

    Uses JSON-RPC style request/response with UUID-based matching.
    Automatically reconnects when a method is called on a broken connection.

    Usage::

        async with PortalWSClient("192.168.1.100", 8081, token="TOKEN") as ws:
            await ws.tap(200, 400)
            state = await ws.get_state()
            png = await ws.take_screenshot()
    """

    def __init__(
        self,
        host: str,
        port: int = 8081,
        token: str = "",
        timeout: float = 10.0,
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.timeout = timeout
        self._ws: ClientConnection | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._pending: dict[str, asyncio.Future[Any]] = {}
        self._closed = False

    @property
    def _url(self) -> str:
        return f"ws://{self.host}:{self.port}/?token={self.token}"

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish WebSocket connection and start listener."""
        if self._ws is not None:
            return
        try:
            self._ws = await websockets.connect(self._url)
        except Exception as exc:
            raise PortalConnectionError(f"Cannot connect to {self._url}: {exc}") from exc
        self._closed = False
        self._listener_task = asyncio.create_task(self._listen())
        logger.debug("WebSocket connected to %s:%s", self.host, self.port)

    async def close(self) -> None:
        """Gracefully close the WebSocket connection."""
        self._closed = True
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        # Fail all pending futures
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(PortalConnectionError("Connection closed"))
        self._pending.clear()

    async def __aenter__(self) -> PortalWSClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def _ensure_connected(self) -> None:
        """Reconnect if the connection is broken."""
        if self._ws is None or self._closed:
            self._ws = None
            self._closed = False
            if self._listener_task is not None:
                self._listener_task.cancel()
                try:
                    await self._listener_task
                except asyncio.CancelledError:
                    pass
                self._listener_task = None
            await self.connect()

    # ------------------------------------------------------------------
    # Listener
    # ------------------------------------------------------------------

    async def _listen(self) -> None:
        """Background task: receive messages and dispatch to pending futures."""
        assert self._ws is not None
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    self._handle_binary(message)
                else:
                    self._handle_text(message)
        except websockets.ConnectionClosed:
            logger.debug("WebSocket connection closed")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("WebSocket listener error: %s", exc)
        finally:
            self._ws = None
            # Fail remaining pending futures
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(PortalConnectionError("Connection lost"))
            self._pending.clear()

    def _handle_text(self, raw: str) -> None:
        """Parse JSON response and resolve the matching future."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Non-JSON message received: %s", raw[:200])
            return

        msg_id = data.get("id")
        if msg_id is None:
            logger.debug("Message without id: %s", raw[:200])
            return

        fut = self._pending.pop(str(msg_id), None)
        if fut is None or fut.done():
            return

        status = data.get("status", "")
        if status == "success":
            fut.set_result(data.get("result"))
        else:
            fut.set_exception(PortalResponseError(f"Method returned status={status}: {data.get('result', data)}"))

    def _handle_binary(self, data: bytes) -> None:
        """Parse binary screenshot frame: first 36 bytes = UUID, rest = PNG."""
        if len(data) < 36:
            logger.warning("Binary frame too short (%d bytes)", len(data))
            return

        msg_id = data[:36].decode("ascii", errors="replace")
        png_data = data[36:]

        fut = self._pending.pop(msg_id, None)
        if fut is None or fut.done():
            logger.debug("No pending future for binary frame id=%s", msg_id)
            return

        fut.set_result(png_data)

    # ------------------------------------------------------------------
    # RPC call
    # ------------------------------------------------------------------

    async def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC request and wait for the response."""
        await self._ensure_connected()
        assert self._ws is not None

        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Any] = loop.create_future()
        self._pending[request_id] = fut

        msg = {"id": request_id, "method": method}
        if params:
            msg["params"] = params

        try:
            await self._ws.send(json.dumps(msg))
        except Exception as exc:
            self._pending.pop(request_id, None)
            raise PortalConnectionError(f"Send failed for {method}: {exc}") from exc

        try:
            return await asyncio.wait_for(fut, timeout=self.timeout)
        except TimeoutError:
            self._pending.pop(request_id, None)
            raise PortalTimeoutError(f"Timeout waiting for response to {method}") from None

    # ------------------------------------------------------------------
    # Action methods
    # ------------------------------------------------------------------

    async def tap(self, x: int, y: int) -> Any:
        """Tap screen coordinates."""
        return await self._call("tap", {"x": x, "y": y})

    async def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: int | None = None,
    ) -> Any:
        """Swipe from (start_x, start_y) to (end_x, end_y).
        Duration in ms (optional)."""
        params: dict[str, Any] = {
            "startX": start_x,
            "startY": start_y,
            "endX": end_x,
            "endY": end_y,
        }
        if duration is not None:
            params["duration"] = duration
        return await self._call("swipe", params)

    async def global_action(self, action: int) -> Any:
        """Execute accessibility global action by Android action ID."""
        return await self._call("global", {"action": action})

    async def start_app(
        self,
        package: str,
        activity: str | None = None,
        stop_before_launch: bool = False,
    ) -> Any:
        """Launch an app by package name."""
        params: dict[str, Any] = {"package": package}
        if activity is not None:
            params["activity"] = activity
        if stop_before_launch:
            params["stopBeforeLaunch"] = True
        return await self._call("app", params)

    async def stop_app(self, package: str) -> Any:
        """Best-effort stop an app."""
        return await self._call("app/stop", {"package": package})

    async def input_text(self, text: str, clear: bool = True) -> Any:
        """Input text via Portal keyboard. Text is base64-encoded automatically."""
        encoded = base64.b64encode(text.encode()).decode()
        return await self._call(
            "keyboard/input",
            {
                "base64_text": encoded,
                "clear": clear,
            },
        )

    async def clear_input(self) -> Any:
        """Clear focused input field."""
        return await self._call("keyboard/clear")

    async def press_key(self, key_code: int) -> Any:
        """Send an Android key code."""
        return await self._call("keyboard/key", {"key_code": key_code})

    async def set_overlay_offset(self, offset: int) -> Any:
        """Set overlay vertical offset in pixels."""
        return await self._call("overlay_offset", {"offset": offset})

    async def set_socket_port(self, port: int) -> Any:
        """Update the HTTP server port."""
        return await self._call("socket_port", {"port": port})

    async def take_screenshot(self, *, hide_overlay: bool = True) -> bytes:
        """Take device screenshot. Returns PNG bytes.

        WebSocket returns a binary frame: first 36 bytes = request UUID,
        rest = PNG data.
        """
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                result = await self._call("screenshot", {"hideOverlay": hide_overlay})
                break
            except PortalResponseError as exc:
                if "interval too short" in str(exc).lower() and attempt < max_retries:
                    await asyncio.sleep(0.5)
                    continue
                raise
        if isinstance(result, bytes):
            return result
        # Fallback: base64-encoded string
        if isinstance(result, str):
            return base64.b64decode(result)
        raise PortalResponseError(f"Unexpected screenshot result type: {type(result)}")

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    async def get_packages(self) -> Any:
        """List launchable packages."""
        return await self._call("packages")

    async def get_state(self, *, filter: bool = True) -> Any:
        """Get full state. Set filter=False to keep small elements."""
        return await self._call("state", {"filter": filter})

    async def get_version(self) -> Any:
        """Get Portal app version."""
        return await self._call("version")

    async def get_time(self) -> Any:
        """Get device Unix timestamp in milliseconds."""
        return await self._call("time")

    async def install(
        self,
        urls: list[str],
        hide_overlay: bool = True,
    ) -> Any:
        """Install APK(s) from URL(s). WebSocket only. Supports split APKs."""
        return await self._call(
            "install",
            {
                "urls": urls,
                "hideOverlay": hide_overlay,
            },
        )
