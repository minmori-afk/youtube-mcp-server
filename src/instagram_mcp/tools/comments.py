"""Comment tools — list, post, reply to, hide, and delete comments."""

from instagram_mcp.server import graph, mcp

COMMENT_FIELDS = (
    "id,text,username,timestamp,like_count,hidden,"
    "replies{id,text,username,timestamp,like_count}"
)


@mcp.tool()
def instagram_list_comments(media_id: str, max_results: int = 25) -> dict:
    """List comments on a post or reel, including replies.

    Args:
        media_id: Instagram media ID (from instagram_list_media)
        max_results: Number of top-level comments to return (max 100)
    """
    items = graph.get_all_pages(
        f"{media_id}/comments",
        {"fields": COMMENT_FIELDS, "limit": min(max_results, 100)},
        max_items=min(max_results, 100),
    )

    comments = []
    for item in items:
        replies = [
            {
                "comment_id": r.get("id"),
                "author": r.get("username"),
                "text": r.get("text"),
                "likes": r.get("like_count", 0),
                "timestamp": r.get("timestamp"),
            }
            for r in item.get("replies", {}).get("data", [])
        ]
        comments.append({
            "comment_id": item.get("id"),
            "author": item.get("username"),
            "text": item.get("text"),
            "likes": item.get("like_count", 0),
            "timestamp": item.get("timestamp"),
            "hidden": item.get("hidden", False),
            "replies": replies,
        })

    return {"media_id": media_id, "comments": comments, "total": len(comments)}


@mcp.tool()
def instagram_post_comment(media_id: str, text: str) -> dict:
    """Post a new top-level comment on a post or reel.

    Args:
        media_id: Instagram media ID to comment on
        text: Comment text
    """
    response = graph.post(f"{media_id}/comments", {"message": text})
    return {"comment_id": response.get("id"), "media_id": media_id, "posted": True}


@mcp.tool()
def instagram_reply_to_comment(comment_id: str, text: str) -> dict:
    """Reply to an existing comment.

    Args:
        comment_id: The comment ID to reply to (from instagram_list_comments)
        text: Reply text
    """
    response = graph.post(f"{comment_id}/replies", {"message": text})
    return {"reply_id": response.get("id"), "parent_id": comment_id, "posted": True}


@mcp.tool()
def instagram_hide_comment(comment_id: str, hide: bool = True) -> dict:
    """Hide or unhide a comment.

    Args:
        comment_id: The comment ID to hide
        hide: True to hide, False to unhide
    """
    graph.post(comment_id, {"hide": "true" if hide else "false"})
    return {"comment_id": comment_id, "hidden": hide}


@mcp.tool()
def instagram_delete_comment(comment_id: str) -> dict:
    """Permanently delete a comment.

    Args:
        comment_id: The comment ID to delete
    """
    graph.delete(comment_id)
    return {"comment_id": comment_id, "deleted": True}
