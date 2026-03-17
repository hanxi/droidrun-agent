"""Integration tests for PortalHTTPClient.

Requires a running Portal HTTP server at localhost:8080.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from droidrun_agent import PortalHTTPClient

BASE_URL = "http://localhost:8080"
TOKEN = "eabfc22e-e795-4862-8046-b109de1ae2e1"


@pytest_asyncio.fixture
async def client():
    async with PortalHTTPClient(BASE_URL, token=TOKEN) as c:
        yield c


# ---------- GET endpoints ----------


@pytest.mark.asyncio
async def test_ping(client: PortalHTTPClient):
    result = await client.ping()
    assert result is not None
    print("ping:", result)


@pytest.mark.asyncio
async def test_get_version(client: PortalHTTPClient):
    version = await client.get_version()
    assert isinstance(version, str)
    assert version != ""
    print("version:", version)


@pytest.mark.asyncio
async def test_get_state(client: PortalHTTPClient):
    state = await client.get_state()
    assert state is not None
    print("state keys:", list(state.keys()) if isinstance(state, dict) else type(state))


@pytest.mark.asyncio
async def test_get_state_full(client: PortalHTTPClient):
    state = await client.get_state_full()
    assert state is not None
    print(
        "state_full keys:",
        list(state.keys()) if isinstance(state, dict) else type(state),
    )


@pytest.mark.asyncio
async def test_get_state_full_no_filter(client: PortalHTTPClient):
    state = await client.get_state_full(filter=False)
    assert state is not None
    print(
        "state_full(no filter) keys:",
        list(state.keys()) if isinstance(state, dict) else type(state),
    )


@pytest.mark.asyncio
async def test_get_a11y_tree(client: PortalHTTPClient):
    tree = await client.get_a11y_tree()
    assert tree is not None
    print("a11y_tree type:", type(tree))


@pytest.mark.asyncio
async def test_get_a11y_tree_full(client: PortalHTTPClient):
    tree = await client.get_a11y_tree_full()
    assert tree is not None
    print("a11y_tree_full type:", type(tree))


@pytest.mark.asyncio
async def test_get_phone_state(client: PortalHTTPClient):
    state = await client.get_phone_state()
    assert state is not None
    print("phone_state:", state)


@pytest.mark.asyncio
async def test_get_packages(client: PortalHTTPClient):
    packages = await client.get_packages()
    assert isinstance(packages, list)
    assert len(packages) > 0
    print(f"packages: {len(packages)} apps")
    if packages:
        print("  first:", packages[0])


@pytest.mark.asyncio
async def test_take_screenshot(client: PortalHTTPClient):
    png = await client.take_screenshot()
    assert isinstance(png, bytes)
    assert len(png) > 100
    assert png[:4] == b"\x89PNG", "Expected PNG magic bytes"
    print(f"screenshot: {len(png)} bytes")


@pytest.mark.asyncio
async def test_take_screenshot_with_overlay(client: PortalHTTPClient):
    png = await client.take_screenshot(hide_overlay=False)
    assert isinstance(png, bytes)
    assert png[:4] == b"\x89PNG"
    print(f"screenshot(overlay): {len(png)} bytes")


# ---------- POST endpoints ----------


@pytest.mark.asyncio
async def test_tap(client: PortalHTTPClient):
    result = await client.tap(100, 100)
    print("tap:", result)


@pytest.mark.asyncio
async def test_swipe(client: PortalHTTPClient):
    result = await client.swipe(200, 500, 200, 200, duration=300)
    print("swipe:", result)


@pytest.mark.asyncio
async def test_global_action(client: PortalHTTPClient):
    # GLOBAL_ACTION_BACK = 1
    result = await client.global_action(1)
    print("global_action(BACK):", result)


@pytest.mark.asyncio
async def test_input_text(client: PortalHTTPClient):
    result = await client.input_text("hello", clear=True)
    print("input_text:", result)


@pytest.mark.asyncio
async def test_clear_input(client: PortalHTTPClient):
    result = await client.clear_input()
    print("clear_input:", result)


@pytest.mark.asyncio
async def test_press_key(client: PortalHTTPClient):
    # KEYCODE_HOME = 3
    result = await client.press_key(3)
    print("press_key(HOME):", result)


@pytest.mark.asyncio
async def test_start_app(client: PortalHTTPClient):
    result = await client.start_app("com.android.settings")
    print("start_app:", result)
    await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_stop_app(client: PortalHTTPClient):
    result = await client.stop_app("com.android.settings")
    print("stop_app:", result)


# ---------- Run directly ----------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
