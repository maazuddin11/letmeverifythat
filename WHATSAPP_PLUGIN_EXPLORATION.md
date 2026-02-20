# WhatsApp Plugin Exploration for LetMeVerifyThat

## Executive Summary

**Yes, building a WhatsApp plugin for LetMeVerifyThat is feasible** and well-aligned with the project's architecture. The existing FastAPI backend with its `claim_extractor` and `claim_verifier` modules can be reused almost entirely — the main work is adding a webhook endpoint and formatting responses for WhatsApp's message constraints.

This document explores the technical approach, costs, limitations, a recommended implementation plan, and monetization strategies for sustainability.

> **Important Policy Update (Jan 2026):** Meta banned general-purpose AI chatbots from WhatsApp effective January 15, 2026. However, **task-specific bots like fact-checkers appear to remain compliant** — the ban targets services where a general-purpose AI assistant is the "primary (rather than incidental or ancillary) functionality." See the [Platform Policy Risks](#platform-policy-risks-metas-2026-ai-chatbot-ban) section for details.

---

## Why WhatsApp Is a Strong Fit

1. **Misinformation spreads on WhatsApp.** Forwarded messages, viral health claims, and suspicious links are the exact content LetMeVerifyThat was built to verify. Meeting users where misinformation lives is high-impact.

2. **The existing backend already handles the core flow.** The `POST /verify` endpoint accepts text and URLs, extracts claims, and verifies them — the same pipeline a WhatsApp bot would use.

3. **WhatsApp's Cloud API is free for reactive bots.** When a user messages the bot first, a 24-hour window opens during which all replies are free. Since a fact-checking bot is inherently reactive (user sends claim → bot replies), messaging costs are effectively $0.

4. **Precedent exists.** Meedan's Check Bot is used by fact-checking orgs globally. Perplexity ran a WhatsApp fact-checker throughout 2025 (shut down by Meta's Jan 2026 policy — but that targeted general-purpose AI assistants, not task-specific bots like fact-checkers).

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

## Platform Policy Risks: Meta's 2026 AI Chatbot Ban

In October 2025, Meta announced that **general-purpose AI chatbots are banned from WhatsApp Business API effective January 15, 2026**. Perplexity, OpenAI (ChatGPT), and Microsoft (Copilot) all shut down their WhatsApp bots.

### Why Fact-Checking Bots Are Likely Exempt

The ban targets services where a general-purpose AI assistant is the **"primary (rather than incidental or ancillary) functionality."** Task-specific bots are explicitly allowed. A fact-checking bot fits the exemption because:

- It has a **single, defined purpose** (claim verification), not open-ended conversation
- AI is **incidental** to a broader public-interest mission
- It uses **structured interactions** (claim in, verdict out), not free-form chat
- Precedent: Meedan's Check Bot, Maldita.es, and The Quint's tipline all continue operating

### Compliance Requirements

To stay on the right side of this policy:

1. **Keep the bot strictly task-specific** — verify claims, don't hold open-ended conversations
2. **Use structured interactions** — menus, templates, and clear input/output patterns
3. **Frame the mission clearly** — public interest / journalism / misinformation-fighting
4. **Include human escalation paths** — option to flag complex claims for human review
5. **Partner with a Meta-approved BSP** if needed for additional credibility

### Evolving Landscape

EU antitrust probes and exemptions in Italy and Brazil may force Meta to revise this ban. Monitor developments — the policy could loosen or tighten further.

---

## Per-Request Cost Analysis

Understanding the actual cost structure is critical for any sustainability plan.

### API Calls Per User Request

Each verification request makes **1 + N Perplexity API calls**, where N is the number of claims found:

| Step | Model | Purpose | Search | Max Tokens |
|------|-------|---------|--------|------------|
| Claim extraction (1 call) | `sonar` (standard) | Extract verifiable claims from text | None | 1,024 |
| Claim verification (N calls, parallel) | `sonar-pro` (premium) | Verify each claim against real-time sources | Web search with domain filtering | 512 |

**The cost is variable, not fixed.** A message with 5 claims costs ~6x more than a message with 0 claims.

### Estimated Per-Query Costs (Perplexity Sonar Pricing)

