"""Tests for Instagram auth and Graph client."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from instagram_mcp.auth import AuthError, InstagramAuth
from instagram_mcp.graph import GraphAPIError, GraphClient


def test_default_config_dir():
    ig_auth = InstagramAuth()
    assert ig_auth.config_dir == Path.home() / ".instagram-mcp"
    assert ig_auth.config_path == Path.home() / ".instagram-mcp" / "config.json"


def test_credentials_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "env-token")
    monkeypatch.setenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "17890000")
    ig_auth = InstagramAuth(config_dir=tmp_path)
    assert ig_auth.access_token == "env-token"
    assert ig_auth.ig_user_id == "17890000"


def test_explicit_overrides_env(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "env-token")
    ig_auth = InstagramAuth(access_token="explicit-token", config_dir=tmp_path)
    assert ig_auth.access_token == "explicit-token"


def test_credentials_from_config_file(tmp_path, monkeypatch):
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", raising=False)
    (tmp_path / "config.json").write_text(
        json.dumps({"access_token": "file-token", "ig_user_id": "17891111"})
    )
    ig_auth = InstagramAuth(config_dir=tmp_path)
    assert ig_auth.access_token == "file-token"
    assert ig_auth.ig_user_id == "17891111"


def test_missing_token_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    ig_auth = InstagramAuth(config_dir=tmp_path)
    with pytest.raises(AuthError, match="No Instagram access token"):
        _ = ig_auth.access_token


def test_missing_ig_user_id_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", raising=False)
    ig_auth = InstagramAuth(config_dir=tmp_path)
    with pytest.raises(AuthError, match="No Instagram account ID"):
        _ = ig_auth.ig_user_id


def test_save_config(tmp_path, monkeypatch):
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", raising=False)
    ig_auth = InstagramAuth(config_dir=tmp_path)
    ig_auth.save_config(access_token="saved-token", ig_user_id="17892222")
    saved = json.loads((tmp_path / "config.json").read_text())
    assert saved == {"access_token": "saved-token", "ig_user_id": "17892222"}
    assert ig_auth.access_token == "saved-token"


def test_status_does_not_leak_token(tmp_path, monkeypatch):
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    ig_auth = InstagramAuth(access_token="secret-token", ig_user_id="17893333", config_dir=tmp_path)
    status = ig_auth.status()
    assert status["access_token_configured"] is True
    assert status["ig_user_id"] == "17893333"
    assert "secret-token" not in json.dumps(status)


def test_graph_api_version_default():
    ig_auth = InstagramAuth()
    assert ig_auth.graph_api_version.startswith("v")
    assert ig_auth.graph_base_url.startswith("https://")


class TestGraphClient:
    def _client(self, tmp_path):
        return GraphClient(
            InstagramAuth(access_token="tok", ig_user_id="123", config_dir=tmp_path)
        )

    @patch("instagram_mcp.graph.requests.request")
    def test_get_adds_token_and_version(self, mock_request, tmp_path):
        mock_request.return_value = MagicMock(
            json=lambda: {"id": "123", "username": "acct"}
        )
        client = self._client(tmp_path)
        result = client.get("123", {"fields": "username"})

        assert result["username"] == "acct"
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert f"/{client.auth.graph_api_version}/123" in args[1]
        assert kwargs["params"]["access_token"] == "tok"

    @patch("instagram_mcp.graph.requests.request")
    def test_error_response_raises(self, mock_request, tmp_path):
        mock_request.return_value = MagicMock(
            json=lambda: {
                "error": {"message": "Invalid OAuth token", "type": "OAuthException", "code": 190}
            }
        )
        client = self._client(tmp_path)
        with pytest.raises(GraphAPIError, match="Invalid OAuth token") as exc_info:
            client.get("me")
        assert exc_info.value.code == 190

    @patch("instagram_mcp.graph.requests.request")
    def test_none_params_dropped(self, mock_request, tmp_path):
        mock_request.return_value = MagicMock(json=lambda: {"ok": True})
        client = self._client(tmp_path)
        client.get("123", {"fields": "id", "since": None})
        _, kwargs = mock_request.call_args
        assert "since" not in kwargs["params"]

    @patch("instagram_mcp.graph.requests.request")
    def test_pagination(self, mock_request, tmp_path):
        page1 = MagicMock(json=lambda: {
            "data": [{"id": "1"}, {"id": "2"}],
            "paging": {"cursors": {"after": "cur1"}, "next": "https://next"},
        })
        page2 = MagicMock(json=lambda: {"data": [{"id": "3"}], "paging": {}})
        mock_request.side_effect = [page1, page2]

        client = self._client(tmp_path)
        items = client.get_all_pages("123/media", {"limit": 25})
        assert [i["id"] for i in items] == ["1", "2", "3"]

    @patch("instagram_mcp.graph.requests.request")
    def test_pagination_respects_max_items(self, mock_request, tmp_path):
        page1 = MagicMock(json=lambda: {
            "data": [{"id": "1"}, {"id": "2"}],
            "paging": {"cursors": {"after": "cur1"}, "next": "https://next"},
        })
        mock_request.side_effect = [page1]

        client = self._client(tmp_path)
        items = client.get_all_pages("123/media", max_items=2)
        assert len(items) == 2
        assert mock_request.call_count == 1
