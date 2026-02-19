"""FastAPI application for claim verification."""

import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from claim_extractor import extract_claims
from claim_verifier import verify_claims
from models import ClaimVerification, VerifyRequest, VerifyResponse
from url_extractor import extract_text_from_url

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
    Extract claims from raw text or a URL, verify each against real sources,
    return results.
    """
    if not os.getenv("PERPLEXITY_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="PERPLEXITY_API_KEY is not configured",
        )

    # Resolve input text — fetch from URL if one was provided
    text = (request.text or "").strip()
    if request.url:
        try:
            url_text = await extract_text_from_url(request.url)
            # Append URL content after any user-provided text
            text = f"{text}\n\n{url_text}".strip() if text else url_text
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch URL (HTTP {e.response.status_code})",
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch URL: {e!s}",
            )

    if not text:
        raise HTTPException(status_code=422, detail="Provide text or a URL to verify")

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
