---
name: portal-client
description: DroidRun Portal HTTP/WebSocket client. Controls Android devices via HTTP or WebSocket, supporting tap, swipe, screenshot, text input, UI state retrieval and more. Use this skill when the user needs to interact with an Android device running DroidRun Portal.
---

# Portal Client

Provides two async clients, `PortalHTTPClient` and `PortalWSClient`, for communicating with Android devices running DroidRun Portal. All methods are `async` and support `async with` context managers.

## Installation

```bash
cd droidrun-agent && uv sync
```

## PortalHTTPClient

Communicates with Portal's HTTP server (default port 8080) using Bearer token authentication.

```python
from droidrun_agent import PortalHTTPClient

async with PortalHTTPClient(base_url="http://192.168.1.100:8080", token="YOUR_TOKEN") as client:
    await client.ping()
    state = await client.get_state_full()
    await client.tap(200, 400)
    png = await client.take_screenshot()
```

### Query Methods (GET)

| Signature | Return Type | Description |
|-----------|-------------|-------------|
| `ping()` | `dict` | Health check, no auth required |
| `get_a11y_tree()` | `dict` | Simplified accessibility tree |
| `get_a11y_tree_full(*, filter: bool = True)` | `dict` | Full accessibility tree, `filter=False` keeps small elements |
| `get_state()` | `dict` | Simplified UI state |
| `get_state_full(*, filter: bool = True)` | `dict` | Full UI state (a11y_tree + phone_state), `filter=False` keeps small elements |
| `get_phone_state()` | `dict` | Phone state info (current app, activity, keyboard status, etc.) |
| `get_version()` | `str` | Portal app version string |
| `get_packages()` | `list[dict]` | List of launchable apps, each containing `packageName`, `label`, etc. |
| `take_screenshot(*, hide_overlay: bool = True)` | `bytes` | Device screenshot as PNG bytes, `hide_overlay=False` to show overlay |

### Action Methods (POST)

| Signature | Return Type | Description |
|-----------|-------------|-------------|
| `tap(x: int, y: int)` | `dict` | Tap screen coordinates |
| `swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration: int \| None = None)` | `dict` | Swipe gesture, `duration` is optional duration in milliseconds |
| `global_action(action: int)` | `dict` | Execute Android accessibility global action (1=Back, 2=Home, 3=Recents) |
| `start_app(package: str, activity: str \| None = None, stop_before_launch: bool = False)` | `dict` | Launch an app |
| `stop_app(package: str)` | `dict` | Best-effort stop an app |
| `input_text(text: str, clear: bool = True)` | `dict` | Input text (auto base64-encoded), `clear=True` clears field first |
| `clear_input()` | `dict` | Clear the focused input field |
| `press_key(key_code: int)` | `dict` | Send Android key code (e.g. 66=Enter, 3=Home, 4=Back) |
| `set_overlay_offset(offset: int)` | `dict` | Set overlay vertical offset in pixels |
| `set_socket_port(port: int)` | `dict` | Update the HTTP server port |

## PortalWSClient

Communicates with Portal's WebSocket server (default port 8081) using JSON-RPC style messages. Automatically reconnects when a method is called on a broken connection.

```python
from droidrun_agent import PortalWSClient

async with PortalWSClient(host="192.168.1.100", port=8081, token="YOUR_TOKEN") as ws:
    await ws.tap(200, 400)
    state = await ws.get_state()
    png = await ws.take_screenshot()
    time_ms = await ws.get_time()
```

### Methods

Supports all action methods from PortalHTTPClient (`tap`, `swipe`, `global_action`, `start_app`, `stop_app`, `input_text`, `clear_input`, `press_key`, `set_overlay_offset`, `set_socket_port`, `take_screenshot`) with identical signatures.

Query methods:

| Signature | Return Type | Description |
|-----------|-------------|-------------|
| `get_packages()` | `Any` | List of launchable packages |
| `get_state(*, filter: bool = True)` | `Any` | Full state, `filter=False` keeps small elements |
| `get_version()` | `Any` | Portal version string |
| `get_time()` | `Any` | Device Unix timestamp in milliseconds |
| `install(urls: list[str], hide_overlay: bool = True)` | `Any` | Install APK(s) from URL(s), supports split APKs (WebSocket only) |

WebSocket screenshots automatically parse binary frames and return PNG `bytes` directly.

## Exceptions

All exceptions inherit from `PortalError`:

| Exception | Trigger |
|-----------|---------|
| `PortalError` | Base exception |
| `PortalConnectionError` | Cannot connect to Portal server |
| `PortalAuthError` | Invalid or missing token (HTTP 401/403) |
| `PortalTimeoutError` | Request timed out |
| `PortalResponseError` | Server returned unexpected status or error |

## Full Usage Example

```python
import asyncio
from droidrun_agent import PortalHTTPClient, PortalWSClient

async def demo_http():
    async with PortalHTTPClient("http://localhost:8080", token="YOUR_TOKEN") as client:
        print(await client.ping())
        print("Version:", await client.get_version())
        print("Packages:", len(await client.get_packages()))

        await client.tap(500, 800)
        await client.swipe(500, 1500, 500, 500, duration=300)
        await client.input_text("Hello World")
        await client.press_key(66)  # Enter

        state = await client.get_state_full()
        png = await client.take_screenshot()
        print(f"Screenshot: {len(png)} bytes")

async def demo_ws():
    async with PortalWSClient("localhost", 8081, token="YOUR_TOKEN") as ws:
        print("Version:", await ws.get_version())
        print("Time:", await ws.get_time())

        await ws.tap(500, 800)
        await ws.start_app("com.android.settings")

        png = await ws.take_screenshot()
        print(f"Screenshot: {len(png)} bytes")

asyncio.run(demo_http())
asyncio.run(demo_ws())
```
