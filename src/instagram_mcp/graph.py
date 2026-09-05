"""Thin HTTP client for the Meta Graph API."""

import requests

from instagram_mcp.auth import InstagramAuth

REQUEST_TIMEOUT = 60


class GraphAPIError(Exception):
    """Raised when the Graph API returns an error response."""

    def __init__(self, message: str, code: int | None = None, error_type: str | None = None):
        super().__init__(message)
        self.code = code
        self.error_type = error_type


class GraphClient:
    """Executes authenticated requests against the Graph API."""

    def __init__(self, auth: InstagramAuth):
        self.auth = auth

    def _url(self, path: str) -> str:
        return f"{self.auth.graph_base_url}/{self.auth.graph_api_version}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, params: dict | None = None) -> dict:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        params["access_token"] = self.auth.access_token
        response = requests.request(
            method, self._url(path), params=params, timeout=REQUEST_TIMEOUT
        )
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise GraphAPIError(f"Non-JSON response from Graph API: {response.text[:200]}")

        if isinstance(data, dict) and "error" in data:
            err = data["error"]
            raise GraphAPIError(
                err.get("error_user_msg") or err.get("message") or "Unknown Graph API error",
                code=err.get("code"),
                error_type=err.get("type"),
            )
        response.raise_for_status()
        return data

    def get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params)

    def post(self, path: str, params: dict | None = None) -> dict:
        return self._request("POST", path, params)

    def delete(self, path: str, params: dict | None = None) -> dict:
        return self._request("DELETE", path, params)

    def get_all_pages(self, path: str, params: dict | None = None, max_items: int = 200) -> list:
        """GET with cursor pagination, following `paging.next` up to max_items."""
        items: list = []
        params = dict(params or {})
        while True:
            data = self.get(path, params)
            items.extend(data.get("data", []))
            if len(items) >= max_items:
                return items[:max_items]
            after = data.get("paging", {}).get("cursors", {}).get("after")
            if not after or not data.get("paging", {}).get("next"):
                return items
            params["after"] = after
