"""Karaar Saathi — FastAPI entrypoint.

Stateless by design: uploaded documents are processed in memory, PII is
redacted before any AI call, and nothing about the document is persisted.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from collections import OrderedDict, defaultdict, deque
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import assist, gcp, kb, llm
from .parsing import Clause, extract_text, normalise, split_clauses
from .privacy import redact

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 5 * 1024 * 1024
ALLOWED_EXT = (".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp")
IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "40"))
CACHE_SIZE = 64
SAMPLES = {
    "rental_one_sided": ("Rental agreement (one-sided)", "rental_agreement_one_sided.txt"),
    "rental_balanced": ("Rental agreement (balanced)", "rental_agreement_balanced.txt"),
    "gig_partner": ("Delivery partner agreement", "gig_partner_agreement.txt"),
    "offer_letter": ("Offer letter with bond", "offer_letter.txt"),
}
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
    "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'self'"
)

gcp.setup_logging()
log = logging.getLogger("karaar")

app = FastAPI(
    title="Karaar Saathi",
    version="1.1.0",
    description="Plain-language legal document assistant for tenants, gig workers and first-job employees in India.",
)
app.add_middleware(GZipMiddleware, minimum_size=1024)

_hits: dict[str, deque] = defaultdict(deque)
_cache: OrderedDict[str, dict] = OrderedDict()


def _client_ip(request: Request) -> str:
    """Use the rightmost X-Forwarded-For hop (added by Google's front end); earlier hops can be spoofed."""
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    return hops[-1] if hops else (request.client.host if request.client else "unknown")


@app.middleware("http")
async def guard(request: Request, call_next):
    """Per-IP sliding-window rate limit on the API plus security headers on every response."""
    if request.url.path.startswith("/api/") and request.method == "POST":
        now, q = time.monotonic(), _hits[_client_ip(request)]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return JSONResponse(
                {"error": "Too many requests. Please wait a minute and try again."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        q.append(now)
    resp = await call_next(request)
    resp.headers.update(
        {
            "Content-Security-Policy": CSP,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }
    )
    resp.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api") else "public, max-age=300"
    return resp


# ------------------------------------------------------------------ helpers
def _lang(lang: str) -> str:
    return lang if lang in gcp.LANGUAGES else "en"


def _file_to_text(filename: str, data: bytes) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, "Unsupported file type. Use PDF, DOCX, TXT or a photo (PNG/JPG).")
    if ext in IMAGE_MIME:
        text = gcp.ocr_image(data) or llm.transcribe(data, IMAGE_MIME[ext])
        if not text:
            raise HTTPException(422, "Couldn't read text from this photo. Try a clearer photo, or paste the text.")
        return normalise(text)
    text = extract_text(filename, data)
    if ext == ".pdf" and len(text) < 40:  # scanned PDF: no text layer
        text = normalise(llm.transcribe(data, "application/pdf") or "")
    return text


async def _read_doc(file: UploadFile | None, text: str | None) -> tuple[list[Clause], dict, str]:
    if file is not None and file.filename:
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "File too large (max 5 MB).")
        try:
            raw = _file_to_text(file.filename, data)
        except HTTPException:
            raise
        except Exception as exc:
            log.info("Unreadable upload: %s", type(exc).__name__)
            raise HTTPException(422, "Could not read that file. Try another format or paste the text.") from exc
    else:
        raw = normalise(text or "")
    if len(raw) < 40:
        raise HTTPException(422, "Please upload a document or paste at least a few sentences of text.")
    safe, redactions = redact(raw)
    clauses = split_clauses(safe)
    if not clauses:
        raise HTTPException(422, "No readable clauses found.")
    return clauses, redactions, hashlib.sha256(safe.encode()).hexdigest()


def _cache_get(key: str) -> dict | None:
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    return None


def _cache_put(key: str, value: dict) -> None:
    _cache[key] = value
    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)


# ------------------------------------------------------------------ routes
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ai": llm.available(),
        "model": llm.MODEL if llm.available() else None,
        "google_cloud": gcp.enabled(),
    }


@app.get("/api/languages")
def languages():
    return [{"code": k, **v, "machine_translated": k not in gcp.NATIVE_LANGS} for k, v in gcp.LANGUAGES.items()]


@app.get("/api/samples")
def samples():
    return [{"id": k, "label": v[0]} for k, v in SAMPLES.items()]


