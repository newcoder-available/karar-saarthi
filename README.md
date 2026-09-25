# Karar-Sarthi · करार सारथी

**Understand your agreement before you sign.** Karar-Sarthi is a GenAI legal-information assistant for India's tenants, gig and platform workers, and first-job employees. It reads a rent agreement, a delivery-partner contract or an offer letter and does five things:

1. Explains the document in plain words, in 11 Indian languages, with read-aloud.
2. Flags risky, one-sided or unusual clauses, and each warning quotes the exact clause and a curated legal reference.
3. Answers questions using only the user's own document, with clause citations.
4. Compares two versions, showing what got better, what got worse and what is still worth negotiating.
5. Builds a **lawyer prep pack**: the situation, top concerns, questions to ask, documents to carry, options, a polite message asking for changes, and free legal-aid contacts.

> Karar-Sarthi provides legal **information**, not legal advice. It never predicts outcomes, and it sends users to free legal aid (NALSA 15100) when a document looks like a legal notice or summons.

---

## Why this problem

Most Indians sign legal documents without reading them closely. These three groups are the most exposed:

| User | Typical document | What goes wrong |
|---|---|---|
| Tenant | 11-month rent agreement | 6–10 month deposits, forfeiture, arbitrary rent hikes, lock-outs, entry without notice |
| Gig / platform worker | Click-through partner T&Cs | Deactivation without reason, payout changes without notice, unlimited indemnity, post-exit non-competes |
| First-job employee | Offer letter + bond | Training bonds, withheld original certificates, forfeited final settlement, non-competes |

Lawyers are expensive, and generic chatbots are unreliable here: they hallucinate laws, cannot say *which* clause is the problem, and send private documents to third parties unredacted.

## What makes it different

| | |
|---|---|
| **Rules first, AI second** | A curated **Fairness Benchmark** of India-specific checks (Model Tenancy Act 2021, Indian Contract Act ss.27/28/74, Code on Social Security 2020, Arbitration Act s.12(5) and the *CORE* (2024) Constitution Bench ruling, DPDP Act 2023…) runs before any model call. Every legal reference shown comes from this reviewed list, never from the model. |
| **Evidence-locked AI** | Gemini can add flags only if it quotes the clause **verbatim**. The server checks each quote against the document and discards any that don't match. Answers must cite clause ids that were actually retrieved, and citations the model invents are rejected. The UI shows how many AI claims were thrown away. |
| **Privacy by design** | Aadhaar, PAN, phone, email, IFSC and account numbers are masked **before** any AI call. Documents are processed in memory and never stored. Feedback is anonymous. |
| **Works offline** | With no API key, every feature still works through the rules engine, including Hindi, so a demo never goes dark. |
| **Built for real users** | Hindi-first copy, 11 languages via Cloud Translation, read-aloud via Cloud Text-to-Speech, photo upload via Cloud Vision OCR, large-text mode, WCAG 2.1 AA. |
| **Knows its limits** | Detects legal notices and deadlines and escalates to NALSA 15100, DLSA and Tele-Law. Refuses to predict outcomes ("Will I win?") and turns the question into what to ask a lawyer. |

## Google services used

| Service | Where | Why |
|---|---|---|
| **Gemini on Vertex AI** (`google-genai`) | `app/llm.py` | Plain-language overview, extra clause review, grounded Q&A, comparison narrative, negotiation message, multimodal OCR fallback for scanned PDFs |
| **Cloud Vision** | `app/gcp.py::ocr_image` | Reads photos of paper agreements (`document_text_detection`, en/hi hints) |
| **Cloud Translation v3** | `app/gcp.py::translate`, `app/assist.py::localise` | Output in Bengali, Marathi, Tamil, Telugu, Kannada, Malayalam, Gujarati, Punjabi and Urdu; clause text is never translated, so citations stay faithful |
| **Cloud Text-to-Speech** | `app/gcp.py::speak`, `/api/speak` | Reads the summary aloud in Indian-locale voices, for low-literacy and visually impaired users |
| **Firestore** | `app/gcp.py::save_feedback` | Anonymous helpful/not-helpful feedback (PII-redacted, no document content) |
| **Cloud Logging** | `app/gcp.py::setup_logging` | Structured logs on Cloud Run (no document content logged) |
| **Cloud Run + Cloud Build + Artifact Registry** | `Dockerfile`, `cloudbuild.yaml` | Lint → test → build → deploy pipeline |

