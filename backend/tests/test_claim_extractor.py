"""Tests for claim_extractor with mocked Perplexity API responses."""

import json

import httpx
import pytest
import respx

from claim_extractor import extract_claims, PERPLEXITY_URL


def _sonar_response(claims: list[str]) -> httpx.Response:
    """Build a mock Sonar API response containing the given claims."""
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"claims": claims}),
                    }
                }
            ]
        },
    )


class TestExtractClaims:
    @pytest.mark.asyncio
    async def test_empty_text_returns_empty(self):
        result = await extract_claims("")
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_empty(self):
        result = await extract_claims("   \n\t  ")
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        with pytest.raises(ValueError, match="PERPLEXITY_API_KEY"):
            await extract_claims("MSG causes headaches")

    @pytest.mark.asyncio
    @respx.mock
    async def test_extracts_claims(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        claims = ["MSG causes headaches", "Turmeric cures cancer"]
        respx.post(PERPLEXITY_URL).mock(return_value=_sonar_response(claims))

        result = await extract_claims("Some forwarded health message")
        assert result == claims

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_empty_on_no_claims(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(return_value=_sonar_response([]))

        result = await extract_claims("Just an opinion, nothing factual")
        assert result == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_strips_whitespace_from_claims(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(
            return_value=_sonar_response(["  padded claim  "])
        )

        result = await extract_claims("text")
        assert result == ["padded claim"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_filters_non_string_claims(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        # Simulate API returning non-string items (shouldn't happen, but be safe)
        respx.post(PERPLEXITY_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": json.dumps({"claims": ["valid", 123, None, ""]})}}
                    ]
                },
            )
        )

        result = await extract_claims("text")
        assert result == ["valid"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_empty_on_empty_choices(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(
            return_value=httpx.Response(200, json={"choices": []})
        )

        result = await extract_claims("text")
        assert result == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_empty_on_malformed_json(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "not valid json"}}]},
            )
        )

        result = await extract_claims("text")
        assert result == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_propagates(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        respx.post(PERPLEXITY_URL).mock(return_value=httpx.Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            await extract_claims("text")
