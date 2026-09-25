"""Document ingestion: file -> text -> numbered clauses.

Clauses are the unit everything else cites. Each gets a stable id (C1, C2, ...)
so that every flag, answer and comparison can point back to exact source text.
"""

from __future__ import annotations

import io
import re
from dataclasses import asdict, dataclass

MAX_CHARS = 60_000  # ~15 pages; keeps latency and cost predictable


@dataclass
class Clause:
    id: str
    heading: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


def extract_text(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    elif name.endswith(".docx"):
        import docx

        d = docx.Document(io.BytesIO(data))
        text = "\n".join(p.text for p in d.paragraphs)
    else:
        text = data.decode("utf-8", errors="ignore")
    return normalise(text)


def normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_CHARS]


# A clause starts at a line like "1.", "12)", "3.2", "(a)", "Clause 4", "ARTICLE V"
_CLAUSE_START = re.compile(
    r"^\s*(?:(?:clause|article|section)\s+[\dIVXivx]+[.:)]?|\d{1,2}(?:\.\d{1,2})*[.)]\s|\(\s*[a-z]\s*\)\s|[IVX]{1,4}\.\s)",
    re.IGNORECASE,
)


def split_clauses(text: str) -> list[Clause]:
    lines = [ln.rstrip() for ln in text.split("\n")]
    blocks: list[list[str]] = []
    current: list[str] = []
    numbered_seen = False
    for ln in lines:
        if _CLAUSE_START.match(ln):
            numbered_seen = True
            if current:
                blocks.append(current)
            current = [ln.strip()]
        elif not ln.strip():
            if not numbered_seen and current:  # paragraph mode until numbering appears
                blocks.append(current)
                current = []
        else:
            current.append(ln.strip())
    if current:
        blocks.append(current)

    clauses: list[Clause] = []
    for block in blocks:
        body = " ".join(block).strip()
        if len(body) < 3:
            continue
        # Long unnumbered blobs get split by sentence groups so citations stay precise
        for chunk in _chunk(body, 900):
            heading = _heading(chunk)
            clauses.append(Clause(id=f"C{len(clauses) + 1}", heading=heading, text=chunk))
    return clauses


def _chunk(body: str, limit: int) -> list[str]:
    if len(body) <= limit:
        return [body]
    sentences = re.split(r"(?<=[.;])\s+", body)
    out, buf = [], ""
    for s in sentences:
        if buf and len(buf) + len(s) > limit:
            out.append(buf.strip())
            buf = ""
        buf += s + " "
    if buf.strip():
        out.append(buf.strip())
    return out


def _heading(text: str) -> str:
    m = re.match(r"^\s*(?:[\d.()a-zA-Z]{1,8}[.)]?\s+)?([A-Z][A-Za-z /&'-]{2,40})[:.\-–]", text)
    if m:
        return m.group(1).strip()
    words = re.sub(r"^\s*[\d.()]+\s*", "", text).split()
    return " ".join(words[:6]) + ("…" if len(words) > 6 else "")
