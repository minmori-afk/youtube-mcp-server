"""Credential management for the Instagram Graph API.

The Instagram Graph API (professional accounts) authenticates with a
long-lived user access token from a Meta app, plus the Instagram
professional account ID. Users generate both once in the Meta developer
tools and provide them via environment variables or a config file.
"""

import json
import os
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".instagram-mcp"
CONFIG_FILE = "config.json"

DEFAULT_GRAPH_API_VERSION = "v23.0"
DEFAULT_GRAPH_BASE_URL = "https://graph.facebook.com"


class AuthError(Exception):
    pass


class InstagramAuth:
    """Resolves the access token and Instagram account ID for API calls.

    Resolution order for each value: explicit constructor argument,
    environment variable, config file (~/.instagram-mcp/config.json).
    """

    def __init__(
        self,
        access_token: str | None = None,
        ig_user_id: str | None = None,
        config_dir: str | Path | None = None,
        graph_api_version: str | None = None,
        graph_base_url: str | None = None,
    ):
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
        self.config_path = self.config_dir / CONFIG_FILE

        self._access_token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        self._ig_user_id = ig_user_id or os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")

        self.graph_api_version = (
            graph_api_version
            or os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            or DEFAULT_GRAPH_API_VERSION
        )
        self.graph_base_url = (
            graph_base_url
            or os.environ.get("INSTAGRAM_GRAPH_BASE_URL")
            or DEFAULT_GRAPH_BASE_URL
        ).rstrip("/")

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        try:
            return json.loads(self.config_path.read_text())
        except Exception:
            return {}

    def save_config(self, access_token: str | None = None, ig_user_id: str | None = None):
        """Persist credentials to the config file (merging with existing values)."""
        config = self._load_config()
        if access_token:
            config["access_token"] = access_token
            self._access_token = access_token
        if ig_user_id:
            config["ig_user_id"] = ig_user_id
            self._ig_user_id = ig_user_id
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(config, indent=2))
        try:
            self.config_path.chmod(0o600)
        except OSError:
            pass

    @property
    def access_token(self) -> str:
        token = self._access_token or self._load_config().get("access_token")
        if not token:
            raise AuthError(
                "No Instagram access token configured. Set the INSTAGRAM_ACCESS_TOKEN "
                "env var, or store it with the instagram_configure tool. Generate a "
                "long-lived token for your Meta app in the Meta developer tools "
                "(Graph API Explorer > Generate Access Token, then exchange for a "
                "long-lived token)."
            )
        return token

    @property
    def ig_user_id(self) -> str:
        ig_id = self._ig_user_id or self._load_config().get("ig_user_id")
        if not ig_id:
            raise AuthError(
                "No Instagram account ID configured. Set the "
                "INSTAGRAM_BUSINESS_ACCOUNT_ID env var, or store it with the "
                "instagram_configure tool. This is the ID of your Instagram "
                "professional (business/creator) account, found via "
                "GET /me/accounts -> page -> instagram_business_account."
            )
        return str(ig_id)

    def status(self) -> dict:
        """Return current credential status (without leaking the token)."""
        config = self._load_config()
        token = self._access_token or config.get("access_token")
        ig_id = self._ig_user_id or config.get("ig_user_id")
        return {
            "access_token_configured": bool(token),
            "ig_user_id_configured": bool(ig_id),
            "ig_user_id": str(ig_id) if ig_id else None,
            "config_path": str(self.config_path),
            "config_file_exists": self.config_path.exists(),
            "graph_api_version": self.graph_api_version,
            "graph_base_url": self.graph_base_url,
        }
