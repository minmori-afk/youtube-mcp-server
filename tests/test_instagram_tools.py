"""Tests for Instagram tools with mocked Graph API."""

from unittest.mock import patch


class TestAccount:
    @patch("instagram_mcp.tools.account.auth")
    @patch("instagram_mcp.tools.account.graph")
    def test_get_account(self, mock_graph, mock_auth):
        from instagram_mcp.tools.account import instagram_get_account

        mock_auth.ig_user_id = "17890000"
        mock_graph.get.return_value = {
            "id": "17890000",
            "username": "mybrand",
            "followers_count": 1234,
        }

        result = instagram_get_account()
        assert result["username"] == "mybrand"
        path, params = mock_graph.get.call_args[0]
        assert path == "17890000"
        assert "followers_count" in params["fields"]

    @patch("instagram_mcp.tools.account.auth")
    @patch("instagram_mcp.tools.account.graph")
    def test_account_insights(self, mock_graph, mock_auth):
        from instagram_mcp.tools.account import instagram_get_account_insights

        mock_auth.ig_user_id = "17890000"
        mock_graph.get.return_value = {
            "data": [{
                "name": "reach",
                "period": "day",
                "title": "Reach",
                "values": [{"value": 500, "end_time": "2026-09-01T07:00:00+0000"}],
            }]
        }

        result = instagram_get_account_insights(metrics="reach")
        assert result["metrics"][0]["name"] == "reach"
        assert result["metrics"][0]["values"][0]["value"] == 500
        _, params = mock_graph.get.call_args[0]
        assert "metric_type" not in params

    @patch("instagram_mcp.tools.account.auth")
    @patch("instagram_mcp.tools.account.graph")
    def test_account_insights_total_value_metrics(self, mock_graph, mock_auth):
        from instagram_mcp.tools.account import instagram_get_account_insights

        mock_auth.ig_user_id = "17890000"
        mock_graph.get.return_value = {
            "data": [{"name": "views", "period": "day", "total_value": {"value": 900}}]
        }

        result = instagram_get_account_insights(metrics="views")
        assert result["metrics"][0]["total_value"] == 900
        _, params = mock_graph.get.call_args[0]
        assert params["metric_type"] == "total_value"

    @patch("instagram_mcp.tools.account.auth")
    @patch("instagram_mcp.tools.account.graph")
    def test_demographics_sorted(self, mock_graph, mock_auth):
        from instagram_mcp.tools.account import instagram_get_audience_demographics

        mock_auth.ig_user_id = "17890000"
        mock_graph.get.return_value = {
            "data": [{
                "total_value": {
                    "breakdowns": [{
                        "results": [
                            {"dimension_values": ["US"], "value": 10},
                            {"dimension_values": ["JP"], "value": 90},
                        ]
                    }]
                }
            }]
        }

        result = instagram_get_audience_demographics(breakdown="country")
        assert result["results"][0] == {"dimension": ["JP"], "followers": 90}


class TestMedia:
    @patch("instagram_mcp.tools.media.auth")
    @patch("instagram_mcp.tools.media.graph")
    def test_list_media(self, mock_graph, mock_auth):
        from instagram_mcp.tools.media import instagram_list_media

        mock_auth.ig_user_id = "17890000"
        mock_graph.get_all_pages.return_value = [{
            "id": "m1",
            "media_type": "IMAGE",
            "caption": "Hello",
            "like_count": 10,
            "comments_count": 2,
        }]

        result = instagram_list_media(max_results=5)
        assert result["total"] == 1
        assert result["media"][0]["likes"] == 10

    @patch("instagram_mcp.tools.media.graph")
    def test_media_insights(self, mock_graph):
        from instagram_mcp.tools.media import instagram_get_media_insights

        mock_graph.get.return_value = {
            "data": [
                {"name": "reach", "values": [{"value": 300}]},
                {"name": "saved", "values": [{"value": 12}]},
            ]
        }

        result = instagram_get_media_insights("m1")
        assert result["insights"] == {"reach": 300, "saved": 12}


