"""FastAPI application for claim verification."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from claim_extractor import extract_claims
from claim_verifier import verify_claims
from models import ClaimVerification, VerifyRequest, VerifyResponse

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
    Extract claims from raw text, verify each against real sources, return results.
    """
    if not os.getenv("PERPLEXITY_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="PERPLEXITY_API_KEY is not configured",
        )
    try:
        claims = await extract_claims(request.text)
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
