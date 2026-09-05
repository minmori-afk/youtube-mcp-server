"""Media tools — list and inspect posts, reels, and stories."""

from instagram_mcp.server import auth, graph, mcp

MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,permalink,"
    "thumbnail_url,timestamp,like_count,comments_count"
)


def _format_media(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "type": item.get("media_type"),
        "product_type": item.get("media_product_type"),
        "caption": (item.get("caption") or "")[:500],
        "permalink": item.get("permalink"),
        "media_url": item.get("media_url"),
        "thumbnail_url": item.get("thumbnail_url"),
        "timestamp": item.get("timestamp"),
        "likes": item.get("like_count", 0),
        "comments": item.get("comments_count", 0),
    }


@mcp.tool()
def instagram_list_media(max_results: int = 25) -> dict:
    """List recent posts and reels on the connected account.

    Args:
        max_results: Number of media items to return (max 100)
    """
    items = graph.get_all_pages(
        f"{auth.ig_user_id}/media",
        {"fields": MEDIA_FIELDS, "limit": min(max_results, 100)},
        max_items=min(max_results, 100),
    )
    media = [_format_media(item) for item in items]
    return {"media": media, "total": len(media)}


@mcp.tool()
def instagram_get_media(media_id: str) -> dict:
    """Get details for a single post or reel.

    Args:
        media_id: Instagram media ID (from instagram_list_media)
    """
    item = graph.get(media_id, {"fields": MEDIA_FIELDS + ",owner,is_comment_enabled"})
    result = _format_media(item)
    result["caption"] = item.get("caption") or ""
    result["is_comment_enabled"] = item.get("is_comment_enabled")
    return result


@mcp.tool()
def instagram_get_media_insights(media_id: str, metrics: str | None = None) -> dict:
    """Get performance insights for a post, reel, or story.

    Args:
        media_id: Instagram media ID
        metrics: Comma-separated metric names. Defaults to
            "views,reach,likes,comments,saved,shares,total_interactions".
            For stories try "views,reach,replies,navigation".
    """
    metrics = metrics or "views,reach,likes,comments,saved,shares,total_interactions"
    data = graph.get(f"{media_id}/insights", {"metric": metrics})

    results = {}
    for metric in data.get("data", []):
        values = metric.get("values", [])
        results[metric.get("name")] = values[0].get("value") if values else None
    return {"media_id": media_id, "insights": results}


@mcp.tool()
def instagram_list_stories() -> dict:
    """List currently live stories on the connected account."""
    data = graph.get(
        f"{auth.ig_user_id}/stories",
        {"fields": "id,media_type,media_url,permalink,timestamp"},
    )
    stories = [
        {
            "id": item.get("id"),
            "type": item.get("media_type"),
            "media_url": item.get("media_url"),
            "permalink": item.get("permalink"),
            "timestamp": item.get("timestamp"),
        }
        for item in data.get("data", [])
    ]
    return {"stories": stories, "total": len(stories)}