| Model | Input | Output | Per-Request Fee | Estimated Cost/Call |
|-------|-------|--------|-----------------|---------------------|
| `sonar` (extraction) | $1/M tokens | $1/M tokens | $0.005–0.012 | ~$0.006 |
| `sonar-pro` (verification) | $3/M tokens | $15/M tokens | $0.006–0.014 | ~$0.012 |

**Example costs per user request (assuming 4 claims average):**

| Component | Calls | Cost/Call | Subtotal |
|-----------|-------|-----------|----------|
| Extraction | 1 | ~$0.006 | $0.006 |
| Verification | 4 | ~$0.012 | $0.048 |
| **Total** | **5** | | **~$0.054** |

### Monthly Cost Projections

| Scale | API Calls | Perplexity Cost | Hosting | WhatsApp | **Total/Month** |
|-------|-----------|----------------|---------|----------|-----------------|
| 1,000 requests/mo | ~5,000 | $50–65 | $10 | $0 | **$60–75** |
| 10,000 requests/mo | ~50,000 | $500–650 | $20 | $0 | **$520–670** |
| 100,000 requests/mo | ~500,000 | $5,000–6,500 | $50 | $0 | **$5,050–6,550** |

WhatsApp messaging remains $0 because the bot is reactive (all replies within the free 24-hour service window).

### Cost Reduction Levers

1. **Response caching** — Many misinformation claims are repeated verbatim. Caching identical queries could cut API calls by 30–50%.
2. **Downgrade verification model** — Use `sonar` instead of `sonar-pro` for simpler claims (saves ~50% per verification call).
3. **Cap claims per request** — Limit extraction to 5 claims max to bound the worst case.
4. **Per-user daily limits** — 3–5 free checks/day prevents abuse.

---

## Monetization and Sustainability

### How Existing Services Fund Themselves

| Service | Model | Details |
|---------|-------|---------|
| **Perplexity WhatsApp** | VC-subsidized loss leader | Entirely free. Used for user acquisition, not revenue. Shut down Jan 2026. |
| **Meedan Check Bot** | Philanthropic grants | $750K from McGovern Foundation, SIDA funding, Press Forward grants, micro-grants program. Nonprofit model. |
| **Maldita.es** | Grants + membership | Users become paying "malditas" (members) with recurring donations. Bot automates 60%+ of claim triage. |
| **FactCheck.org** | Foundation funding | Annenberg Foundation endowment + Facebook/Meta partnership fees. |

**Key takeaway:** No one in this space has cracked pure-profit monetization. The successful models are either VC-subsidized, grant-funded, or membership/donation-supported.

### Recommended Models (Ranked by Practicality for Break-Even)

#### 1. Freemium with Daily Limits (Most Practical)

Offer a free tier with a cap, charge for more:

- **Free:** 3–5 fact-checks per day per user
- **Premium:** $1–3/month for unlimited checks (or higher cap)
- **Math:** 500 paying users at $2/month = $1,000/month, covering ~15,000–20,000 requests

This is the most predictable model. It keeps the service accessible while shifting costs to power users.

#### 2. Donation/Tip Model

Embed a non-intrusive donation prompt in bot responses:

- _"This fact-check was free. Help keep it running: [link]"_
- Use Ko-fi, Buy Me a Coffee, GitHub Sponsors, or direct payment links
- WhatsApp donation bots show ~5x higher conversion than email
- **Math:** 10,000 requests/month, 3% donate $1 = $300/month vs ~$520–670 cost

Won't fully cover costs alone at scale, but works well **combined** with other models.

#### 3. Grant Funding

Several active programs fund fact-checking tools:

| Program | Amount | Notes |
|---------|--------|-------|
| **IFCN SUSTAIN Grants** (Poynter) | $30,000 each | Round 2 opens mid-Feb 2026 |
| **Global Fact Check Fund** (Google/YouTube/IFCN) | From $13.2M pool | Three tracks: BUILD/GROW/ENGAGE |
| **Meedan Micro-Grants** | Up to $15,000 | Rolling applications |
| **Democracy Fund Prototype Fund** | ~$50,000 avg | For misinformation-fighting tools |
| **Pulitzer Center Truth Decay** | Varies | Open to U.S. residents, global journalists |

