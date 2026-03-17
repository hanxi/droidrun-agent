"""MCP Server exposing DroidRun Portal as tools for AI agents.

Requires the ``mcp`` optional dependency::

    pip install droidrun-agent[mcp]

Start via CLI::

    droidrun-agent --mcp

Or as a Python module::

    python -m droidrun_agent --mcp

Environment variables:
    PORTAL_BASE_URL  (required) - Portal HTTP or WS base URL.
    PORTAL_TOKEN     (required) - Bearer token.
    PORTAL_TIMEOUT   (optional) - Timeout in seconds, default 10.
    PORTAL_TRANSPORT (optional) - ``http`` or ``ws``, default ``http``.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import ImageContent, TextContent, Tool

from .config import PortalConfig
from .exceptions import PortalError
from .http_client import PortalHTTPClient
from .ws_client import PortalWSClient

logger = logging.getLogger("droidrun_agent.mcp")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_config: PortalConfig | None = None
_client: PortalHTTPClient | PortalWSClient | None = None


async def _get_client() -> PortalHTTPClient | PortalWSClient:
    """Lazily create and connect the Portal client."""
    global _config, _client
    if _client is not None:
        return _client
    if _config is None:
        _config = PortalConfig.from_env()
    _client = _config.create_client()
    await _client.connect()
    return _client


def _text(data: Any) -> list[TextContent]:
    """Wrap a value as MCP TextContent."""
    if isinstance(data, str):
        return [TextContent(type="text", text=data)]
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, default=str))]


def _image(png: bytes) -> list[ImageContent]:
    """Wrap PNG bytes as MCP ImageContent."""
    return [ImageContent(type="image", data=base64.b64encode(png).decode(), mimeType="image/png")]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="portal_ping",
        description="Health check (HTTP transport only, no auth required).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="portal_tap",
        description="Tap screen coordinates on the Android device.",
        inputSchema={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
            },
            "required": ["x", "y"],
        },
    ),
    Tool(
        name="portal_swipe",
        description="Swipe from one point to another on the Android device.",
        inputSchema={
            "type": "object",
            "properties": {
                "start_x": {"type": "integer", "description": "Start X coordinate"},
                "start_y": {"type": "integer", "description": "Start Y coordinate"},
                "end_x": {"type": "integer", "description": "End X coordinate"},
                "end_y": {"type": "integer", "description": "End Y coordinate"},
                "duration": {"type": "integer", "description": "Duration in milliseconds (optional)"},
            },
            "required": ["start_x", "start_y", "end_x", "end_y"],
        },
    ),
    Tool(
        name="portal_screenshot",
        description="Take a screenshot of the Android device. Returns PNG image.",
        inputSchema={
            "type": "object",
            "properties": {
                "hide_overlay": {
                    "type": "boolean",
                    "description": "Hide overlay before capture (default true)",
                    "default": True,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="portal_get_state",
        description="Get simplified UI state of the Android device.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="portal_get_state_full",
        description="Get full UI state (accessibility tree + phone state). HTTP: filter param; WS: filter param.",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "boolean",
                    "description": "Filter out small elements (default true)",
                    "default": True,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="portal_get_a11y_tree",
        description="Get simplified accessibility tree (HTTP transport only).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="portal_get_a11y_tree_full",
        description="Get full accessibility tree (HTTP transport only). Set filter=false to keep small elements.",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "boolean",
                    "description": "Filter out small elements (default true)",
                    "default": True,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="portal_get_phone_state",
        description="Get phone state info: current app, activity, keyboard status, etc. (HTTP transport only).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="portal_get_version",
        description="Get Portal app version string.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="portal_get_packages",
        description="List launchable packages on the Android device.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="portal_global_action",
        description="Execute an Android accessibility global action. Common IDs: 1=Back, 2=Home, 3=Recents.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "integer", "description": "Android global action ID"},
            },
            "required": ["action"],
        },
    ),
    Tool(
        name="portal_start_app",
        description="Launch an app by package name on the Android device.",
        inputSchema={
            "type": "object",
            "properties": {
                "package": {"type": "string", "description": "App package name"},
                "activity": {"type": "string", "description": "Activity name (optional)"},
                "stop_before_launch": {
                    "type": "boolean",
                    "description": "Stop the app before launching (default false)",
                    "default": False,
                },
            },
            "required": ["package"],
        },
    ),
    Tool(
        name="portal_stop_app",
        description="Best-effort stop an app on the Android device.",
        inputSchema={
            "type": "object",
            "properties": {
                "package": {"type": "string", "description": "App package name"},
            },
            "required": ["package"],
        },
    ),
    Tool(
        name="portal_input_text",
        description="Input text into the currently focused field on the Android device.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to input"},
                "clear": {
                    "type": "boolean",
                    "description": "Clear the field first (default true)",
                    "default": True,
                },
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="portal_clear_input",
        description="Clear the currently focused input field.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="portal_press_key",
        description="Send an Android key code. Common codes: 66=Enter, 3=Home, 4=Back, 67=Backspace.",
        inputSchema={
            "type": "object",
            "properties": {
                "key_code": {"type": "integer", "description": "Android key code"},
            },
            "required": ["key_code"],
        },
    ),
    Tool(
        name="portal_set_overlay_offset",
        description="Set overlay vertical offset in pixels.",
        inputSchema={
            "type": "object",
            "properties": {
                "offset": {"type": "integer", "description": "Offset in pixels"},
            },
            "required": ["offset"],
        },
    ),
    Tool(
        name="portal_get_time",
        description="Get device Unix timestamp in milliseconds (WebSocket transport only).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="portal_install",
        description="Install APK(s) from URL(s). Supports split APKs (WebSocket transport only).",
        inputSchema={
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of APK URLs to install",
                },
                "hide_overlay": {
                    "type": "boolean",
                    "description": "Hide overlay during install (default true)",
                    "default": True,
                },
            },
            "required": ["urls"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool dispatch – individual handlers
# ---------------------------------------------------------------------------

_Content = list[TextContent | ImageContent]


def _http_only(client: PortalHTTPClient | PortalWSClient, tool_name: str) -> _Content | None:
    """Return an error response if *client* is not HTTP, else ``None``."""
    if not isinstance(client, PortalHTTPClient):
        return _text({"error": f"{tool_name} is only available with HTTP transport"})
    return None


def _ws_only(client: PortalHTTPClient | PortalWSClient, tool_name: str) -> _Content | None:
    """Return an error response if *client* is not WebSocket, else ``None``."""
    if not isinstance(client, PortalWSClient):
        return _text({"error": f"{tool_name} is only available with WebSocket transport"})
    return None


async def _do_ping(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    if (err := _http_only(client, "portal_ping")) is not None:
        return err
    return _text(await client.ping())


async def _do_tap(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    return _text(await client.tap(args["x"], args["y"]))


async def _do_swipe(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    result = await client.swipe(
        args["start_x"], args["start_y"], args["end_x"], args["end_y"],
        duration=args.get("duration"),
    )
    return _text(result)


async def _do_screenshot(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    png = await client.take_screenshot(hide_overlay=args.get("hide_overlay", True))
    return _image(png)


async def _do_get_state(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    if isinstance(client, PortalHTTPClient):
        return _text(await client.get_state())
    return _text(await client.get_state(filter=True))


async def _do_get_state_full(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    f = args.get("filter", True)
    if isinstance(client, PortalHTTPClient):
        return _text(await client.get_state_full(filter=f))
    return _text(await client.get_state(filter=f))


async def _do_get_a11y_tree(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    if (err := _http_only(client, "portal_get_a11y_tree")) is not None:
        return err
    return _text(await client.get_a11y_tree())


async def _do_get_a11y_tree_full(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    if (err := _http_only(client, "portal_get_a11y_tree_full")) is not None:
        return err
    return _text(await client.get_a11y_tree_full(filter=args.get("filter", True)))


async def _do_get_phone_state(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    if (err := _http_only(client, "portal_get_phone_state")) is not None:
        return err
    return _text(await client.get_phone_state())


async def _do_get_version(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    return _text(await client.get_version())


async def _do_get_packages(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    return _text(await client.get_packages())


async def _do_global_action(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    return _text(await client.global_action(args["action"]))


async def _do_start_app(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    result = await client.start_app(
        args["package"], activity=args.get("activity"),
        stop_before_launch=args.get("stop_before_launch", False),
    )
    return _text(result)


async def _do_stop_app(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    return _text(await client.stop_app(args["package"]))


async def _do_input_text(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    return _text(await client.input_text(args["text"], clear=args.get("clear", True)))


async def _do_clear_input(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    return _text(await client.clear_input())


async def _do_press_key(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    return _text(await client.press_key(args["key_code"]))


async def _do_set_overlay_offset(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    return _text(await client.set_overlay_offset(args["offset"]))


async def _do_get_time(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    if (err := _ws_only(client, "portal_get_time")) is not None:
        return err
    return _text(await client.get_time())


async def _do_install(client: PortalHTTPClient | PortalWSClient, args: dict[str, Any]) -> _Content:
    if (err := _ws_only(client, "portal_install")) is not None:
        return err
    return _text(await client.install(args["urls"], hide_overlay=args.get("hide_overlay", True)))


_DISPATCH: dict[str, Any] = {
    "portal_ping": _do_ping,
    "portal_tap": _do_tap,
    "portal_swipe": _do_swipe,
    "portal_screenshot": _do_screenshot,
    "portal_get_state": _do_get_state,
    "portal_get_state_full": _do_get_state_full,
    "portal_get_a11y_tree": _do_get_a11y_tree,
    "portal_get_a11y_tree_full": _do_get_a11y_tree_full,
    "portal_get_phone_state": _do_get_phone_state,
    "portal_get_version": _do_get_version,
    "portal_get_packages": _do_get_packages,
    "portal_global_action": _do_global_action,
    "portal_start_app": _do_start_app,
    "portal_stop_app": _do_stop_app,
    "portal_input_text": _do_input_text,
    "portal_clear_input": _do_clear_input,
    "portal_press_key": _do_press_key,
    "portal_set_overlay_offset": _do_set_overlay_offset,
    "portal_get_time": _do_get_time,
    "portal_install": _do_install,
}


async def _handle_tool(name: str, arguments: dict[str, Any]) -> _Content:
    """Dispatch a tool call to the appropriate client method."""
    handler = _DISPATCH.get(name)
    if handler is None:
        return _text({"error": f"Unknown tool: {name}"})
    client = await _get_client()
    return await handler(client, arguments)


# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("droidrun-agent")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
        try:
            return await _handle_tool(name, arguments)
        except PortalError as exc:
            return _text({"error": type(exc).__name__, "message": str(exc)})

    return server


async def run_server() -> None:
    """Run the MCP server over stdio."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Entry point for ``droidrun-agent --mcp``."""
    import asyncio

    asyncio.run(run_server())
