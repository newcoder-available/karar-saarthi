"""Deterministic analysis layer (works with no LLM at all).

Produces: document type, key facts, evidence-locked risk flags, missing
protections, urgency signal, and a keyword retriever for Q&A. The LLM layer
builds on top of this, and its outputs are checked against it.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from contextlib import suppress
from functools import lru_cache

from . import kb
from .parsing import Clause

WORD_NUM = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "thirty": 30,
    "sixty": 60,
    "ninety": 90,
}

_AMOUNT = re.compile(r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)(?:\s*/-)?", re.IGNORECASE)


# ------------------------------------------------------------------ helpers
@lru_cache(maxsize=512)
def _rx(pattern: str) -> re.Pattern:
    """Compile each knowledge-base pattern once."""
    return re.compile(pattern, re.IGNORECASE)


def _amounts(text: str) -> list[float]:
    out = []
    for m in _AMOUNT.finditer(text):
        with suppress(ValueError):
            out.append(float(m.group(1).replace(",", "")))
    return [a for a in out if a > 0]


def _num(token: str) -> float | None:
    token = token.lower().strip()
    if token in WORD_NUM:
        return WORD_NUM[token]
    try:
        return float(token)
    except ValueError:
        return None


def _snippet(text: str, m: re.Match, pad: int = 70) -> str:
    s, e = max(0, m.start() - pad), min(len(text), m.end() + pad)
    # expand to word boundaries
    while s > 0 and text[s - 1].isalnum():
        s -= 1
    while e < len(text) and text[e].isalnum():
        e += 1
    return ("…" if s > 0 else "") + text[s:e].strip() + ("…" if e < len(text) else "")


# ------------------------------------------------------------------ classification
_TYPE_SIGNALS = {
    kb.RENTAL: [
        r"\btenan",
        r"\blandlord",
        r"\blessor",
        r"\blessee",
        r"\brent\b",
        r"leave\s+and\s+licen",
        r"premises",
        r"security\s+deposit",
    ],
    kb.GIG: [
        r"platform",
        r"delivery\s+partner",
        r"\bpartner\b",
        r"aggregator",
        r"\bapp\b",
        r"per\s+(order|trip|task)",
        r"payout",
        r"independent\s+contractor",
        r"deactivat",
    ],
    kb.JOB: [
        r"employ",
        r"\bctc\b",
        r"probation",
        r"designation",
        r"offer\s+letter",
        r"joining",
        r"salary",
        r"appointment",
    ],
}


def classify(text: str) -> tuple[str, dict[str, int]]:
    low = text.lower()
    scores = {t: sum(len(re.findall(p, low)) for p in pats) for t, pats in _TYPE_SIGNALS.items()}
    best = max(scores, key=scores.get)
    return (best if scores[best] > 0 else "other"), scores


# ------------------------------------------------------------------ key facts
def key_facts(clauses: list[Clause], doc_type: str) -> dict:
    full = " ".join(c.text for c in clauses)
    facts: dict = {}

    rent = None
    candidates = [
        c
        for c in clauses
        if re.search(r"\brent\b|licen[cs]e\s+fee", c.text, re.I)
        and re.search(r"per\s+month|monthly|p\.?m\.?|/month|a\s+month", c.text, re.I)
        and [a for a in _amounts(c.text) if a >= 500]
    ]
    # prefer the clause that is about rent itself, not the deposit clause that mentions rent
    candidates.sort(key=lambda c: bool(re.search(r"deposit", c.text, re.I)))
    if candidates:
        c = candidates[0]
        rent = [a for a in _amounts(c.text) if a >= 500][0]
        facts["monthly_rent"] = {"value": rent, "clause": c.id}

    for c in clauses:
        low = c.text.lower()
        if re.search(
            r"security\s+deposit|interest[- ]free\s+(refundable\s+)?deposit|advance\s+deposit|\bdeposit\b", low
        ):
            m = re.search(r"(\w+)\s*(?:\(\d+\)\s*)?months?'?\s*(?:of\s+)?(?:the\s+)?(?:monthly\s+)?rent", low)
            months = _num(m.group(1)) if m else None
            amts = [a for a in _amounts(c.text) if not rent or a != rent]
            amount = max(amts) if amts else None
            if months is None and amount and rent:
                months = round(amount / rent, 1)
            if amount or months:
                facts["security_deposit"] = {"value": amount, "months_of_rent": months, "clause": c.id}
                break

    for c in clauses:
        if doc_type == kb.JOB or re.search(r"compet|lock[- ]?in|probation|bond|service\s+agreement", c.text, re.I):
            continue
        m = re.search(r"(?:period|term)\s+of\s+(\w+)\s*(?:\(\d+\)\s*)?(months?|years?)", c.text, re.I)
        if m and _num(m.group(1)):
            facts["term"] = {"value": f"{int(_num(m.group(1)))} {m.group(2).lower()}", "clause": c.id}
            break

    for c in clauses:
        m = re.search(r"lock[- ]?in\s+(?:period\s+)?(?:of\s+)?(\w+)\s*(?:\(\d+\)\s*)?(months?|years?)", c.text, re.I)
        if m and _num(m.group(1)):
            facts["lock_in"] = {"value": f"{int(_num(m.group(1)))} {m.group(2).lower()}", "clause": c.id}
            break

    ordered = sorted(clauses, key=lambda c: not re.search(r"terminat|resign|vacate|notice\s+period", c.text, re.I))
    ordered = [c for c in ordered if not re.search(r"probation|revis|increase|enter", c.text, re.I)] or ordered
    for c in ordered:
        m = re.search(
            r"(\w+)\s*(?:\(\d+\)\s*)?(days?|months?)(?:'s|')?\s*(?:prior\s+)?(?:written\s+)?notice", c.text, re.I
        ) or re.search(r"notice\s+(?:period\s+)?of\s+(\w+)\s*(?:\(\d+\)\s*)?(days?|months?)", c.text, re.I)
        if m and _num(m.group(1)):
            facts["notice_period"] = {"value": f"{int(_num(m.group(1)))} {m.group(2).lower()}", "clause": c.id}
            break

    for c in clauses:
        m = re.search(
            r"(\d+(?:\.\d+)?)\s*%[^.]{0,60}(increase|escalat|enhance|hike)|(increase|escalat|enhance)\w*[^.]{0,60}?(\d+(?:\.\d+)?)\s*%",
            c.text,
            re.I,
        )
        if m and re.search(r"rent|fee|salary", c.text, re.I):
            pct = m.group(1) or m.group(4)
            facts["escalation"] = {"value": f"{pct}%", "clause": c.id}
            break

    for c in clauses:
        m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:per\s+month|p\.?m\.?|a\s+month|monthly)", c.text, re.I)
        if m and re.search(r"late|delay|interest|overdue", c.text, re.I):
            facts["late_interest_pm"] = {"value": float(m.group(1)), "clause": c.id}
            break

    for label, pat in (("salary_ctc", r"(ctc|cost\s+to\s+company|salary)"),):
        if doc_type == kb.JOB:
            for c in clauses:
                if re.search(pat, c.text, re.I):
                    amts = _amounts(c.text)
                    if amts:
                        facts[label] = {"value": max(amts), "clause": c.id}
                        break

    m = re.search(
        r"(?:jurisdiction\s+of\s+the\s+courts?\s+(?:at|in)|courts?\s+(?:at|in)|seated\s+(?:at|in))\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
        full,
    )
    if m:
        facts["jurisdiction"] = {"value": m.group(1)}
    return facts


# ------------------------------------------------------------------ flags
def _flag(rule: kb.Rule, clause: Clause | None, evidence: str, source: str = "rules", **fmt) -> dict:
    return {
        "rule_id": rule.id,
        "category": rule.category,
        "title": rule.title,
        "severity": rule.severity,
        "clause_id": clause.id if clause else None,
        "evidence": evidence,
        "explain_en": rule.explain_en.format(**fmt) if fmt else rule.explain_en,
        "explain_hi": rule.explain_hi.format(**fmt) if fmt else rule.explain_hi,
        "law": rule.law,
        "ask_lawyer": rule.ask_lawyer,
        "negotiate": rule.negotiate,
        "source": source,
    }


def find_flags(clauses: list[Clause], doc_type: str, facts: dict) -> list[dict]:
    flags: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for rule in kb.RULES:
        if doc_type not in rule.types and doc_type != "other":
            continue
        for c in clauses:
            low = c.text.lower()
            if rule.all_of and not all(_rx(p).search(low) for p in rule.all_of):
                continue
            if rule.none_of and any(_rx(p).search(low) for p in rule.none_of):
                continue
            for p in rule.patterns:
                m = _rx(p).search(low)
                if (
                    m
                    and (rule.id, c.id) not in seen
                    and not (rule.id == "X_BLANKS" and any(f["rule_id"] == "X_BLANKS" for f in flags))
                ):
                    seen.add((rule.id, c.id))
                    flags.append(_flag(rule, c, _snippet(c.text, m)))
                    break

    by_id = {c.id: c for c in clauses}
    dep = facts.get("security_deposit")
    if doc_type == kb.RENTAL and dep and dep.get("months_of_rent") and dep["months_of_rent"] > 2:
        c = by_id.get(dep["clause"])
        months = dep["months_of_rent"]
        months_s = str(int(months)) if float(months).is_integer() else str(months)
        flags.append(_flag(kb.DEPOSIT_CAP, c, c.text[:220] + ("…" if len(c.text) > 220 else ""), months=months_s))

    li = facts.get("late_interest_pm")
    if li and li["value"] >= 2:
        c = by_id.get(li["clause"])
        rate = li["value"]
        annual = round(((1 + rate / 100) ** 12 - 1) * 100)
        rate_s = str(int(rate)) if float(rate).is_integer() else str(rate)
        m = re.search(r"\d+(?:\.\d+)?\s*%", c.text)
        flags.append(_flag(kb.LATE_FEE, c, _snippet(c.text, m) if m else c.text[:200], rate=rate_s, annual=annual))

    if doc_type == kb.RENTAL:
        term = facts.get("term", {}).get("value", "")
        c = by_id.get(facts.get("term", {}).get("clause", ""))
        flags.append(_flag(kb.REGISTRATION, c, c.text[:200] if c else f"Term: {term or 'not stated'}"))

    flags.sort(key=lambda f: (kb.SEVERITY_ORDER[f["severity"]], int((f["clause_id"] or "C999")[1:])))
    return flags


def missing_protections(clauses: list[Clause], doc_type: str) -> list[dict]:
    full = " ".join(c.text for c in clauses).lower()
    return [
        {"id": e["id"], "label": e["label"], "label_hi": e["hi"]}
        for e in kb.EXPECTED.get(doc_type, [])
        if not _rx(e["pattern"]).search(full)
    ]


def urgency(text: str) -> list[str]:
    hits = []
    for p in kb.URGENT_PATTERNS:
        m = _rx(p).search(text)
        if m:
            hits.append(m.group(0))
    return hits


def score(flags: list[dict], missing: list[dict]) -> dict:
    """Fairness score: 100 minus weighted issues. Transparent by design."""
    weights = {kb.HIGH: 14, kb.MEDIUM: 7, kb.LOW: 3, kb.INFO: 0}
    penalty = sum(weights[f["severity"]] for f in flags) + 4 * len(missing)
    value = max(0, 100 - penalty)
    band = (
        "Looks balanced"
        if value >= 80
        else "Needs a closer look"
        if value >= 55
        else "One-sided — negotiate or get advice"
    )
    band_hi = "संतुलित लगता है" if value >= 80 else "ध्यान से देखें" if value >= 55 else "एकतरफ़ा — बातचीत करें या सलाह लें"
    return {
        "value": value,
        "band": band,
        "band_hi": band_hi,
        "counts": dict(Counter(f["severity"] for f in flags)),
        "missing": len(missing),
    }


# ------------------------------------------------------------------ retrieval
_STOP = frozenset(
    [
        "the",
        "a",
        "an",
        "of",
        "to",
        "and",
        "or",
        "in",
        "on",
        "for",
        "by",
        "with",
        "is",
        "are",
        "be",
        "shall",
        "will",
        "may",
        "this",
        "that",
        "any",
        "all",
        "as",
        "at",
        "from",
        "it",
        "its",
        "his",
        "her",
        "their",
        "such",
        "said",
    ]
)

_SYNONYMS = {
    "deposit": ["advance", "security", "refund"],
    "leave": ["vacate", "terminate", "termination", "exit", "notice", "lock"],
    "early": ["lock", "before", "expiry"],
    "before": ["lock", "expiry"],
    "vacate": ["leave", "terminate", "notice"],
    "increase": ["escalation", "revise", "enhance", "hike"],
    "hike": ["increase", "escalation", "revise"],
    "fire": ["terminate", "deactivate", "termination"],
    "fired": ["terminate", "deactivate"],
    "blocked": ["deactivate", "suspend"],
    "pay": ["payment", "payout", "salary", "fee"],
    "repair": ["repairs", "maintenance"],
    "quit": ["resign", "terminate", "notice"],
    "pet": ["pets", "animals"],
    "guest": ["guests", "visitors"],
    "sublet": ["sub-let", "assign", "sublease"],
}


# Hindi keywords -> English retrieval terms, so offline Q&A works for Hindi questions too.
_HINDI_TERMS = {
    "किराय": "rent",
    "डिपॉज़िट": "deposit security refund",
    "डिपॉजिट": "deposit security refund",
    "जमा": "deposit",
    "छोड़": "leave vacate terminate lock notice",
    "खाली": "vacate",
    "नोटिस": "notice",
    "बढ़": "increase revise",
    "मरम्मत": "repairs maintenance",
    "बिजली": "electricity",
    "पानी": "water",
    "ताला": "lock premises",
    "अकाउंट": "account deactivate suspend",
    "बंद": "deactivate suspend terminate",
    "कमाई": "payout earnings payment",
    "कटौती": "deduct withhold penalties",
    "जुर्माना": "penalty penalties",
    "दुर्घटना": "accident injury insurance",
    "बीमा": "insurance",
    "बॉन्ड": "bond service liquidated damages",
    "प्रतियोगी": "competitor compete competing",
    "सैलरी": "salary",
    "वेतन": "salary",
    "सर्टिफ़िकेट": "certificates original",
    "विवाद": "disputes arbitrator",
    "अदालत": "court jurisdiction",
    "लॉक": "lock",
    "इस्तीफ़": "resign notice",
    "नौकरी": "employment leave resign",
}


def _expand_hindi(text: str) -> str:
    return text + " " + " ".join(v for k, v in _HINDI_TERMS.items() if k in text)


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]+", text.lower()) if t not in _STOP and len(t) > 2]


def retrieve(question: str, clauses: list[Clause], k: int = 4) -> list[tuple[Clause, float]]:
    q = _tokens(_expand_hindi(question))
    q += [s for t in list(q) for s in _SYNONYMS.get(t, [])]
    docs = [_tokens(c.heading + " " + c.text) for c in clauses]
    n = len(docs) or 1
    df = Counter(t for d in docs for t in set(d))
    avg = sum(len(d) for d in docs) / n
    scored = []
    for c, d in zip(clauses, docs, strict=True):
        tf = Counter(d)
        s = 0.0
        for t in set(q):
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(d) / max(avg, 1)))
        # prefix match for stems (terminat~ termination)
        for t in set(q):
            if t not in tf and len(t) > 5 and any(w.startswith(t[:6]) for w in tf):
                s += 0.5
        if s > 0:
            scored.append((c, s))
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


# ------------------------------------------------------------------ orchestrator
def analyse(clauses: list[Clause]) -> dict:
    text = " ".join(c.text for c in clauses)
    doc_type, type_scores = classify(text)
    facts = key_facts(clauses, doc_type)
    flags = find_flags(clauses, doc_type, facts)
    missing = missing_protections(clauses, doc_type)
    return {
        "doc_type": doc_type,
        "type_scores": type_scores,
        "facts": facts,
        "flags": flags,
        "missing": missing,
        "urgent": urgency(text),
        "score": score(flags, missing),
    }
