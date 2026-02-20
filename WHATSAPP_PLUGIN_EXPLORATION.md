# WhatsApp Plugin Exploration for LetMeVerifyThat

## Executive Summary

**Yes, building a WhatsApp plugin for LetMeVerifyThat is feasible** and well-aligned with the project's architecture. The existing FastAPI backend with its `claim_extractor` and `claim_verifier` modules can be reused almost entirely — the main work is adding a webhook endpoint and formatting responses for WhatsApp's message constraints.

This document explores the technical approach, costs, limitations, and a recommended implementation plan.

---

## Why WhatsApp Is a Strong Fit

1. **Misinformation spreads on WhatsApp.** Forwarded messages, viral health claims, and suspicious links are the exact content LetMeVerifyThat was built to verify. Meeting users where misinformation lives is high-impact.

2. **The existing backend already handles the core flow.** The `POST /verify` endpoint accepts text and URLs, extracts claims, and verifies them — the same pipeline a WhatsApp bot would use.

3. **WhatsApp's Cloud API is free for reactive bots.** When a user messages the bot first, a 24-hour window opens during which all replies are free. Since a fact-checking bot is inherently reactive (user sends claim → bot replies), messaging costs are effectively $0.

4. **Precedent exists.** Perplexity itself runs a WhatsApp fact-checking number (+1 833 436 3285). Meedan's Check Bot is used by fact-checking orgs globally. An n8n template combines Twilio + Perplexity for WhatsApp fact-checking.

---

## How It Would Work

### User Experience

```
User sends:  "I heard turmeric cures cancer and MSG is toxic"

Bot replies:  "I found 2 claims to verify. Checking now..."

Bot replies:  ❌ Claim: "Turmeric cures cancer"
              Verdict: MISLEADING (35% confidence)
              Turmeric contains curcumin which has shown some
              anti-inflammatory properties in lab studies, but
              there is no clinical evidence it cures cancer.
              Sources: NIH, PubMed

Bot replies:  ❌ Claim: "MSG is toxic"
              Verdict: FALSE (15% confidence)
              FDA classifies MSG as GRAS. Decades of research
              show no evidence of toxicity at normal dietary levels.
              Sources: FDA.gov, WHO
```

Users could also:
- **Forward a suspicious message** — the bot extracts claims from the forwarded text
- **Paste a URL** — the bot fetches the article, extracts claims, and verifies them
- **Send images/videos** (future) — with OCR or transcription added to the pipeline

### Technical Architecture

```
[WhatsApp User]
       |
       v
[Meta Cloud API] --webhook POST--> [FastAPI Backend]
       ^                                  |
       |                                  v
       |                          [Message Router]
       |                           /            \
       |                  [Text Handler]    [URL Handler]
       |                       |                 |
       |                       v                 v
       |               [claim_extractor]  [url_extractor]
       |                       |                 |
       |                       v                 v
       |               [claim_verifier (Perplexity Sonar)]
       |                       |
       |                       v
       |               [Format for WhatsApp]
       |                       |
       +--- POST /messages <---+
```

### What Changes in the Codebase

| Component | Change Required |
|-----------|----------------|
| `backend/main.py` | Add `/webhook/whatsapp` GET (verification) and POST (message handler) endpoints |
| `backend/claim_extractor.py` | No changes — reuse as-is |
| `backend/claim_verifier.py` | No changes — reuse as-is |
| `backend/url_extractor.py` | No changes — reuse as-is |
| New: `backend/whatsapp.py` | WhatsApp Cloud API client (send messages, handle webhooks) |
| New: `backend/formatters.py` | Format `ClaimVerification` results into WhatsApp-friendly text |
| `.env` | Add `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` |

The core verification pipeline stays untouched. The new code is purely integration glue.

---

## WhatsApp Cloud API Details

### API Choice: Official Cloud API (Recommended)

| Option | Recommendation | Reasoning |
|--------|---------------|-----------|
| **WhatsApp Cloud API (direct)** | **Recommended** | Free hosting by Meta, no ban risk, production-grade |
| **Twilio WhatsApp** | Good for prototyping | Adds per-message markup but has a sandbox for testing |
| **Baileys / whatsapp-web.js** | **Avoid** | Unofficial, violates ToS, phone number ban risk |

### Costs

| Item | Cost |
|------|------|
| WhatsApp Cloud API setup | Free |
| Service messages (replies within 24-hr window) | **Free** |
| Utility template messages (within 24-hr window) | **Free** |
| Template messages (outside 24-hr window) | ~$0.004–$0.046/msg (varies by country) |
| Perplexity Sonar API | Existing cost (the real expense) |
| Server hosting for webhook | Existing infrastructure |

**For a reactive fact-checking bot, WhatsApp messaging is essentially free.** The primary cost remains Perplexity API usage.

### Message Capabilities

**Can receive from users:**
- Text (up to 4,096 chars), images, videos, audio, documents, locations, contacts, forwarded messages

**Can send to users (within 24-hr window):**
- Text (up to 1,600 chars), images, videos, documents
- Interactive reply buttons (up to 3 buttons)
- Interactive list messages (up to 10 options)
- CTA URL buttons (tappable links)

