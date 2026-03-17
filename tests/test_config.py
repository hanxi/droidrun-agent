"""Tests for PortalConfig."""

from __future__ import annotations

import os

import pytest

from droidrun_agent.config import PortalConfig


class TestPortalConfigDirect:
    """Test direct construction."""

    def test_defaults(self) -> None:
        cfg = PortalConfig(base_url="http://localhost:8080", token="tok")
        assert cfg.base_url == "http://localhost:8080"
        assert cfg.token == "tok"
        assert cfg.timeout == 10.0
        assert cfg.transport == "http"

    def test_custom_values(self) -> None:
        cfg = PortalConfig(base_url="ws://1.2.3.4:8081", token="abc", timeout=5.0, transport="ws")
        assert cfg.transport == "ws"
        assert cfg.timeout == 5.0


class TestPortalConfigFromEnv:
    """Test from_env() class method."""

    def test_required_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORTAL_BASE_URL", "http://10.0.0.1:8080")
        monkeypatch.setenv("PORTAL_TOKEN", "secret")
        cfg = PortalConfig.from_env()
        assert cfg.base_url == "http://10.0.0.1:8080"
        assert cfg.token == "secret"
        assert cfg.timeout == 10.0
        assert cfg.transport == "http"

    def test_all_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORTAL_BASE_URL", "ws://192.168.1.1:8081")
        monkeypatch.setenv("PORTAL_TOKEN", "tok123")
        monkeypatch.setenv("PORTAL_TIMEOUT", "30")
        monkeypatch.setenv("PORTAL_TRANSPORT", "ws")
        cfg = PortalConfig.from_env()
        assert cfg.base_url == "ws://192.168.1.1:8081"
        assert cfg.timeout == 30.0
        assert cfg.transport == "ws"

    def test_missing_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PORTAL_BASE_URL", raising=False)
        monkeypatch.setenv("PORTAL_TOKEN", "tok")
        with pytest.raises(ValueError, match="PORTAL_BASE_URL"):
            PortalConfig.from_env()

    def test_missing_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORTAL_BASE_URL", "http://localhost:8080")
        monkeypatch.delenv("PORTAL_TOKEN", raising=False)
        with pytest.raises(ValueError, match="PORTAL_TOKEN"):
            PortalConfig.from_env()

    def test_invalid_transport(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORTAL_BASE_URL", "http://localhost:8080")
        monkeypatch.setenv("PORTAL_TOKEN", "tok")
        monkeypatch.setenv("PORTAL_TRANSPORT", "grpc")
        with pytest.raises(ValueError, match="'http' or 'ws'"):
            PortalConfig.from_env()

    def test_transport_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORTAL_BASE_URL", "http://localhost:8080")
        monkeypatch.setenv("PORTAL_TOKEN", "tok")
        monkeypatch.setenv("PORTAL_TRANSPORT", "WS")
        cfg = PortalConfig.from_env()
        assert cfg.transport == "ws"


class TestPortalConfigCreateClient:
    """Test create_client() factory."""

    def test_http_client(self) -> None:
        from droidrun_agent.http_client import PortalHTTPClient

        cfg = PortalConfig(base_url="http://localhost:8080", token="tok", transport="http")
        client = cfg.create_client()
        assert isinstance(client, PortalHTTPClient)
        assert client.base_url == "http://localhost:8080"
        assert client.token == "tok"
        assert client.timeout == 10.0

    def test_ws_client(self) -> None:
        from droidrun_agent.ws_client import PortalWSClient

        cfg = PortalConfig(base_url="ws://localhost:8081", token="tok", timeout=5.0, transport="ws")
        client = cfg.create_client()
        assert isinstance(client, PortalWSClient)
        assert client.base_url == "ws://localhost:8081"
        assert client.token == "tok"
        assert client.timeout == 5.0
