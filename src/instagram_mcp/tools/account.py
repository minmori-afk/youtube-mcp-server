"""Account tools — profile info, account insights, and audience demographics."""

from instagram_mcp.server import auth, graph, mcp

PROFILE_FIELDS = (
    "id,username,name,biography,website,followers_count,follows_count,"
    "media_count,profile_picture_url"
)


@mcp.tool()
def instagram_get_account() -> dict:
    """Get profile info for the connected Instagram account.

    Returns username, bio, website, follower/following counts, and media count.
    """
    return graph.get(auth.ig_user_id, {"fields": PROFILE_FIELDS})


@mcp.tool()
def instagram_get_account_insights(
    metrics: str = "reach,follower_count,profile_views",
    period: str = "day",
    since: str | None = None,
    until: str | None = None,
) -> dict:
    """Get account-level insights (reach, follower growth, profile views, etc).

    Args:
        metrics: Comma-separated metric names, e.g. "reach,follower_count,
            profile_views,accounts_engaged,views"
        period: Aggregation period: "day", "week", or "days_28"
        since: Start date (YYYY-MM-DD or unix timestamp), optional
        until: End date (YYYY-MM-DD or unix timestamp), optional
    """
    params = {
        "metric": metrics,
        "period": period,
        "since": since,
        "until": until,
    }
    # Newer interaction metrics require metric_type=total_value
    total_value_metrics = {
        "accounts_engaged", "total_interactions", "likes", "comments",
        "shares", "saves", "replies", "profile_links_taps", "views",
    }
    requested = {m.strip() for m in metrics.split(",")}
    if requested & total_value_metrics:
        params["metric_type"] = "total_value"

    data = graph.get(f"{auth.ig_user_id}/insights", params)

    results = []
    for metric in data.get("data", []):
        entry = {
            "name": metric.get("name"),
            "period": metric.get("period"),
            "title": metric.get("title"),
        }
        if "values" in metric:
            entry["values"] = metric["values"]
        if "total_value" in metric:
            entry["total_value"] = metric["total_value"].get("value")
        results.append(entry)
    return {"metrics": results}


@mcp.tool()
def instagram_get_audience_demographics(
    breakdown: str = "country",
    timeframe: str = "this_month",
) -> dict:
    """Get follower demographics for the connected account.

    Requires at least 100 followers.

    Args:
        breakdown: Dimension to break down by: "country", "city", "age", or "gender"
        timeframe: "this_month" or "this_week"
    """
    data = graph.get(
        f"{auth.ig_user_id}/insights",
        {
            "metric": "follower_demographics",
            "period": "lifetime",
            "timeframe": timeframe,
            "breakdown": breakdown,
            "metric_type": "total_value",
        },
    )

    breakdowns = []
    for metric in data.get("data", []):
        for bd in metric.get("total_value", {}).get("breakdowns", []):
            for result in bd.get("results", []):
                breakdowns.append({
                    "dimension": result.get("dimension_values"),
                    "followers": result.get("value"),
                })
    breakdowns.sort(key=lambda r: r.get("followers") or 0, reverse=True)
    return {"breakdown": breakdown, "timeframe": timeframe, "results": breakdowns}
