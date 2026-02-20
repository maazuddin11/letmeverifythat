"""FastAPI application for claim verification."""

import asyncio
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from claim_extractor import extract_claims
from claim_verifier import verify_claims
from models import ClaimVerification, VerifyRequest, VerifyResponse
from url_extractor import extract_urls, fetch_url_text
from youtube_extractor import extract_video_id, fetch_youtube_transcript, is_youtube_url

# Load .env from project root then backend/ so keys are found when run from backend/
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

app = FastAPI(title="LetMeVerifyThat", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


@app.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest) -> VerifyResponse:
    """
    Accept free-form text (which may contain URLs), fetch any URLs found,
    combine everything, extract claims, verify, and return results.
    """
    if not os.getenv("PERPLEXITY_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="PERPLEXITY_API_KEY is not configured",
        )

    raw = (request.text or "").strip()
    if not raw:
        raise HTTPException(status_code=422, detail="Provide some text to verify")

    # Pull URLs out of the input and keep the remaining prose
    urls, remaining_text = extract_urls(raw)

    # Fetch all URLs in parallel, routing YouTube URLs to the transcript API
    url_texts: list[str] = []
    if urls:

        async def _fetch_one(url: str) -> str:
            if is_youtube_url(url):
                video_id = extract_video_id(url)
                if video_id:
                    try:
                        return await asyncio.to_thread(
                            fetch_youtube_transcript, video_id
                        )
                    except ValueError:
                        pass  # fall through to generic HTML fetch
            return await fetch_url_text(url)

        fetch_results = await asyncio.gather(
            *(_fetch_one(u) for u in urls),
            return_exceptions=True,
        )
        for url, result in zip(urls, fetch_results):
            if isinstance(result, Exception):
                # Skip URLs we can't fetch — still verify the rest
                continue
            url_texts.append(result)

    # Combine: remaining user text + fetched page content
    parts = [p for p in [remaining_text, *url_texts] if p.strip()]
    text = "\n\n".join(parts).strip()

    if not text:
        raise HTTPException(
            status_code=422,
            detail="Could not extract any content from the provided input",
        )

    try:
        claims = await extract_claims(text)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Claim extraction failed: {e!s}",
        )
    if not claims:
        return VerifyResponse(claims=[])
    try:
        results: list[ClaimVerification] = await verify_claims(claims)
        return VerifyResponse(claims=results)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Claim verification failed: {e!s}",
        )
