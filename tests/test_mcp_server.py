"""Tests for the MCP server tool registration and dispatch."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from droidrun_agent import mcp_server
from droidrun_agent.config import PortalConfig
from droidrun_agent.exceptions import PortalConnectionError, PortalTimeoutError
from droidrun_agent.mcp_server import TOOLS, _handle_tool, _text, _image


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_globals() -> None:
    """Reset module-level state between tests."""
    mcp_server._config = None
    mcp_server._client = None


@pytest.fixture()
def mock_http_client() -> AsyncMock:
    """Return a mock PortalHTTPClient and inject it into the module."""
    from droidrun_agent.http_client import PortalHTTPClient

    client = AsyncMock(spec=PortalHTTPClient)
    client.connect = AsyncMock()
    mcp_server._config = PortalConfig(base_url="http://test:8080", token="tok")
    mcp_server._client = client
    return client


@pytest.fixture()
def mock_ws_client() -> AsyncMock:
    """Return a mock PortalWSClient and inject it into the module."""
    from droidrun_agent.ws_client import PortalWSClient

    client = AsyncMock(spec=PortalWSClient)
    client.connect = AsyncMock()
    mcp_server._config = PortalConfig(base_url="ws://test:8081", token="tok", transport="ws")
    mcp_server._client = client
    return client


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------

class TestToolRegistration:
    """Verify tool metadata."""

    def test_tools_list_non_empty(self) -> None:
        assert len(TOOLS) > 0

    def test_all_tools_have_required_fields(self) -> None:
        for tool in TOOLS:
            assert tool.name, f"Tool missing name: {tool}"
            assert tool.description, f"Tool {tool.name} missing description"
            assert tool.inputSchema is not None, f"Tool {tool.name} missing inputSchema"

    def test_tool_names_unique(self) -> None:
        names = [t.name for t in TOOLS]
        assert len(names) == len(set(names)), f"Duplicate tool names: {names}"

    def test_expected_tools_present(self) -> None:
        names = {t.name for t in TOOLS}
        expected = {
            "portal_ping",
            "portal_tap",
            "portal_swipe",
            "portal_screenshot",
            "portal_get_state",
            "portal_get_version",
            "portal_get_packages",
            "portal_global_action",
            "portal_start_app",
            "portal_stop_app",
            "portal_input_text",
            "portal_clear_input",
            "portal_press_key",
        }
        assert expected.issubset(names), f"Missing tools: {expected - names}"


# ---------------------------------------------------------------------------
# Helpers tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_text_string(self) -> None:
        result = _text("hello")
        assert len(result) == 1
        assert result[0].text == "hello"

    def test_text_dict(self) -> None:
        result = _text({"key": "value"})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert parsed == {"key": "value"}

    def test_image(self) -> None:
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = _image(png)
        assert len(result) == 1
        assert result[0].mimeType == "image/png"
        assert result[0].type == "image"


# ---------------------------------------------------------------------------
# HTTP tool dispatch tests
# ---------------------------------------------------------------------------

class TestHTTPToolDispatch:
    async def test_ping(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.ping.return_value = {"status": "ok"}
        result = await _handle_tool("portal_ping", {})
        mock_http_client.ping.assert_awaited_once()
        assert "ok" in result[0].text

    async def test_tap(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.tap.return_value = {"success": True}
        result = await _handle_tool("portal_tap", {"x": 100, "y": 200})
        mock_http_client.tap.assert_awaited_once_with(100, 200)

    async def test_swipe(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.swipe.return_value = {"success": True}
        result = await _handle_tool(
            "portal_swipe",
            {"start_x": 0, "start_y": 0, "end_x": 500, "end_y": 500, "duration": 300},
        )
        mock_http_client.swipe.assert_awaited_once_with(0, 0, 500, 500, duration=300)

    async def test_screenshot(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.take_screenshot.return_value = b"\x89PNG\r\n\x1a\n"
        result = await _handle_tool("portal_screenshot", {"hide_overlay": True})
        assert result[0].type == "image"
        mock_http_client.take_screenshot.assert_awaited_once_with(hide_overlay=True)

    async def test_get_state(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.get_state.return_value = {"app": "com.test"}
        result = await _handle_tool("portal_get_state", {})
        mock_http_client.get_state.assert_awaited_once()

    async def test_get_state_full(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.get_state_full.return_value = {"full": True}
        result = await _handle_tool("portal_get_state_full", {"filter": False})
        mock_http_client.get_state_full.assert_awaited_once_with(filter=False)

    async def test_start_app(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.start_app.return_value = {"success": True}
        result = await _handle_tool("portal_start_app", {"package": "com.android.settings"})
        mock_http_client.start_app.assert_awaited_once_with(
            "com.android.settings", activity=None, stop_before_launch=False
        )

    async def test_input_text(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.input_text.return_value = {"success": True}
        result = await _handle_tool("portal_input_text", {"text": "hello", "clear": False})
        mock_http_client.input_text.assert_awaited_once_with("hello", clear=False)

    async def test_get_version(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.get_version.return_value = "1.0.0"
        result = await _handle_tool("portal_get_version", {})
        assert "1.0.0" in result[0].text

    async def test_get_packages(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.get_packages.return_value = [{"packageName": "com.test"}]
        result = await _handle_tool("portal_get_packages", {})
        mock_http_client.get_packages.assert_awaited_once()

    async def test_global_action(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.global_action.return_value = {"success": True}
        result = await _handle_tool("portal_global_action", {"action": 1})
        mock_http_client.global_action.assert_awaited_once_with(1)

    async def test_press_key(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.press_key.return_value = {"success": True}
        result = await _handle_tool("portal_press_key", {"key_code": 66})
        mock_http_client.press_key.assert_awaited_once_with(66)


# ---------------------------------------------------------------------------
# WS-only tools tested against HTTP should show error
# ---------------------------------------------------------------------------

class TestTransportRestrictions:
    async def test_get_time_http_error(self, mock_http_client: AsyncMock) -> None:
        result = await _handle_tool("portal_get_time", {})
        assert "error" in result[0].text

    async def test_install_http_error(self, mock_http_client: AsyncMock) -> None:
        result = await _handle_tool("portal_install", {"urls": ["http://example.com/a.apk"]})
        assert "error" in result[0].text

    async def test_ping_ws_error(self, mock_ws_client: AsyncMock) -> None:
        result = await _handle_tool("portal_ping", {})
        assert "error" in result[0].text

    async def test_get_time_ws_ok(self, mock_ws_client: AsyncMock) -> None:
        mock_ws_client.get_time.return_value = 1700000000000
        result = await _handle_tool("portal_get_time", {})
        mock_ws_client.get_time.assert_awaited_once()

    async def test_install_ws_ok(self, mock_ws_client: AsyncMock) -> None:
        mock_ws_client.install.return_value = {"success": True}
        result = await _handle_tool("portal_install", {"urls": ["http://example.com/a.apk"]})
        mock_ws_client.install.assert_awaited_once_with(["http://example.com/a.apk"], hide_overlay=True)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    async def test_portal_error_caught(self, mock_http_client: AsyncMock) -> None:
        mock_http_client.tap.side_effect = PortalConnectionError("Connection refused")
        # The server's call_tool wraps PortalError; here we test _handle_tool directly
        with pytest.raises(PortalConnectionError):
            await _handle_tool("portal_tap", {"x": 0, "y": 0})

    async def test_unknown_tool(self, mock_http_client: AsyncMock) -> None:
        result = await _handle_tool("portal_nonexistent", {})
        assert "Unknown tool" in result[0].text


# ---------------------------------------------------------------------------
# Server creation
# ---------------------------------------------------------------------------

class TestServerCreation:
    def test_create_server(self) -> None:
        from droidrun_agent.mcp_server import create_server

        server = create_server()
        assert server is not None
        assert server.name == "droidrun-agent"