Every integration fails soft: if a service is unavailable, the app falls back to the rules engine, the browser's own voice, or English.

## Architecture

```
Browser (vanilla JS, WCAG 2.1 AA, no HTML-string injection)
   │  upload / paste / photo
   ▼
FastAPI on Cloud Run ── rate limit · CSP & security headers · size/type validation · GZip
   │
   ├─ parsing.py   PDF/DOCX/TXT → text      (Cloud Vision / Gemini OCR for images & scans)
   ├─ privacy.py   mask Aadhaar/PAN/phone/email/bank  ◄── before anything else
   ├─ parsing.py   split into numbered clauses C1…Cn (the unit of every citation)
   ├─ engine.py    classify → key facts → Fairness Benchmark flags → missing protections
   │               → urgency detector → transparent fairness score → BM25 retriever (+Hindi terms)
   ├─ llm.py       Gemini: overview, extra flags, grounded answers, compare, message
   │               └─ guardrails: document-as-data prompt · verbatim-quote check · citation check
   ├─ assist.py    merges rules + AI, offline fallbacks, prep pack, Cloud Translation localisation
   └─ gcp.py       Vision · Translation · Text-to-Speech · Firestore · Logging  (all optional)
```

### API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/analyse` | multipart `file` or `text`, `lang`, `ai` → full analysis (cached by content hash) |
| `POST` | `/api/ask` | question + clauses → cited answer |
| `POST` | `/api/compare` | two documents → diff, scores, narrative |
| `POST` | `/api/prep` | analysis → lawyer prep pack |
| `POST` | `/api/speak` | text → MP3 (Cloud TTS) |
| `POST` | `/api/feedback` | anonymous feedback → Firestore |
| `GET` | `/api/kb` | every check and its legal reference (transparency) |
| `GET` | `/api/languages`, `/api/samples`, `/api/health`, `/docs` | metadata, sample documents, health check, OpenAPI |

## Security

- PII masked before any model call; documents never persisted; feedback comments are redacted too.
- Prompt-injection resistant: the document is wrapped as `<document>` data, the system prompt forbids following instructions inside it, and outputs are validated server-side.
- Strict Content-Security-Policy (`script-src 'self'`, no inline script), `X-Frame-Options: DENY`, HSTS, `nosniff`, `no-referrer`, `Permissions-Policy`.
- Front end builds the DOM with `textContent` only: no `innerHTML`, no `eval`.
- Per-IP sliding-window rate limit that resists `X-Forwarded-For` spoofing; 5 MB upload cap with a bounded read; extension allow-list; Pydantic validation (clause ids must match `^C\d+$`, bounded list sizes).
- Generic error messages (no stack traces or parser internals leaked); non-root container; pinned dependencies; secrets only via env / Vertex service account.

## Efficiency

- Rules engine runs in milliseconds with pre-compiled, cached regexes; Gemini is called once per analysis.
- LRU cache keyed by a SHA-256 of the redacted text, language and mode, so switching views or re-running doesn't re-bill the model.
- Stateless Q&A: the client sends back only the clauses it has, and BM25 retrieval sends Gemini just the top 4.
- Cloud clients are created once (`lru_cache`); translation is batched (100 strings per call); GZip responses; no front-end framework (~27 KB JS, unminified).

## Testing

```bash
pip install -r requirements-dev.txt
ruff check app tests && pytest --cov=app          # 100 tests, ~95% coverage, fail_under=90
npm i && pip install playwright && pytest tests/test_accessibility.py   # + axe-core WCAG audit in a real browser
```