class TestPublishing:
    @patch("instagram_mcp.tools.publishing.auth")
    @patch("instagram_mcp.tools.publishing.graph")
    def test_publish_photo(self, mock_graph, mock_auth):
        from instagram_mcp.tools.publishing import instagram_publish_photo

        mock_auth.ig_user_id = "17890000"
        mock_graph.post.side_effect = [{"id": "container1"}, {"id": "media1"}]
        mock_graph.get.return_value = {"id": "media1", "permalink": "https://instagr.am/p/x"}

        result = instagram_publish_photo("https://example.com/a.jpg", "caption")
        assert result["published"] is True
        assert result["media_id"] == "media1"
        create_path, create_params = mock_graph.post.call_args_list[0][0]
        assert create_path == "17890000/media"
        assert create_params["image_url"] == "https://example.com/a.jpg"

    @patch("instagram_mcp.tools.publishing.time.sleep")
    @patch("instagram_mcp.tools.publishing.auth")
    @patch("instagram_mcp.tools.publishing.graph")
    def test_publish_reel_waits_for_processing(self, mock_graph, mock_auth, mock_sleep):
        from instagram_mcp.tools.publishing import instagram_publish_reel

        mock_auth.ig_user_id = "17890000"
        mock_graph.post.side_effect = [{"id": "container1"}, {"id": "media2"}]
        mock_graph.get.side_effect = [
            {"status_code": "IN_PROGRESS"},
            {"status_code": "FINISHED"},
            {"id": "media2", "permalink": "https://instagr.am/reel/y"},
        ]

        result = instagram_publish_reel("https://example.com/v.mp4", "reel caption")
        assert result["published"] is True
        mock_sleep.assert_called_once()

    @patch("instagram_mcp.tools.publishing.auth")
    @patch("instagram_mcp.tools.publishing.graph")
    def test_publish_carousel_validates_count(self, mock_graph, mock_auth):
        from instagram_mcp.tools.publishing import instagram_publish_carousel

        result = instagram_publish_carousel(["https://example.com/only-one.jpg"])
        assert result["status"] == "error"
        mock_graph.post.assert_not_called()

    @patch("instagram_mcp.tools.publishing.auth")
    @patch("instagram_mcp.tools.publishing.graph")
    def test_publish_carousel(self, mock_graph, mock_auth):
        from instagram_mcp.tools.publishing import instagram_publish_carousel

        mock_auth.ig_user_id = "17890000"
        mock_graph.post.side_effect = [
            {"id": "child1"},
            {"id": "child2"},
            {"id": "carousel1"},
            {"id": "media3"},
        ]
        mock_graph.get.return_value = {"id": "media3", "permalink": "https://instagr.am/p/z"}

        result = instagram_publish_carousel(
            ["https://example.com/1.jpg", "https://example.com/2.jpg"], "carousel"
        )
        assert result["published"] is True
        _, carousel_params = mock_graph.post.call_args_list[2][0]
        assert carousel_params["children"] == "child1,child2"

    @patch("instagram_mcp.tools.publishing.auth")
    @patch("instagram_mcp.tools.publishing.graph")
    def test_publish_story_requires_one_url(self, mock_graph, mock_auth):
        from instagram_mcp.tools.publishing import instagram_publish_story

        assert instagram_publish_story()["status"] == "error"
        assert instagram_publish_story("https://a.jpg", "https://b.mp4")["status"] == "error"
        mock_graph.post.assert_not_called()


class TestComments:
    @patch("instagram_mcp.tools.comments.graph")
    def test_list_comments(self, mock_graph):
        from instagram_mcp.tools.comments import instagram_list_comments

        mock_graph.get_all_pages.return_value = [{
            "id": "c1",
            "username": "fan1",
            "text": "Nice post!",
            "like_count": 3,
            "replies": {"data": [{"id": "r1", "username": "mybrand", "text": "Thanks!"}]},
        }]

        result = instagram_list_comments("m1")
        assert result["total"] == 1
        assert result["comments"][0]["text"] == "Nice post!"
        assert result["comments"][0]["replies"][0]["text"] == "Thanks!"

    @patch("instagram_mcp.tools.comments.graph")
    def test_reply(self, mock_graph):
        from instagram_mcp.tools.comments import instagram_reply_to_comment

        mock_graph.post.return_value = {"id": "r2"}
        result = instagram_reply_to_comment("c1", "Thanks!")
        assert result["posted"] is True
        assert result["parent_id"] == "c1"
        mock_graph.post.assert_called_once_with("c1/replies", {"message": "Thanks!"})

    @patch("instagram_mcp.tools.comments.graph")
    def test_hide(self, mock_graph):
        from instagram_mcp.tools.comments import instagram_hide_comment

        result = instagram_hide_comment("c1")
        assert result["hidden"] is True
        mock_graph.post.assert_called_once_with("c1", {"hide": "true"})

    @patch("instagram_mcp.tools.comments.graph")
    def test_delete(self, mock_graph):
        from instagram_mcp.tools.comments import instagram_delete_comment

        result = instagram_delete_comment("c1")
        assert result["deleted"] is True
        mock_graph.delete.assert_called_once_with("c1")


class TestHashtags:
    @patch("instagram_mcp.tools.hashtags.auth")
    @patch("instagram_mcp.tools.hashtags.graph")
    def test_search_strips_hash(self, mock_graph, mock_auth):
        from instagram_mcp.tools.hashtags import instagram_search_hashtag

        mock_auth.ig_user_id = "17890000"
        mock_graph.get.return_value = {"data": [{"id": "hash1"}]}

        result = instagram_search_hashtag("#travel")
        assert result["hashtag_id"] == "hash1"
        _, params = mock_graph.get.call_args[0]
        assert params["q"] == "travel"

    @patch("instagram_mcp.tools.hashtags.auth")
    @patch("instagram_mcp.tools.hashtags.graph")
    def test_hashtag_media_kind_validated(self, mock_graph, mock_auth):
        from instagram_mcp.tools.hashtags import instagram_get_hashtag_media

        result = instagram_get_hashtag_media("hash1", kind="weird")
        assert result["status"] == "error"
        mock_graph.get_all_pages.assert_not_called()

    @patch("instagram_mcp.tools.hashtags.auth")
    @patch("instagram_mcp.tools.hashtags.graph")
    def test_hashtag_media(self, mock_graph, mock_auth):
        from instagram_mcp.tools.hashtags import instagram_get_hashtag_media

        mock_auth.ig_user_id = "17890000"
        mock_graph.get_all_pages.return_value = [
            {"id": "p1", "media_type": "IMAGE", "like_count": 42}
        ]

        result = instagram_get_hashtag_media("hash1", kind="recent")
        assert result["media"][0]["likes"] == 42
        path = mock_graph.get_all_pages.call_args[0][0]
        assert path == "hash1/recent_media"
