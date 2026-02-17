"""Service to extract verifiable claims from raw text using Perplexity Sonar API."""

import json
import os
from typing import Any

import httpx

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
EXTRACTOR_MODEL = "sonar"

EXTRACT_CLAIMS_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "extracted_claims",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "claims": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of distinct factual, verifiable claims",
                }
            },
            "required": ["claims"],
            "additionalProperties": False,
        },
    },
}

SYSTEM_PROMPT = """You extract factual, verifiable claims from user-provided text.
- Output ONLY claims that can be fact-checked against external sources (scientific, medical, historical, etc.).
- Skip: opinions, questions, vague statements, jokes, or non-factual content.
- Each claim should be a single, clear sentence.
- Deduplicate: if the same claim is stated in different words, output it once.
- If there are no verifiable claims, return an empty list: {"claims": []}."""


async def extract_claims(text: str) -> list[str]:
    """
    Extract distinct verifiable claims from raw text using Sonar API.
    Returns an empty list if the text contains no verifiable claims or on API failure.
    """
    text = (text or "").strip()
    if not text:
        return []

    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is not set")

    payload: dict[str, Any] = {
        "model": EXTRACTOR_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract verifiable claims from this text:\n\n{text}"},
        ],
        "max_tokens": 1024,
        "response_format": EXTRACT_CLAIMS_SCHEMA,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            PERPLEXITY_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        return []
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        return []

    try:
        parsed = json.loads(content)
        claims = parsed.get("claims") or []
        return [c.strip() for c in claims if isinstance(c, str) and c.strip()]
    except (json.JSONDecodeError, TypeError):
        return []
