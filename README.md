# [droidrun-agent](https://github.com/hanxi/droidrun-agent)

[![PyPI version](https://img.shields.io/pypi/v/droidrun-agent)](https://pypi.org/project/droidrun-agent/)
[![Python](https://img.shields.io/pypi/pyversions/droidrun-agent)](https://pypi.org/project/droidrun-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Async Python client for the [DroidRun Portal](https://github.com/droidrun/droidrun-portal) local API. Provides both HTTP and WebSocket clients to control Android devices through Portal's accessibility service.

## Features

- **HTTP Client** (`PortalHTTPClient`) - Communicates with Portal's HTTP server (default port 8080)
- **WebSocket Client** (`PortalWSClient`) - Communicates with Portal's WebSocket server (default port 8081) using JSON-RPC style messages
- Bearer token authentication
- Async context manager support (`async with`)
- Automatic reconnection for WebSocket client
- Full type hints

## Installation

```bash
pip install droidrun-agent
```

Or install from source using [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/hanxi/droidrun-agent.git
cd droidrun-agent
uv sync
```

## Quick Start

### HTTP Client

```python
import asyncio
from droidrun_agent import PortalHTTPClient

async def main():
    async with PortalHTTPClient("http://192.168.1.100:8080", token="YOUR_TOKEN") as client:
        # Health check (no auth required)
        await client.ping()

        # Get device UI state
        state = await client.get_state_full()
        print(state)

        # Tap on screen coordinates
        await client.tap(200, 400)

        # Take a screenshot (returns PNG bytes)
        png_data = await client.take_screenshot()
        with open("screenshot.png", "wb") as f:
            f.write(png_data)

asyncio.run(main())
```

### WebSocket Client

```python
import asyncio
from droidrun_agent import PortalWSClient

async def main():
    async with PortalWSClient("ws://192.168.1.100:8081", token="YOUR_TOKEN") as ws:
        # Tap on screen coordinates
        await ws.tap(200, 400)

        # Get device state
        state = await ws.get_state()
        print(state)

        # Take a screenshot (returns PNG bytes)
        png_data = await ws.take_screenshot()
        with open("screenshot.png", "wb") as f:
            f.write(png_data)

        # Install APK from URL (WebSocket only)
        await ws.install(["https://example.com/app.apk"])

asyncio.run(main())
```

## Documentation

For detailed API documentation of the DroidRun Portal local API, see:
- [Local API Documentation](https://github.com/droidrun/droidrun-portal/blob/main/docs/local-api.md)

## API Reference

### PortalHTTPClient

| Method | Description |
|---|---|
| `ping()` | Health check (no auth required) |
| `get_a11y_tree()` | Get simplified accessibility tree |
| `get_a11y_tree_full(filter=True)` | Get full accessibility tree |
| `get_state()` | Get simplified UI state |
| `get_state_full(filter=True)` | Get full UI state (a11y tree + phone state) |
| `get_phone_state()` | Get phone state info |
| `get_version()` | Get Portal app version string |
| `get_packages()` | Get list of launchable packages |
| `take_screenshot(hide_overlay=True)` | Take device screenshot, returns PNG bytes |
| `tap(x, y)` | Tap screen coordinates |
| `swipe(start_x, start_y, end_x, end_y, duration=None)` | Swipe gesture |
| `global_action(action)` | Execute accessibility global action |
| `start_app(package, activity=None, stop_before_launch=False)` | Launch an app |
| `stop_app(package)` | Stop an app |
| `input_text(text, clear=True)` | Input text via Portal keyboard |
| `clear_input()` | Clear focused input field |
| `press_key(key_code)` | Send an Android key code |
| `set_overlay_offset(offset)` | Set overlay vertical offset in pixels |
| `set_socket_port(port)` | Update the HTTP server port |

### PortalWSClient

Supports all methods from HTTP client, plus:

| Method | Description |
|---|---|
| `get_time()` | Get device Unix timestamp in milliseconds |
| `install(urls, hide_overlay=True)` | Install APK(s) from URL(s), supports split APKs |

### Exceptions

| Exception | Description |
|---|---|
| `PortalError` | Base exception for all Portal client errors |
| `PortalConnectionError` | Failed to connect to Portal server |
| `PortalAuthError` | Authentication failed (invalid or missing token) |
| `PortalTimeoutError` | Request timed out |
| `PortalResponseError` | Server returned an unexpected or error response |

## Requirements

- Python >= 3.11
- [httpx](https://www.python-httpx.org/) >= 0.28.1
- [websockets](https://websockets.readthedocs.io/) >= 12.0

## Development Workflow

This project uses [uv](https://docs.astral.sh/uv/) for development. Here are the common development commands:

### Code Formatting

```bash
# Format all Python code
uv format

# Check formatting without making changes
uv format --check
```

### Code Quality

```bash
# Run code quality checks
uv run ruff check .

# Automatically fix fixable issues
uv run ruff check --fix .
```

### Testing

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run tests and show coverage
uv run pytest --cov=src
```

### Dependency Management

```bash
# Install development dependencies
uv sync --group dev

# Add a new dependency
uv add package_name

# Add a development dependency
uv add --group dev package_name

# Remove a dependency
uv remove package_name
```

### Complete Development Flow

```bash
# 1. Format code
uv format

# 2. Check code quality
uv run ruff check .

# 3. Run tests
uv run pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
