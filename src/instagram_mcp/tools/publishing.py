"""Publishing tools — post photos, reels, carousels, and stories.

Instagram content publishing is a two-step flow: create a media container,
then publish it. Media must be hosted on a publicly accessible URL.
"""

import time

from instagram_mcp.graph import GraphAPIError
from instagram_mcp.server import auth, graph, mcp

CONTAINER_POLL_INTERVAL = 5
CONTAINER_POLL_TIMEOUT = 300


def _wait_for_container(creation_id: str) -> str:
    """Poll a media container until processing finishes. Returns final status."""
    deadline = time.monotonic() + CONTAINER_POLL_TIMEOUT
    while True:
        status = graph.get(creation_id, {"fields": "status_code,status"})
        code = status.get("status_code")
        if code == "FINISHED":
            return code
        if code == "ERROR":
            raise GraphAPIError(f"Media container processing failed: {status.get('status')}")
        if time.monotonic() >= deadline:
            raise GraphAPIError(
                f"Media container not ready after {CONTAINER_POLL_TIMEOUT}s "
                f"(status: {code}). Try publishing later with creation_id={creation_id}."
            )
        time.sleep(CONTAINER_POLL_INTERVAL)


def _publish_container(creation_id: str) -> dict:
    response = graph.post(
        f"{auth.ig_user_id}/media_publish", {"creation_id": creation_id}
    )
    media_id = response.get("id")
    item = graph.get(media_id, {"fields": "id,permalink"})
    return {"media_id": media_id, "permalink": item.get("permalink"), "published": True}


@mcp.tool()
def instagram_publish_photo(image_url: str, caption: str = "") -> dict:
    """Publish a photo post to the connected account.

    Args:
        image_url: Publicly accessible URL of the image (JPEG recommended)
        caption: Post caption (may include hashtags and @mentions)
    """
    container = graph.post(
        f"{auth.ig_user_id}/media",
        {"image_url": image_url, "caption": caption},
    )
    return _publish_container(container["id"])


@mcp.tool()
def instagram_publish_reel(
    video_url: str,
    caption: str = "",
    share_to_feed: bool = True,
    cover_url: str | None = None,
) -> dict:
    """Publish a reel to the connected account.

    Video processing can take a few minutes; this tool waits for it.

    Args:
        video_url: Publicly accessible URL of the video (MP4/MOV)
        caption: Reel caption (may include hashtags and @mentions)
        share_to_feed: Whether the reel also appears in the main feed
        cover_url: Optional publicly accessible URL for the cover image
    """
    container = graph.post(
        f"{auth.ig_user_id}/media",
        {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true" if share_to_feed else "false",
            "cover_url": cover_url,
        },
    )
    _wait_for_container(container["id"])
    return _publish_container(container["id"])


@mcp.tool()
def instagram_publish_carousel(image_urls: list[str], caption: str = "") -> dict:
    """Publish a carousel post (2-10 images) to the connected account.

    Args:
        image_urls: Publicly accessible URLs of the images, in display order
        caption: Post caption (may include hashtags and @mentions)
    """
    if not 2 <= len(image_urls) <= 10:
        return {"status": "error", "detail": "A carousel needs 2-10 images"}

    children = []
    for url in image_urls:
        child = graph.post(
            f"{auth.ig_user_id}/media",
            {"image_url": url, "is_carousel_item": "true"},
        )
        children.append(child["id"])

    container = graph.post(
        f"{auth.ig_user_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
        },
    )
    return _publish_container(container["id"])


@mcp.tool()
def instagram_publish_story(
    image_url: str | None = None, video_url: str | None = None
) -> dict:
    """Publish a story to the connected account.

    Provide exactly one of image_url or video_url.

    Args:
        image_url: Publicly accessible URL of a story image
        video_url: Publicly accessible URL of a story video
    """
    if bool(image_url) == bool(video_url):
        return {"status": "error", "detail": "Provide exactly one of image_url or video_url"}

    params: dict = {"media_type": "STORIES"}
    if image_url:
        params["image_url"] = image_url
    else:
        params["video_url"] = video_url

    container = graph.post(f"{auth.ig_user_id}/media", params)
    if video_url:
        _wait_for_container(container["id"])
    return _publish_container(container["id"])


@mcp.tool()
def instagram_get_publishing_limit() -> dict:
    """Check how much of the 24-hour publishing quota (100 posts) is used."""
    data = graph.get(
        f"{auth.ig_user_id}/content_publishing_limit",
        {"fields": "quota_usage,config"},
    )
    entries = data.get("data", [])
    if not entries:
        return {"quota_usage": None}
    entry = entries[0]
    config = entry.get("config", {})
    return {
        "quota_usage": entry.get("quota_usage"),
        "quota_total": config.get("quota_total"),
        "quota_duration_seconds": config.get("quota_duration"),
    }
