"""Tests for youtube_extractor: YouTube URL detection, video ID extraction, and transcript fetching."""

import pytest
from unittest.mock import MagicMock, patch

from youtube_extractor import (
    is_youtube_url,
    extract_video_id,
    fetch_youtube_transcript,
    MAX_TRANSCRIPT_LENGTH,
)


# ---------------------------------------------------------------------------
# is_youtube_url
# ---------------------------------------------------------------------------

class TestIsYoutubeUrl:
    def test_standard_watch_url(self):
        assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_short_url(self):
        assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_shorts_url(self):
        assert is_youtube_url("https://www.youtube.com/shorts/dQw4w9WgXcQ") is True

    def test_mobile_url(self):
        assert is_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_no_www(self):
        assert is_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_embed_url(self):
        assert is_youtube_url("https://www.youtube.com/embed/dQw4w9WgXcQ") is True

    def test_non_youtube_url(self):
        assert is_youtube_url("https://example.com/article") is False

    def test_similar_domain_not_matched(self):
        assert is_youtube_url("https://notyoutube.com/watch?v=abc") is False

    def test_empty_string(self):
        assert is_youtube_url("") is False

    def test_not_a_url(self):
        assert is_youtube_url("just some text") is False


# ---------------------------------------------------------------------------
# extract_video_id
# ---------------------------------------------------------------------------

class TestExtractVideoId:
    def test_standard_watch_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_watch_url_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42&list=PLxyz"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url_with_timestamp(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=30") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_mobile_url(self):
        assert extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_no_www(self):
        assert extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_watch_url_missing_v_param(self):
        assert extract_video_id("https://www.youtube.com/watch?list=PLxyz") is None

    def test_channel_url_returns_none(self):
        assert extract_video_id("https://www.youtube.com/channel/UCxyz") is None

    def test_playlist_url_returns_none(self):
        assert extract_video_id("https://www.youtube.com/playlist?list=PLxyz") is None

    def test_non_youtube_url_returns_none(self):
        assert extract_video_id("https://example.com/page") is None

    def test_empty_string_returns_none(self):
        assert extract_video_id("") is None

    def test_youtu_be_empty_path(self):
        assert extract_video_id("https://youtu.be/") is None


# ---------------------------------------------------------------------------
# fetch_youtube_transcript
# ---------------------------------------------------------------------------

class TestFetchYoutubeTranscript:
    @patch("youtube_extractor.YouTubeTranscriptApi")
    def test_successful_english_transcript(self, MockApi):
        snippet1 = MagicMock()
        snippet1.text = "Hello everyone"
        snippet2 = MagicMock()
        snippet2.text = "today we discuss vaccines"

        mock_transcript = MagicMock()
        mock_transcript.snippets = [snippet1, snippet2]

        MockApi.return_value.fetch.return_value = mock_transcript

        result = fetch_youtube_transcript("abc123")
        assert "Hello everyone" in result
        assert "today we discuss vaccines" in result
        MockApi.return_value.fetch.assert_called_once_with("abc123", languages=["en"])

    @patch("youtube_extractor.YouTubeTranscriptApi")
    def test_transcript_text_joined_with_spaces(self, MockApi):
        snippet1 = MagicMock()
        snippet1.text = "Part one."
        snippet2 = MagicMock()
        snippet2.text = "Part two."

        mock_transcript = MagicMock()
        mock_transcript.snippets = [snippet1, snippet2]
        MockApi.return_value.fetch.return_value = mock_transcript

        result = fetch_youtube_transcript("vid123")
        assert result == "Part one. Part two."

    @patch("youtube_extractor.YouTubeTranscriptApi")
    def test_transcripts_disabled_raises_valueerror(self, MockApi):
        from youtube_transcript_api._errors import TranscriptsDisabled
        MockApi.return_value.fetch.side_effect = TranscriptsDisabled("vid123")

        with pytest.raises(ValueError, match="Cannot access transcript"):
            fetch_youtube_transcript("vid123")

    @patch("youtube_extractor.YouTubeTranscriptApi")
    def test_video_unavailable_raises_valueerror(self, MockApi):
        from youtube_transcript_api._errors import VideoUnavailable
        MockApi.return_value.fetch.side_effect = VideoUnavailable("vid123")

        with pytest.raises(ValueError, match="Cannot access transcript"):
            fetch_youtube_transcript("vid123")

    @patch("youtube_extractor.YouTubeTranscriptApi")
    def test_fallback_to_non_english_transcript(self, MockApi):
        from youtube_transcript_api._errors import NoTranscriptFound

        MockApi.return_value.fetch.side_effect = NoTranscriptFound(
            "vid123", ["en"], {}
        )

        snippet = MagicMock()
        snippet.text = "Hola a todos"
        mock_fetched = MagicMock()
        mock_fetched.snippets = [snippet]

        mock_entry = MagicMock()
        mock_entry.fetch.return_value = mock_fetched
        mock_list = MagicMock()
        mock_list.__iter__ = MagicMock(return_value=iter([mock_entry]))
        MockApi.return_value.list.return_value = mock_list

        result = fetch_youtube_transcript("vid123")
        assert "Hola a todos" in result

    @patch("youtube_extractor.YouTubeTranscriptApi")
    def test_empty_transcript_raises_valueerror(self, MockApi):
        mock_transcript = MagicMock()
        mock_transcript.snippets = []
        MockApi.return_value.fetch.return_value = mock_transcript

        with pytest.raises(ValueError, match="empty"):
            fetch_youtube_transcript("vid123")

    @patch("youtube_extractor.YouTubeTranscriptApi")
    def test_transcript_truncated_at_max_length(self, MockApi):
        snippet = MagicMock()
        snippet.text = "x" * 100_000

        mock_transcript = MagicMock()
        mock_transcript.snippets = [snippet]
        MockApi.return_value.fetch.return_value = mock_transcript

        result = fetch_youtube_transcript("vid123")
        assert len(result) <= MAX_TRANSCRIPT_LENGTH
