"""Hashtag tools — research hashtags and browse their top/recent media."""

from instagram_mcp.server import auth, graph, mcp

HASHTAG_MEDIA_FIELDS = "id,caption,media_type,permalink,timestamp,like_count,comments_count"


@mcp.tool()
def instagram_search_hashtag(query: str) -> dict:
    """Look up a hashtag's ID by name (needed for hashtag media queries).

    Args:
        query: Hashtag name without the # prefix, e.g. "travel"
    """
    data = graph.get(
        "ig_hashtag_search",
        {"user_id": auth.ig_user_id, "q": query.lstrip("#")},
    )
    hashtags = data.get("data", [])
    return {
        "query": query,
        "hashtag_id": hashtags[0]["id"] if hashtags else None,
        "results": hashtags,
    }


@mcp.tool()
def instagram_get_hashtag_media(
    hashtag_id: str, kind: str = "top", max_results: int = 25
) -> dict:
    """Get top or recent public media for a hashtag.

    Args:
        hashtag_id: Hashtag ID (from instagram_search_hashtag)
        kind: "top" (best performing) or "recent" (most recently posted)
        max_results: Number of media items to return (max 50)
    """
    if kind not in ("top", "recent"):
        return {"status": "error", "detail": 'kind must be "top" or "recent"'}

    edge = "top_media" if kind == "top" else "recent_media"
    items = graph.get_all_pages(
        f"{hashtag_id}/{edge}",
        {
            "user_id": auth.ig_user_id,
            "fields": HASHTAG_MEDIA_FIELDS,
            "limit": min(max_results, 50),
        },
        max_items=min(max_results, 50),
    )

    media = [
        {
            "id": item.get("id"),
            "type": item.get("media_type"),
            "caption": (item.get("caption") or "")[:300],
            "permalink": item.get("permalink"),
            "timestamp": item.get("timestamp"),
            "likes": item.get("like_count"),
            "comments": item.get("comments_count"),
        }
        for item in items
    ]
    return {"hashtag_id": hashtag_id, "kind": kind, "media": media, "total": len(media)}
