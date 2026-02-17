"""Service to verify claims against real sources using Perplexity Sonar Pro API."""

import json
import os
from typing import Any

import httpx

from models import ClaimVerification, VERDICTS

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
VERIFIER_MODEL = "sonar-pro"

SEARCH_DOMAIN_FILTER = [
    "pubmed.ncbi.nlm.nih.gov",
    "who.int",
    "cdc.gov",
    "nih.gov",
    "mayoclinic.org",
    "wikipedia.org",
]

VERIFY_CLAIM_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "verification_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {
                    "type": "string",
                    "enum": list(VERDICTS),
                    "description": "Fact-check verdict",
                },
                "confidence": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Confidence score 0-100",
                },
                "explanation": {
                    "type": "string",
                    "description": "Brief explanation of the verdict",
                },
            },
            "required": ["verdict", "confidence", "explanation"],
            "additionalProperties": False,
        },
    },
}

SYSTEM_PROMPT = """You are a fact-checker. Given a claim, determine its veracity using web search.
- Verdict must be exactly one of: True, Mostly True, Misleading, False, Unverifiable.
- Confidence: 0-100. Be conservative; only high confidence when evidence is strong.
- Explanation: 1-3 sentences citing what reputable sources say. Do not invent URLs."""


async def verify_one_claim(claim: str) -> ClaimVerification:
    """
    Verify a single claim using Sonar Pro. Uses top-level API citations for sources.
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is not set")

    payload: dict[str, Any] = {
        "model": VERIFIER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Fact-check this claim: {claim}"},
        ],
        "max_tokens": 512,
        "response_format": VERIFY_CLAIM_SCHEMA,
        "search_domain_filter": SEARCH_DOMAIN_FILTER,
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
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

    # Citations from top-level API response (not from model text)
    citations: list[str] = data.get("citations") or []
    sources = [c for c in citations if isinstance(c, str) and c.strip()]

    choices = data.get("choices") or []
    if not choices:
        return ClaimVerification(
            claim=claim,
            verdict="Unverifiable",
            confidence=0,
            explanation="No response from verification service.",
            sources=sources,
        )
    message = choices[0].get("message") or {}
    content = message.get("content") or ""

    try:
        parsed = json.loads(content)
        verdict = parsed.get("verdict") or "Unverifiable"
        if verdict not in VERDICTS:
            verdict = "Unverifiable"
        confidence = int(parsed.get("confidence", 0))
        confidence = max(0, min(100, confidence))
        explanation = (parsed.get("explanation") or "").strip() or "No explanation provided."
        return ClaimVerification(
            claim=claim,
            verdict=verdict,
            confidence=confidence,
            explanation=explanation,
            sources=sources,
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return ClaimVerification(
            claim=claim,
            verdict="Unverifiable",
            confidence=0,
            explanation="Could not parse verification result.",
            sources=sources,
        )


async def verify_claims(claims: list[str]) -> list[ClaimVerification]:
    """
    Verify all claims concurrently using asyncio.gather.
    """
    import asyncio

    if not claims:
        return []
    results = await asyncio.gather(
        *[verify_one_claim(c) for c in claims],
        return_exceptions=True,
    )
    out: list[ClaimVerification] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            out.append(
                ClaimVerification(
                    claim=claims[i],
                    verdict="Unverifiable",
                    confidence=0,
                    explanation=f"Verification failed: {r!s}",
                    sources=[],
                )
            )
        else:
            out.append(r)
    return out
