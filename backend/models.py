"""Pydantic models for the verification API."""

from typing import Optional

from pydantic import BaseModel, Field


VERDICTS = ("True", "Mostly True", "Misleading", "False", "Unverifiable")


class VerifyRequest(BaseModel):
    """Raw user input to verify — accepts free-form text, a URL, or both."""

    text: str = Field(default="", description="The raw user input containing claims to verify")
    url: Optional[str] = Field(default=None, description="URL to fetch and extract claims from")


class ClaimVerification(BaseModel):
    """Result of verifying a single claim."""

    claim: str = Field(..., description="The claim that was verified")
    verdict: str = Field(..., description="One of: True, Mostly True, Misleading, False, Unverifiable")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score 0-100")
    explanation: str = Field(..., description="Brief explanation of the verdict")
    sources: list[str] = Field(default_factory=list, description="Citation URLs from verification")


class VerifyResponse(BaseModel):
    """Response containing all claim verifications."""

    claims: list[ClaimVerification] = Field(
        default_factory=list,
        description="List of verified claims with verdicts and citations",
    )