### Key Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| **24-hour reply window** | Cannot proactively message users after 24 hours | Not an issue — bot is reactive. For re-engagement, use approved templates. |
| **1,600 char text limit** | Long explanations must be split | Send one message per claim; link to full web results for details |
| **No group chat API** | Bot works in 1:1 conversations only | Acceptable for initial version |
| **Template approval required** | Proactive messages need Meta approval | Only needed for re-engagement features |
| **Business verification** | Meta reviews your business before going live | Standard process; plan for a few days |
| **Video/image processing** | WhatsApp sends media, but bot needs OCR/transcription | Phase 2 feature — start with text and URLs |

---

## Recommended Implementation Plan

### Phase 1: Core WhatsApp Bot (MVP)

**Goal:** Users can send text claims or URLs to verify directly in WhatsApp.

1. **Set up Meta Business Portfolio** — Register at business.facebook.com, create a Meta App, enable WhatsApp product.

2. **Add webhook endpoint** to existing FastAPI backend:
   - `GET /webhook/whatsapp` — Meta verification challenge handler
   - `POST /webhook/whatsapp` — Incoming message handler

3. **Create WhatsApp client module** (`backend/whatsapp.py`):
   - Send text messages via Cloud API
   - Send interactive button messages
   - Handle media downloads (for forwarded images)

4. **Create response formatter** (`backend/formatters.py`):
   - Convert `ClaimVerification` objects to WhatsApp-formatted text
   - Verdict indicators, confidence display, truncated explanations
   - Source links

5. **Wire up the existing pipeline:**
   - Text → `claim_extractor` → `claim_verifier` → format → send
   - URL detected → `url_extractor` → `claim_extractor` → `claim_verifier` → format → send

6. **Add async processing:**
   - Respond immediately with "Checking your claims..." (WhatsApp expects fast webhook responses)
   - Process verification in background task
   - Send results when ready

7. **Test with Meta sandbox** — Use test phone numbers before going live.

### Phase 2: Enhanced Input (Future)

- **Forwarded message detection** — WhatsApp marks forwarded messages; use this as a signal
- **Image OCR** — Extract text from screenshots of claims (e.g., using Tesseract or a cloud OCR service)
- **Video/audio transcription** — YouTube transcript extraction, or Whisper for audio messages
- **Interactive buttons** — "Verify another claim", "See full sources", "Share results"

### Phase 3: Scale & Polish (Future)

- **Usage analytics** — Track popular claims, verification volumes
- **Rate limiting** — Prevent abuse (per-user request limits)
- **Multi-language support** — Detect input language, respond accordingly
- **Database persistence** — Store verification results server-side (replace localStorage-only approach)
- **Shareable links** — Include link to full web results page in WhatsApp responses

---

## Proof of Concept: Minimal Webhook Handler

A minimal implementation would look roughly like this (pseudocode):

```python
# backend/whatsapp.py

import httpx
from claim_extractor import extract_claims
from claim_verifier import verify_claim
from url_extractor import extract_urls, fetch_url_text

WHATSAPP_API = "https://graph.facebook.com/v21.0"

async def handle_incoming_message(phone_number_id: str, from_number: str, text: str):
    """Handle an incoming WhatsApp message."""
    # 1. Acknowledge quickly
    await send_text(phone_number_id, from_number, "Checking your claims...")

    # 2. Extract URLs and fetch content (reuse existing modules)
    urls, remaining_text = extract_urls(text)
    fetched_texts = []
    for url in urls:
        content = await fetch_url_text(url)
        if content:
            fetched_texts.append(content)

    combined = remaining_text + "\n".join(fetched_texts)

    # 3. Extract and verify claims (reuse existing modules)
    claims = await extract_claims(combined)
    if not claims:
        await send_text(phone_number_id, from_number, "No verifiable claims found.")
        return

    for claim_text in claims:
        result = await verify_claim(claim_text)
        formatted = format_for_whatsapp(result)
        await send_text(phone_number_id, from_number, formatted)

async def send_text(phone_number_id: str, to: str, body: str):
    """Send a text message via WhatsApp Cloud API."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{WHATSAPP_API}/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body}
            }
        )
```

This reuses the existing `extract_claims`, `verify_claim`, `extract_urls`, and `fetch_url_text` functions with zero modifications.

---

## Existing Precedents

| Project | Description |
|---------|-------------|
| **Perplexity WhatsApp** | Perplexity runs its own WhatsApp fact-checking at +1 (833) 436-3285 |
| **Meedan Check Bot** | Used by fact-checking orgs in Brazil, India, Africa; handles forwarded messages |
| **n8n Template** | Workflow combining Twilio + Perplexity AI for WhatsApp fact-checking |
| **Fact-Checker-WhatsApp-Bot** | Open-source Flask + Twilio + OpenAI bot on GitHub |

---

## Conclusion

A WhatsApp plugin for LetMeVerifyThat is not only feasible — it's a natural extension. The architecture already separates concerns cleanly: the verification pipeline is independent of the delivery channel. Adding WhatsApp means building a thin webhook layer on top of the existing backend, with no changes to the core claim extraction and verification logic.

The official WhatsApp Cloud API makes this economically viable (free for reactive bots) and technically straightforward (webhook-based, REST API). The main investment is the integration code and Meta's business verification process, not a fundamental rearchitecture.