@app.get("/api/samples/{sample_id}")
def sample(sample_id: str):
    if sample_id not in SAMPLES:
        raise HTTPException(404, "Unknown sample")
    return {"id": sample_id, "text": (ROOT / "samples" / SAMPLES[sample_id][1]).read_text(encoding="utf-8")}


@app.post("/api/analyse")
async def analyse(
    file: UploadFile | None = File(None),
    text: str | None = Form(None, max_length=200_000),
    lang: str = Form("en"),
    ai: bool = Form(True),
):
    lang = _lang(lang)
    clauses, redactions, digest = await _read_doc(file, text)
    key = f"{digest}:{lang}:{ai and llm.available()}"
    cached = _cache_get(key)
    if cached is not None:
        return {**cached, "cached": True}
    result = assist.analyse(clauses, assist.base_lang(lang), use_ai=ai)
    result = assist.localise(result, lang)
    result["redactions"] = redactions
    result["lang"] = lang
    _cache_put(key, result)
    log.info(
        "analysed doc_type=%s clauses=%d flags=%d mode=%s",
        result["doc_type"],
        len(clauses),
        len(result["flags"]),
        result["mode"],
    )
    return result


class ClauseIn(BaseModel):
    id: str = Field(pattern=r"^C\d{1,4}$")
    heading: str = Field("", max_length=200)
    text: str = Field(max_length=5000)


class AskBody(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    clauses: list[ClauseIn] = Field(min_length=1, max_length=400)
    doc_type: Literal["rental", "gig", "employment", "other"] = "other"
    flags: list[dict] = Field(default_factory=list, max_length=200)
    lang: str = "en"


@app.post("/api/ask")
def ask(body: AskBody):
    lang = _lang(body.lang)
    result = assist.ask(
        body.question, [c.model_dump() for c in body.clauses], body.doc_type, body.flags, assist.base_lang(lang)
    )
    return assist.localise(result, lang)


@app.post("/api/compare")
async def compare(
    file_a: UploadFile | None = File(None),
    text_a: str | None = Form(None, max_length=200_000),
    file_b: UploadFile | None = File(None),
    text_b: str | None = Form(None, max_length=200_000),
    lang: str = Form("en"),
):
    lang = _lang(lang)
    a, _, _ = await _read_doc(file_a, text_a)
    b, _, _ = await _read_doc(file_b, text_b)
    return assist.localise(assist.compare(a, b, assist.base_lang(lang)), lang)


class PrepBody(BaseModel):
    analysis: dict
    lang: str = "en"
    ai: bool = True


@app.post("/api/prep")
def prep(body: PrepBody):
    a = dict(body.analysis)
    for key in ("doc_type", "flags", "facts"):
        if key not in a:
            raise HTTPException(422, f"analysis.{key} missing — run /api/analyse first")
    if a["doc_type"] not in assist.TYPE_LABEL:
        a["doc_type"] = "other"
    lang = _lang(body.lang)
    return assist.localise(assist.prep_pack(a, assist.base_lang(lang), use_ai=body.ai), lang)


class SpeakBody(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    lang: str = "en"


@app.post("/api/speak")
def speak(body: SpeakBody):
    audio = gcp.speak(body.text, _lang(body.lang))
    if audio is None:
        raise HTTPException(503, "Server voice unavailable; using your device's voice instead.")
    return Response(content=audio, media_type="audio/mpeg")


class FeedbackBody(BaseModel):
    helpful: bool
    doc_type: Literal["rental", "gig", "employment", "other"] = "other"
    lang: str = "en"
    comment: str = Field("", max_length=500)


@app.post("/api/feedback")
def feedback(body: FeedbackBody):
    comment, _ = redact(body.comment)
    saved = gcp.save_feedback(
        {"helpful": body.helpful, "doc_type": body.doc_type, "lang": _lang(body.lang), "comment": comment}
    )
    return {"saved": saved}


@app.get("/api/kb")
def knowledge_base():
    """Transparency: every check the engine runs and the reference it relies on."""
    return [
        {"id": r.id, "applies_to": r.types, "title": r.title, "severity": r.severity, "reference": r.law}
        for r in kb.RULES + [kb.DEPOSIT_CAP, kb.LATE_FEE, kb.REGISTRATION]
    ]


@app.exception_handler(HTTPException)
async def http_error(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "static" / "index.html")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
