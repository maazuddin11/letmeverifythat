"""Integration tests for the FastAPI /verify and /health endpoints."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestVerifyEndpoint:
    def test_empty_text_returns_422(self, client, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        resp = client.post("/verify", json={"text": ""})
        assert resp.status_code == 422

    def test_missing_text_field_returns_422(self, client):
        resp = client.post("/verify", json={})
        assert resp.status_code == 422

    def test_missing_api_key_returns_503(self, client, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        resp = client.post("/verify", json={"text": "some claim"})
        assert resp.status_code == 503
        assert "PERPLEXITY_API_KEY" in resp.json()["detail"]

    @patch("main.extract_claims", new_callable=AsyncMock)
    def test_no_claims_returns_empty(self, mock_extract, client, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        mock_extract.return_value = []

        resp = client.post("/verify", json={"text": "just an opinion"})
        assert resp.status_code == 200
        assert resp.json() == {"claims": []}

    @patch("main.verify_claims", new_callable=AsyncMock)
    @patch("main.extract_claims", new_callable=AsyncMock)
    def test_full_flow(self, mock_extract, mock_verify, client, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        mock_extract.return_value = ["MSG causes headaches"]
        mock_verify.return_value = [
            {
                "claim": "MSG causes headaches",
                "verdict": "Misleading",
                "confidence": 70,
                "explanation": "Limited evidence supports this claim.",
                "sources": ["https://pubmed.ncbi.nlm.nih.gov/12345"],
            }
        ]

        resp = client.post("/verify", json={"text": "MSG causes headaches"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["claims"]) == 1
        assert data["claims"][0]["verdict"] == "Misleading"

    @patch("main.fetch_url_text", new_callable=AsyncMock)
    @patch("main.verify_claims", new_callable=AsyncMock)
    @patch("main.extract_claims", new_callable=AsyncMock)
    def test_text_with_url_fetches_and_combines(
        self, mock_extract, mock_verify, mock_fetch, client, monkeypatch
    ):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        mock_fetch.return_value = "Article says turmeric is not a cure."
        mock_extract.return_value = ["Turmeric is not a cancer cure"]
        mock_verify.return_value = [
            {
                "claim": "Turmeric is not a cancer cure",
                "verdict": "True",
                "confidence": 95,
                "explanation": "Supported by medical research.",
                "sources": [],
            }
        ]

        resp = client.post(
            "/verify",
            json={"text": "https://example.com/article\nAlso check MSG claims"},
        )
        assert resp.status_code == 200
        # fetch_url_text should have been called with the URL
        mock_fetch.assert_called_once_with("https://example.com/article")
        # extract_claims should receive combined text
        combined = mock_extract.call_args[0][0]
        assert "Also check MSG claims" in combined
        assert "Article says turmeric is not a cure." in combined

    @patch("main.fetch_url_text", new_callable=AsyncMock)
    @patch("main.verify_claims", new_callable=AsyncMock)
    @patch("main.extract_claims", new_callable=AsyncMock)
    def test_unfetchable_url_still_processes_text(
        self, mock_extract, mock_verify, mock_fetch, client, monkeypatch
    ):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        mock_fetch.side_effect = Exception("Connection refused")
        mock_extract.return_value = ["MSG causes headaches"]
        mock_verify.return_value = [
            {
                "claim": "MSG causes headaches",
                "verdict": "Misleading",
                "confidence": 60,
                "explanation": "Limited evidence.",
                "sources": [],
            }
        ]

        resp = client.post(
            "/verify",
            json={"text": "https://dead-link.com\nMSG causes headaches"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["claims"]) == 1

    @patch("main.extract_claims", new_callable=AsyncMock)
    def test_claim_extraction_failure_returns_502(
        self, mock_extract, client, monkeypatch
    ):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        mock_extract.side_effect = RuntimeError("API down")

        resp = client.post("/verify", json={"text": "some text"})
        assert resp.status_code == 502
        assert "Claim extraction failed" in resp.json()["detail"]

    @patch("main.verify_claims", new_callable=AsyncMock)
    @patch("main.extract_claims", new_callable=AsyncMock)
    def test_claim_verification_failure_returns_502(
        self, mock_extract, mock_verify, client, monkeypatch
    ):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
        mock_extract.return_value = ["A claim"]
        mock_verify.side_effect = RuntimeError("API down")

        resp = client.post("/verify", json={"text": "some text"})
        assert resp.status_code == 502
        assert "Claim verification failed" in resp.json()["detail"]
