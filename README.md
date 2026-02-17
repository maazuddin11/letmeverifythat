# LetMeVerifyThat

A fact-checking app powered by Perplexity's Sonar API. Paste in some text (eventually a URL) and it'll break down the individual claims, verify each one against real sources, and give you confidence scores with citations.

The idea came from getting forwarded health videos from family — "turmeric cures cancer", "MSG is toxic" etc. — and wanting a quick way to check what's actually true. Building this as a way to play with Perplexity's Sonar API and learn what it can do, especially around search grounding, citations, and domain filtering.

## Feature Set
### Must Haves
- Extract individual claims from user-provided text
- Verify each claim using Perplexity Sonar API
- Return a verdict per claim (True / Mostly True / Misleading / False / Unverifiable)
- Confidence scores (0-100) with brief explanations
- Source citations from Sonar's web-grounded responses
- Prioritize reputable sources for health claims (.gov, .edu, pubmed etc.) via `search_domain_filter`

### Nice to Haves
- URL support — paste an article/blog link and auto-extract claims from it
- Shareable results pages with unique URLs
- History of past verifications
- Social media / video support (Instagram, TikTok, YouTube transcripts)

## Tech Stack
- **Backend:** Python + FastAPI
- **Frontend:** Next.js (React) + Tailwind CSS
- **AI:** Perplexity Sonar API

## Setup
TODO
