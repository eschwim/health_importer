"""Tests for libs/web.py OAuthFetchWebServer functionality."""

import json
import tempfile
from typing import TYPE_CHECKING
from unittest import mock

import pytest

if TYPE_CHECKING:
    from libs.web import OAuthFetchWebServer


@pytest.fixture
def web_server() -> "OAuthFetchWebServer":
    """Create an OAuthFetchWebServer instance for testing."""
    with mock.patch("libs.web.constants") as mock_constants:
        mock_constants.OURA_CLIENT_ID = "test_client_id"
        mock_constants.OURA_CLIENT_SECRET = "test_client_secret"
        mock_constants.REDIRECT_URI = "http://localhost:8080/"
        mock_constants.AUTHORIZE_URL = "https://cloud.ouraring.com/oauth/authorize"
        mock_constants.TOKEN_URL = "https://api.ouraring.com/oauth/token"
        mock_constants.SCOPES = []
        mock_constants.TOKEN_FILE = "/tmp/test_tokens"
        mock_constants.HTTP_PORT = 8080

        from libs.web import OAuthFetchWebServer

        token_cfg: dict[str, str | int] = {}
        return OAuthFetchWebServer(token_cfg)


class TestOAuthFetchWebServer:
    """Tests for OAuthFetchWebServer class."""

    def test_init_sets_auth_params(self, web_server: "OAuthFetchWebServer") -> None:
        """Test that __init__ correctly sets auth parameters."""
        assert web_server.auth_params["client_id"] == "test_client_id"
        assert web_server.auth_params["redirect_uri"] == "http://localhost:8080/"
        assert web_server.auth_params["response_type"] == "code"

    async def test_fetch_token_returns_message_when_no_code(
        self, web_server: "OAuthFetchWebServer"
    ) -> None:
        """Test that fetch_token returns message when code is None."""
        result = await web_server.fetch_token(None)
        assert "No authorization code found" in result

    def test_write_token_file(self, web_server: "OAuthFetchWebServer") -> None:
        """Test that _write_token_file writes JSON correctly."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = f.name

        with mock.patch("libs.web.constants") as mock_constants:
            mock_constants.TOKEN_FILE = temp_path

            web_server.token_cfg = {"access_token": "test", "expires_in": 86400}
            web_server._write_token_file()

            with open(temp_path) as f:
                data = json.load(f)
                assert data["access_token"] == "test"
                assert data["expires_in"] == 86400

    def test_read_token_file(self, web_server: "OAuthFetchWebServer") -> None:
        """Test that _read_token_file reads JSON correctly."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump({"access_token": "test_token", "expires_in": 3600}, f)
            temp_path = f.name

        with mock.patch("libs.web.constants") as mock_constants:
            mock_constants.TOKEN_FILE = temp_path

            result = web_server._read_token_file()
            assert result["access_token"] == "test_token"
            assert result["expires_in"] == 3600
