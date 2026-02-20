"""Tests for claim_verifier with mocked Perplexity API responses."""

import json

import httpx
import pytest
import respx

from claim_verifier import verify_one_claim, verify_claims, PERPLEXITY_URL


def _verification_response(
    verdict: str = "True",
    confidence: int = 85,
    explanation: str = "Well-supported by evidence.",
    citations: list[str] | None = None,
) -> httpx.Response:
    """Build a mock Sonar Pro verification response."""
    return httpx.Response(
        200,
        json={
            "citations": citations or ["https://pubmed.ncbi.nlm.nih.gov/12345"],
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "verdict": verdict,
                                "confidence": confidence,
                                "explanation": explanation,
                            }
                        ),
                    }
                }
            ],
        },
    )


class TestVerifyOneClaim:
    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        with pytest.raises(ValueError, match="PERPLEXITY_API_KEY"):
            await verify_one_claim("Test claim")

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_verification(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(
            return_value=_verification_response(
                verdict="False",
                confidence=90,
                explanation="No scientific evidence supports this.",
                citations=["https://pubmed.ncbi.nlm.nih.gov/99999"],
            )
        )

        result = await verify_one_claim("Turmeric cures cancer")
        assert result.claim == "Turmeric cures cancer"
        assert result.verdict == "False"
        assert result.confidence == 90
        assert "No scientific evidence" in result.explanation
        assert "https://pubmed.ncbi.nlm.nih.gov/99999" in result.sources

    @pytest.mark.asyncio
    @respx.mock
    async def test_invalid_verdict_becomes_unverifiable(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(
            return_value=_verification_response(verdict="Maybe")
        )

        result = await verify_one_claim("Some claim")
        assert result.verdict == "Unverifiable"

    @pytest.mark.asyncio
    @respx.mock
    async def test_confidence_clamped_to_range(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(
            return_value=_verification_response(confidence=150)
        )

        result = await verify_one_claim("Some claim")
        assert result.confidence == 100

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_choices_returns_unverifiable(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(
            return_value=httpx.Response(200, json={"choices": [], "citations": []})
        )

        result = await verify_one_claim("Some claim")
        assert result.verdict == "Unverifiable"
        assert result.confidence == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_malformed_json_returns_unverifiable(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "citations": [],
                    "choices": [{"message": {"content": "not json"}}],
                },
            )
        )

        result = await verify_one_claim("Some claim")
        assert result.verdict == "Unverifiable"
        assert "Could not parse" in result.explanation


class TestVerifyClaims:
    @pytest.mark.asyncio
    async def test_empty_list(self):
        result = await verify_claims([])
        assert result == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_multiple_claims_verified_concurrently(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(
            return_value=_verification_response()
        )

        results = await verify_claims(["Claim A", "Claim B"])
        assert len(results) == 2
        assert results[0].claim == "Claim A"
        assert results[1].claim == "Claim B"

    @pytest.mark.asyncio
    @respx.mock
    async def test_individual_failure_still_returns_result(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        # First call succeeds, second fails
        route = respx.post(PERPLEXITY_URL)
        route.side_effect = [
            _verification_response(),
            httpx.Response(500),
        ]

        results = await verify_claims(["Good claim", "Bad claim"])
        assert len(results) == 2
        assert results[0].verdict == "True"
        assert results[1].verdict == "Unverifiable"
        assert "Verification failed" in results[1].explanation
