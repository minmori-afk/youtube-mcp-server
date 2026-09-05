"""Instagram MCP Server — FastMCP entry point."""

import os

from mcp.server.fastmcp import FastMCP

from instagram_mcp.auth import InstagramAuth
from instagram_mcp.graph import GraphClient

mcp = FastMCP(
    "Instagram MCP Server",
    instructions=(
        "MCP server for managing an Instagram professional account via the "
        "Instagram Graph API: profile, media, publishing, comments, insights, "
        "and hashtag research."
    ),
)

# Shared state
auth = InstagramAuth(
    access_token=os.environ.get("INSTAGRAM_ACCESS_TOKEN"),
    ig_user_id=os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID"),
    config_dir=os.environ.get("INSTAGRAM_MCP_CONFIG_DIR"),
)
graph = GraphClient(auth)


# --- Auth tools ---


@mcp.tool()
def instagram_auth_status() -> dict:
    """Check current Instagram credential configuration status."""
    return auth.status()


@mcp.tool()
def instagram_configure(access_token: str | None = None, ig_user_id: str | None = None) -> dict:
    """Store Instagram credentials in the local config file.

    Args:
        access_token: Long-lived Meta Graph API user access token
        ig_user_id: Instagram professional account ID
    """
    if not access_token and not ig_user_id:
        return {"status": "error", "detail": "Provide access_token and/or ig_user_id"}
    auth.save_config(access_token=access_token, ig_user_id=ig_user_id)
    return {"status": "saved", "detail": auth.status()}


# --- Register tool modules ---
# Import tool modules so their @mcp.tool() decorators run

from instagram_mcp.tools import (  # noqa: E402
    account,  # noqa: F401
    comments,  # noqa: F401
    hashtags,  # noqa: F401
    media,  # noqa: F401
    publishing,  # noqa: F401
)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
