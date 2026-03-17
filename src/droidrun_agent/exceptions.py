"""Portal client exceptions."""

from __future__ import annotations


class PortalError(Exception):
    """Base exception for Portal client errors."""


class PortalConnectionError(PortalError):
    """Failed to connect to Portal server."""


class PortalAuthError(PortalError):
    """Authentication failed (invalid or missing token)."""


class PortalTimeoutError(PortalError):
    """Request timed out."""


class PortalResponseError(PortalError):
    """Server returned an unexpected or error response."""