Even one $15K micro-grant covers 12–18 months of operation at moderate scale. This requires nonprofit status or fiscal sponsorship and effort in proposal writing, but is highly viable for a public-interest tool.

#### 4. Institutional Licensing / White-Label

Sell access to the verification engine, not directly to consumers:

- **News organizations** pay $10–50/month to embed a fact-check widget or bot for their audience
- **Schools/libraries** get organizational access
- **NGOs** white-label the bot for their regions

This shifts your revenue source from individual users to organizations with budgets.

#### 5. API Access / Developer Tier

Offer the fact-checking pipeline as a paid API:

- Other developers or organizations call your `/verify` endpoint
- Charge per request (e.g., $0.10/check) or monthly subscription
- Covers your Perplexity costs with margin

### What Won't Work

| Model | Why Not |
|-------|---------|
| **Ads in bot responses** | Terrible UX in a trust-oriented service. Undermines credibility. |
| **Selling user data** | Ethical and legal minefield. Incompatible with a fact-checking mission. |
| **Pure free + hope for donations** | Doesn't scale. Perplexity could afford it with VC money; a small project can't. |

### Recommended Strategy: Layered Approach

The most resilient approach combines multiple revenue streams:

```
Month 1-3:   Free with daily limits (3 checks/day)
             + Donation link in every 3rd response
             + Apply for 1-2 grants (Meedan, IFCN)

Month 3-6:   Introduce $2/month premium tier
             + Implement response caching (cut costs 30-50%)

Month 6-12:  Pursue institutional licensing
             + API access tier for developers
             + Continue grant applications

Cost floor:  ~$60-75/month at 1K requests
Cost target: Break even at ~5K requests with 200 paying users
```

### Architecture for Cost Control

Build these into the system from day one:

1. **Response cache** — Store (claim_hash → result) with a TTL. Viral misinformation is highly repetitive.
2. **Tiered processing** — Simple claims use `sonar` ($0.006); complex claims escalate to `sonar-pro` ($0.012).
3. **Per-user rate limits** — Free tier: 3–5/day. Premium: 25–50/day. Hard cap prevents runaway costs.
4. **Usage dashboard** — Monitor daily API spend to catch spikes early.
5. **Claim deduplication** — Normalize claim text before extraction to catch near-duplicates.

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

| Project | Status | Funding Model | Description |
|---------|--------|---------------|-------------|
| **Perplexity WhatsApp** | Shut down (Jan 2026) | VC-subsidized (free) | Ran a free WhatsApp fact-checker throughout 2025; shut down by Meta's general-purpose AI bot ban |
| **Meedan Check Bot** | Active | Grants ($750K+ from multiple funders) | Used by fact-checking orgs in Brazil, India, Africa; handles forwarded messages |
| **Maldita.es** | Active | Grants + membership donations | Spanish fact-checker; bot automates 60%+ of claim triage |
| **n8n Template** | Active | Open-source template | Workflow combining Twilio + Perplexity AI for WhatsApp fact-checking |
| **Fact-Checker-WhatsApp-Bot** | Active | Open-source | Flask + Twilio + OpenAI bot on GitHub |

---

## Conclusion

A WhatsApp plugin for LetMeVerifyThat is technically feasible and architecturally natural — the verification pipeline is already independent of the delivery channel. Adding WhatsApp means building a thin webhook layer, not a rearchitecture.

**For sustainability**, the realistic path is a layered approach: free tier with daily limits + a low-cost premium tier + grant funding. No fact-checking service has achieved pure-profit monetization; the successful ones combine freemium, donations, and grants. The good news is that the cost floor is low (~$60–75/month at 1K requests), and even modest revenue from 200 paying users at $2/month covers significant scale.

**The key risk** is Meta's January 2026 ban on general-purpose AI chatbots. A task-specific fact-checking bot likely falls under the exemption, but this should be confirmed with Meta or a BSP partner before investing heavily in the integration. The policy landscape is actively shifting, with EU antitrust probes potentially forcing Meta to revise its stance.
