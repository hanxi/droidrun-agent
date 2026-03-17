"""Portal connection configuration with environment variable support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .http_client import PortalHTTPClient
    from .ws_client import PortalWSClient


@dataclass
class PortalConfig:
    """Configuration for connecting to a DroidRun Portal device.

    Can be constructed directly or loaded from environment variables
    via :meth:`from_env`.
    """

    base_url: str
    token: str
    timeout: float = 10.0
    transport: str = "http"

    @classmethod
    def from_env(cls) -> PortalConfig:
        """Create a config from environment variables.

        Environment variables:
            PORTAL_BASE_URL  (required) - Portal HTTP or WS base URL.
            PORTAL_TOKEN     (required) - Bearer token.
            PORTAL_TIMEOUT   (optional) - Request timeout in seconds, default 10.
            PORTAL_TRANSPORT (optional) - ``http`` or ``ws``, default ``http``.
        """
        base_url = os.environ.get("PORTAL_BASE_URL", "")
        token = os.environ.get("PORTAL_TOKEN", "")
        if not base_url:
            raise ValueError("PORTAL_BASE_URL environment variable is required")
        if not token:
            raise ValueError("PORTAL_TOKEN environment variable is required")

        timeout = float(os.environ.get("PORTAL_TIMEOUT", "10.0"))
        transport = os.environ.get("PORTAL_TRANSPORT", "http").lower()
        if transport not in ("http", "ws"):
            raise ValueError(f"PORTAL_TRANSPORT must be 'http' or 'ws', got '{transport}'")

        return cls(base_url=base_url, token=token, timeout=timeout, transport=transport)

    def create_client(self) -> PortalHTTPClient | PortalWSClient:
        """Create the appropriate client based on :attr:`transport`."""
        if self.transport == "ws":
            from .ws_client import PortalWSClient

            return PortalWSClient(base_url=self.base_url, token=self.token, timeout=self.timeout)

        from .http_client import PortalHTTPClient

        return PortalHTTPClient(base_url=self.base_url, token=self.token, timeout=self.timeout)
