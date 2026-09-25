"""PII redaction applied before any text leaves the server for the LLM.

Aadhaar, PAN, Indian mobile numbers, emails and bank account/IFSC details are
masked. The original document is never persisted.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AADHAAR", re.compile(r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("IFSC", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("PHONE", re.compile(r"(?:\+91[\s-]?|\b0)?\b[6-9]\d{4}[\s-]?\d{5}\b")),
    ("ACCOUNT", re.compile(r"(?i)(?:a/c|account)\s*(?:no\.?|number)?\s*[:#-]?\s*\d{9,18}")),
]


def redact(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for label, pat in _PATTERNS:
        text, n = pat.subn(f"[{label}]", text)
        if n:
            counts[label] = n
    return text, counts
