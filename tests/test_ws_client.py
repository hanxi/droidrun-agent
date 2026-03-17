"""Integration tests for PortalWSClient.

Requires a running Portal WebSocket server at localhost:8081.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from droidrun_agent import PortalWSClient

BASE_URL = "ws://localhost:8081"
TOKEN = "eabfc22e-e795-4862-8046-b109de1ae2e1"


@pytest_asyncio.fixture
async def client():
    async with PortalWSClient(BASE_URL, token=TOKEN) as c:
        yield c


# ---------- Connection ----------


@pytest.mark.asyncio
async def test_connect_disconnect():
    ws = PortalWSClient(BASE_URL, token=TOKEN)
    await ws.connect()
    await ws.close()


# ---------- Query methods ----------


@pytest.mark.asyncio
async def test_get_version(client: PortalWSClient):
    version = await client.get_version()
    assert version is not None
    print("version:", version)


@pytest.mark.asyncio
async def test_get_state(client: PortalWSClient):
    state = await client.get_state()
    assert state is not None
    print("state type:", type(state))


@pytest.mark.asyncio
async def test_get_state_no_filter(client: PortalWSClient):
    state = await client.get_state(filter=False)
    assert state is not None
    print("state(no filter) type:", type(state))


@pytest.mark.asyncio
async def test_get_packages(client: PortalWSClient):
    packages = await client.get_packages()
    assert packages is not None
    print("packages:", type(packages))


@pytest.mark.asyncio
async def test_get_time(client: PortalWSClient):
    t = await client.get_time()
    assert t is not None
    print("time:", t)


# ---------- Screenshot (binary frame) ----------


@pytest.mark.asyncio
async def test_take_screenshot(client: PortalWSClient):
    png = await client.take_screenshot()
    assert isinstance(png, bytes)
    assert len(png) > 100
    assert png[:4] == b"\x89PNG", "Expected PNG magic bytes"
    with open("tmp/ws_screenshot.png", "wb") as f:
        f.write(png)
    print(f"screenshot: {len(png)} bytes, saved to tmp/ws_screenshot.png")


@pytest.mark.asyncio
async def test_take_screenshot_with_overlay(client: PortalWSClient):
    png = await client.take_screenshot(hide_overlay=False)
    assert isinstance(png, bytes)
    assert png[:4] == b"\x89PNG"
    with open("tmp/ws_screenshot_overlay.png", "wb") as f:
        f.write(png)
    print(f"screenshot(overlay): {len(png)} bytes, saved to tmp/ws_screenshot_overlay.png")


# ---------- Action methods ----------


@pytest.mark.asyncio
async def test_tap(client: PortalWSClient):
    result = await client.tap(100, 100)
    print("tap:", result)


@pytest.mark.asyncio
async def test_swipe(client: PortalWSClient):
    result = await client.swipe(200, 500, 200, 200, duration=300)
    print("swipe:", result)


@pytest.mark.asyncio
async def test_global_action(client: PortalWSClient):
    # GLOBAL_ACTION_BACK = 1
    result = await client.global_action(1)
    print("global_action(BACK):", result)


@pytest.mark.asyncio
async def test_input_text(client: PortalWSClient):
    result = await client.input_text("hello", clear=True)
    print("input_text:", result)


@pytest.mark.asyncio
async def test_clear_input(client: PortalWSClient):
    result = await client.clear_input()
    print("clear_input:", result)


@pytest.mark.asyncio
async def test_press_key(client: PortalWSClient):
    # KEYCODE_HOME = 3
    result = await client.press_key(3)
    print("press_key(HOME):", result)


@pytest.mark.asyncio
async def test_start_app(client: PortalWSClient):
    result = await client.start_app("com.android.settings")
    print("start_app:", result)
    await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_stop_app(client: PortalWSClient):
    result = await client.stop_app("com.android.settings")
    print("stop_app:", result)


# ---------- Concurrent requests ----------


@pytest.mark.asyncio
async def test_concurrent_requests(client: PortalWSClient):
    """Verify UUID matching works with multiple concurrent requests."""
    results = await asyncio.gather(
        client.get_version(),
        client.get_time(),
        client.get_packages(),
    )
    assert len(results) == 3
    print("concurrent results:", [type(r) for r in results])


# ---------- Auto-reconnect ----------


@pytest.mark.asyncio
async def test_auto_reconnect():
    """Verify that calling a method after disconnect triggers reconnect."""
    ws = PortalWSClient(BASE_URL, token=TOKEN)
    await ws.connect()
    # Force close
    await ws.close()
    # Should auto-reconnect
    ws._closed = False
    ws._ws = None
    version = await ws.get_version()
    assert version is not None
    print("reconnect version:", version)
    await ws.close()


# ---------- Run directly ----------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
