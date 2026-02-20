"""Service to detect YouTube URLs and extract video transcript text."""

import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

# Recognized YouTube hostnames
_YOUTUBE_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}

# Max transcript text length (matches url_extractor.MAX_TEXT_LENGTH)
MAX_TRANSCRIPT_LENGTH = 80_000


def is_youtube_url(url: str) -> bool:
    """Return True if *url* points to a YouTube domain."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return (parsed.hostname or "") in _YOUTUBE_HOSTS


def extract_video_id(url: str) -> str | None:
    """
    Extract the YouTube video ID from a URL.

    Returns the video ID string, or None if the URL doesn't match
    any known YouTube video pattern.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    host = parsed.hostname or ""

    if host == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/")[0]
        return video_id or None

    if host in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        # /watch?v=VIDEO_ID
        if parsed.path == "/watch":
            ids = parse_qs(parsed.query).get("v")
            return ids[0] if ids else None

        # /shorts/VIDEO_ID or /embed/VIDEO_ID
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] in ("shorts", "embed"):
            return parts[1]

    return None


def fetch_youtube_transcript(video_id: str) -> str:
    """
    Fetch the transcript for a YouTube video and return it as plain text.

    Tries English first, then falls back to any available language.
    Raises ValueError if no transcript is available.
    """
    api = YouTubeTranscriptApi()

    try:
        transcript = api.fetch(video_id, languages=["en"])
    except NoTranscriptFound:
        try:
            transcript_list = api.list(video_id)
            first = next(iter(transcript_list))
            transcript = first.fetch()
        except (StopIteration, CouldNotRetrieveTranscript) as exc:
            raise ValueError(
                f"No transcript available for YouTube video {video_id}"
            ) from exc
    except (TranscriptsDisabled, VideoUnavailable) as exc:
        raise ValueError(
            f"Cannot access transcript for YouTube video {video_id}: {exc}"
        ) from exc
    except CouldNotRetrieveTranscript as exc:
        raise ValueError(
            f"Failed to retrieve transcript for YouTube video {video_id}: {exc}"
        ) from exc

    text_parts = [snippet.text for snippet in transcript.snippets]
    text = " ".join(text_parts)
    text = re.sub(r"\s{2,}", " ", text).strip()

    if not text:
        raise ValueError(f"Transcript for YouTube video {video_id} is empty")

    return text[:MAX_TRANSCRIPT_LENGTH]