- `test_engine.py`: parsing, redaction, classification, fact extraction, every sample's expected flags, evidence integrity, knowledge-base integrity, Hindi retrieval.
- `test_ai_guardrails.py`: Gemini and Cloud mocks. Checks that fabricated quotes are rejected, invented citations are rejected, uncited answers are rejected, every service fails soft, translation never touches clause text, and the prompt treats the document as data.
- `test_api.py`: every endpoint, validation, 413/415/422/429/503 paths, security headers, caching, OCR path, spoofed-IP rate limiting.
- `test_accessibility.py`: static checks (one h1, labels, ARIA tabs, live regions, focus styles, no unsafe DOM APIs) plus an **axe-core WCAG 2.1 AA audit of every UI state in light and dark mode: 0 violations**.

## Accessibility

Skip link · single `h1` and logical headings · labelled controls · WAI-ARIA tabs with arrow/Home/End keys · `aria-live` regions for results and chat · `role="alert"` errors · focus moved to new results · visible `:focus-visible` · 44 px touch targets · severity shown as text, not only colour · light/dark themes with AA contrast · `prefers-reduced-motion` · large-text toggle · read-aloud · `lang`/`dir` switch per language (RTL for Urdu) · mobile layout with no horizontal scroll · print stylesheet for the prep pack.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env   # set GOOGLE_API_KEY, or Vertex AI project settings; leave empty for offline mode
uvicorn app.main:app --reload --port 8080
# open http://localhost:8080 and click a sample
```

## Deploy to Cloud Run

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com vision.googleapis.com translate.googleapis.com texttospeech.googleapis.com firestore.googleapis.com
gcloud artifacts repositories create karar --repository-format=docker --location=asia-south1
gcloud firestore databases create --location=asia-south1
gcloud builds submit --config cloudbuild.yaml
```

Give the Cloud Run service account these roles: `roles/aiplatform.user`, `roles/cloudtranslate.user`, `roles/datastore.user`, `roles/logging.logWriter`. Vision and Text-to-Speech only need their APIs enabled.

## Demo script (3 minutes)

1. **Understand**: click *Rental agreement (one-sided)* → *Explain*. The score shows 0/100 and 16 flags, each quoting its clause: a 6-month deposit against the 2-month Model Tenancy Act benchmark, forfeiture, lock-out and utility cut-off, a court bar, and a landlord-appointed arbitrator (*CORE* 2024). Aadhaar, PAN and phone are masked.
2. **Ask**: "When will I get my deposit back?" returns a cited answer, and clicking **C7** jumps to the clause. Ask "Will I win if I sue?" and it declines to predict and turns the question into one for a lawyer.
3. **Language**: switch to हिन्दी (or தமிழ் with Cloud Translation), then 🔊 read aloud.
4. **Compare**: load the draft vs revised sample. The score goes 0 → 100: the deposit drops from 6× to 2× rent, the lock-in from 11 to 3 months, and 14 risks are fixed.
5. **Prep pack**: create it, copy the message to the landlord, and download it as Markdown or print it.
6. Repeat with the **gig partner** sample (deactivation, payout changes, non-compete, e-Shram) and the **offer letter** (₹2 lakh bond, withheld certificates).

## Project layout

```
app/        main.py (API) · engine.py (rules) · kb.py (Fairness Benchmark) · llm.py (Gemini)
            assist.py (orchestration, prep pack, localisation) · gcp.py (Google Cloud) · parsing.py · privacy.py
static/     index.html · app.js · styles.css
samples/    four realistic Indian documents (fictional parties)
tests/      engine · AI guardrails · API · accessibility
```

## Limitations

The legal content is a benchmark reviewed in Sept 2026, not a statement of every state's law. Tenancy is a state subject, and the Model Tenancy Act applies only where a state has adopted it, which the app says every time. Rule coverage is focused on three document types. Machine translations beyond English and Hindi are labelled as such. Always confirm with a lawyer or free legal aid before acting.
