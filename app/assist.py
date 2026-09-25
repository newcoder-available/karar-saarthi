"""High-level features. Each one: rules engine first, Gemini on top, verified,
with a complete offline fallback so every feature works without an API key."""

from __future__ import annotations

import re

from . import engine, gcp, kb, llm
from .parsing import Clause

TYPE_LABEL = {
    "rental": ("Rental / tenancy agreement", "किराया एग्रीमेंट"),
    "gig": ("Gig / platform partner agreement", "गिग / प्लेटफ़ॉर्म पार्टनर एग्रीमेंट"),
    "employment": ("Offer letter / employment contract", "ऑफ़र लेटर / नौकरी का कॉन्ट्रैक्ट"),
    "other": ("Legal document", "क़ानूनी दस्तावेज़"),
}
COUNTERPARTY = {"rental": "landlord", "gig": "platform", "employment": "HR team", "other": "other party"}

FACT_LABELS = {
    "monthly_rent": ("Monthly rent", "मासिक किराया"),
    "security_deposit": ("Security deposit", "सिक्योरिटी डिपॉज़िट"),
    "term": ("Term", "अवधि"),
    "lock_in": ("Lock-in", "लॉक-इन"),
    "notice_period": ("Notice period", "नोटिस पीरियड"),
    "escalation": ("Rent increase", "किराया बढ़ोतरी"),
    "late_interest_pm": ("Late-payment interest", "देरी पर ब्याज"),
    "salary_ctc": ("Annual CTC", "सालाना CTC"),
    "jurisdiction": ("Courts / seat", "अदालत / स्थान"),
}


def inr(v: float) -> str:
    n = int(round(v))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        s = head + "," + tail
    return "₹" + s


def fact_rows(facts: dict, lang: str) -> list[dict]:
    rows = []
    for key, (en, hi) in FACT_LABELS.items():
        f = facts.get(key)
        if not f:
            continue
        v = f.get("value")
        if key in ("monthly_rent", "salary_ctc") and isinstance(v, (int, float)):
            shown = inr(v)
        elif key == "security_deposit":
            parts = []
            if f.get("value"):
                parts.append(inr(f["value"]))
            if f.get("months_of_rent"):
                m = f["months_of_rent"]
                parts.append(
                    f"{int(m) if float(m).is_integer() else m} × rent"
                    if lang != "hi"
                    else f"{int(m) if float(m).is_integer() else m} महीने का किराया"
                )
            shown = " · ".join(parts)
        elif key == "late_interest_pm":
            pct = f"{v:g}"
            shown = f"{pct}% / month" if lang != "hi" else f"{pct}% प्रति माह"
        else:
            shown = str(v)
        rows.append({"key": key, "label": hi if lang == "hi" else en, "value": shown, "clause": f.get("clause")})
    return rows


def _offline_overview(analysis: dict, lang: str) -> tuple[str, list[str]]:
    t = analysis["doc_type"]
    label = TYPE_LABEL[t][1 if lang == "hi" else 0]
    flags = analysis["flags"]
    highs = [f for f in flags if f["severity"] == "high"]
    rows = fact_rows(analysis["facts"], lang)
    facts_line = "; ".join(f"{r['label']}: {r['value']}" for r in rows[:5])
    if lang == "hi":
        overview = f"यह एक {label} लगता है। {facts_line + '। ' if facts_line else ''}हमें {len(highs)} गंभीर और {len(flags) - len(highs)} अन्य बातें मिलीं जिन पर ध्यान देना चाहिए।"
        points = _points(flags)
    else:
        overview = f"This looks like a {label.lower()}. {facts_line + '. ' if facts_line else ''}We found {len(highs)} serious and {len(flags) - len(highs)} other points worth your attention before you sign."
        points = _points(flags)
    return overview, points


def _points(flags: list[dict]) -> list[str]:
    """One bullet per distinct issue, citing every clause where it appears."""
    grouped: dict[str, list[str]] = {}
    for f in flags:
        if f["clause_id"] and f["severity"] in ("high", "medium"):
            grouped.setdefault(f["title"], []).append(f["clause_id"])
    return [f"{title} " + " ".join(f"[{c}]" for c in ids) for title, ids in list(grouped.items())[:6]]


# ------------------------------------------------------------------ analyse
def analyse(clauses: list[Clause], lang: str = "en", use_ai: bool = True) -> dict:
    a = engine.analyse(clauses)
    cl = [c.to_dict() for c in clauses]
    ai = llm.enrich(cl, a, lang) if use_ai else None
    if ai:
        a["flags"] = sorted(
            a["flags"] + ai["extra_flags"],
            key=lambda f: (kb.SEVERITY_ORDER[f["severity"]], int((f["clause_id"] or "C999")[1:])),
        )
        a["score"] = engine.score(a["flags"], a["missing"])
        overview, points, parties = ai["overview"], ai["key_points"], ai["parties"]
        mode, guard = "gemini", ai["guardrail"]
    else:
        overview, points = _offline_overview(a, lang)
        parties, mode, guard = [], "rules", {}
    if not overview:
        overview, points = _offline_overview(a, lang)
    for f in a["flags"]:
        f["explain"] = (f["explain_hi"] or f["explain_en"]) if lang == "hi" else (f["explain_en"] or f["explain_hi"])
    for m in a["missing"]:
        m["text"] = m["label_hi"] if lang == "hi" else m["label"]
    a["score"]["label"] = a["score"]["band_hi"] if lang == "hi" else a["score"]["band"]
    return {
        **a,
        "doc_label": TYPE_LABEL[a["doc_type"]][1 if lang == "hi" else 0],
        "fact_rows": fact_rows(a["facts"], lang),
        "overview": overview,
        "key_points": points,
        "parties": parties,
        "clauses": cl,
        "mode": mode,
        "guardrail": guard,
        "disclaimer": kb.DISCLAIMER[lang],
        "legal_aid": kb.LEGAL_AID[lang] if a["urgent"] else [],
    }


# ------------------------------------------------------------------ ask
_OUTCOME_Q = re.compile(r"\b(will i win|can i win|should i sign|is it legal to sue|sue|case against|chances)\b", re.I)


def ask(question: str, clauses: list[dict], doc_type: str, flags: list[dict], lang: str = "en") -> dict:
    cl = [Clause(**c) for c in clauses]
    hits = engine.retrieve(question, cl, k=4)
    hit_dicts = [c.to_dict() for c, _ in hits]
    note = None
    if _OUTCOME_Q.search(question):
        note = (
            "I can't predict outcomes or tell you what to decide, but here is what your document says and what to ask a lawyer."
            if lang != "hi"
            else "मैं नतीजे का अनुमान नहीं लगा सकता या फ़ैसला नहीं बता सकता, लेकिन आपका दस्तावेज़ क्या कहता है और वकील से क्या पूछें, यह बता सकता हूँ।"
        )
    if not hits:
        msg = (
            "Your document doesn't seem to cover this. Ask the other party to add it in writing, or raise it with a lawyer."
            if lang != "hi"
            else "आपके दस्तावेज़ में इसका ज़िक्र नहीं लगता। सामने वाले पक्ष से इसे लिखित में जोड़ने को कहें, या वकील से पूछें।"
        )
        return {"answer": msg, "citations": [], "covered": False, "mode": "rules", "note": note, "sources": []}
    ai = llm.answer(question, hit_dicts, doc_type, lang, flags)
    if ai:
        return {
            **ai,
            "mode": "gemini",
            "note": note,
            "sources": [h for h in hit_dicts if h["id"] in ai["citations"]] or hit_dicts[:2],
        }
    top = hit_dicts[:3]
    flag_by_clause = {f["clause_id"]: f for f in flags}
    parts = []
    for h in top:
        f = flag_by_clause.get(h["id"])
        if lang == "hi":
            parts.append(f"[{h['id']}] में लिखा है: “{h['text'][:280]}”" + (f" — ध्यान दें: {f['explain_hi']}" if f else ""))
        else:
            parts.append(
                f"[{h['id']}] says: “{h['text'][:280]}”" + (f" — Why it matters: {f['explain_en']}" if f else "")
            )
    lead = "The most relevant parts of your document:" if lang != "hi" else "आपके दस्तावेज़ के सबसे ज़रूरी हिस्से:"
    return {
        "answer": lead + "\n\n" + "\n\n".join(parts),
        "citations": [h["id"] for h in top],
        "covered": True,
        "mode": "rules",
        "note": note,
        "sources": top,
        "follow_up": next((flag_by_clause[h["id"]]["ask_lawyer"] for h in top if h["id"] in flag_by_clause), ""),
    }


# ------------------------------------------------------------------ compare
def compare(a_clauses: list[Clause], b_clauses: list[Clause], lang: str = "en") -> dict:
    A, B = engine.analyse(a_clauses), engine.analyse(b_clauses)
    doc_type = A["doc_type"] if A["doc_type"] != "other" else B["doc_type"]
    facts = []
    for key, (en, hi) in FACT_LABELS.items():
        fa, fb = A["facts"].get(key), B["facts"].get(key)
        if not fa and not fb:
            continue
        ra = next((r for r in fact_rows({key: fa}, lang)), None) if fa else None
        rb = next((r for r in fact_rows({key: fb}, lang)), None) if fb else None
        va, vb = (ra or {}).get("value", "—"), (rb or {}).get("value", "—")
        facts.append(
            {
                "label": hi if lang == "hi" else en,
                "a": va,
                "b": vb,
                "changed": va != vb,
                "a_clause": (fa or {}).get("clause"),
                "b_clause": (fb or {}).get("clause"),
            }
        )
    ids_a = {f["rule_id"]: f for f in A["flags"]}
    ids_b = {f["rule_id"]: f for f in B["flags"]}
    fixed = [ids_a[r] for r in ids_a if r not in ids_b]
    new = [ids_b[r] for r in ids_b if r not in ids_a]
    still = [ids_b[r] for r in ids_b if r in ids_a and ids_b[r]["severity"] != kb.INFO]
    miss_a = {m["id"] for m in A["missing"]}
    miss_b = {m["id"] for m in B["missing"]}
    diff = {
        "doc_type": doc_type,
        "score": {"a": A["score"], "b": B["score"]},
        "facts": facts,
        "fixed_in_b": [_brief(f) for f in fixed],
        "new_in_b": [_brief(f) for f in new],
        "in_both": [_brief(f) for f in still],
        "protections_added_in_b": [m["label"] for m in A["missing"] if m["id"] not in miss_b],
        "protections_lost_in_b": [m["label"] for m in B["missing"] if m["id"] not in miss_a],
    }
    summary = llm.compare_narrative(diff, lang)
    mode = "gemini" if summary else "rules"
    if not summary:
        better = A["score"]["value"] < B["score"]["value"]
        if lang == "hi":
            summary = (
                f"B में {len(fixed)} जोखिम हटे और {len(new)} नए जुड़े। फ़ेयरनेस स्कोर A: {A['score']['value']}, B: {B['score']['value']}। "
                + ("B आपके लिए ज़्यादा संतुलित है।" if better else "B आपके लिए बेहतर नहीं है — बदलावों को ध्यान से देखें।")
            )
        else:
            summary = (
                f"Version B removes {len(fixed)} risk(s) and adds {len(new)} new one(s). Fairness score moves from "
                f"{A['score']['value']} (A) to {B['score']['value']} (B). "
                + (
                    "B is more balanced for you."
                    if better
                    else "B is not better for you — check the changes carefully."
                )
            )
            if still:
                summary += " Still worth negotiating: " + ", ".join(f["title"].lower() for f in still[:3]) + "."
    return {**diff, "summary": summary, "mode": mode, "disclaimer": kb.DISCLAIMER[lang]}


def _brief(f: dict) -> dict:
    return {"title": f["title"], "severity": f["severity"], "clause_id": f["clause_id"], "rule_id": f["rule_id"]}


# ------------------------------------------------------------------ lawyer prep pack
DOCS_TO_BRING = {
    "rental": [
        "Signed agreement (all pages) and any earlier versions",
        "Rent payment proofs (bank statements / UPI screenshots)",
        "Deposit payment receipt",
        "Photos/video of the flat's condition at move-in",
        "All WhatsApp/email messages with the landlord",
        "Electricity/water bills in your name, if any",
    ],
    "gig": [
        "Screenshots of the partner agreement / T&Cs version you accepted",
        "Weekly payout statements and rate cards",
        "Deactivation or penalty notices received",
        "Chat logs with support, ticket numbers",
        "Your partner ID and e-Shram UAN (if registered)",
    ],
    "employment": [
        "Offer letter and appointment letter",
        "Salary slips and bank statements",
        "Bond / service agreement",
        "Resignation email and acknowledgement",
        "Any HR policy or handbook referred to",
    ],
    "other": ["The document (all pages)", "Payment proofs", "All related messages and emails"],
}
DOCS_TO_BRING_HI = {
    "rental": [
        "साइन किया हुआ एग्रीमेंट (सभी पन्ने)",
        "किराया भुगतान के सबूत (बैंक स्टेटमेंट / UPI स्क्रीनशॉट)",
        "डिपॉज़िट की रसीद",
        "घर में आते समय की फ़ोटो/वीडियो",
        "मकान मालिक से WhatsApp/ईमेल बातचीत",
        "बिजली/पानी के बिल (अगर आपके नाम पर हों)",
    ],
    "gig": [
        "आपने जो T&C स्वीकार की उसके स्क्रीनशॉट",
        "हफ़्तेवार पेआउट स्टेटमेंट और रेट कार्ड",
        "डिएक्टिवेशन या जुर्माने के नोटिस",
        "सपोर्ट से चैट और टिकट नंबर",
        "पार्टनर ID और e-Shram UAN (अगर रजिस्टर्ड हैं)",
    ],
    "employment": [
        "ऑफ़र लेटर और अपॉइंटमेंट लेटर",
        "सैलरी स्लिप और बैंक स्टेटमेंट",
        "बॉन्ड / सर्विस एग्रीमेंट",
        "इस्तीफ़े का ईमेल और जवाब",
        "HR पॉलिसी या हैंडबुक",
    ],
    "other": ["दस्तावेज़ (सभी पन्ने)", "भुगतान के सबूत", "संबंधित सभी मैसेज और ईमेल"],
}


def prep_pack(analysis: dict, lang: str = "en", use_ai: bool = True) -> dict:
    t = analysis["doc_type"]
    flags = analysis["flags"]
    serious = [f for f in flags if f["severity"] in ("high", "medium")]
    questions = []
    for f in serious:
        if f["ask_lawyer"] not in questions:
            questions.append(f["ask_lawyer"])
    for m in analysis.get("missing", []):
        questions.append(
            f"The document says nothing about: {m['label'].lower()}. What applies by default, and should I ask for it in writing?"
        )
    asks = [f["negotiate"] for f in serious if f["source"] != "ai-verified"][:5]
    cp = COUNTERPARTY.get(t, "other party")
    msg = llm.draft_message(t, cp, asks, lang) if (use_ai and asks) else None
    if not msg:
        if lang == "hi":
            msg = (
                "नमस्ते [Name] जी,\n\nएग्रीमेंट भेजने के लिए धन्यवाद। साइन करने से पहले मैं कुछ बदलाव चाहूँगा/चाहूँगी:\n"
                + "\n".join(f"{i + 1}. {a}" for i, a in enumerate(asks))
                + "\n\nये बदलाव हम दोनों के लिए स्पष्टता लाएंगे। क्या हम इस पर बात कर सकते हैं?\n\nधन्यवाद,\n[आपका नाम]"
            )
        else:
            msg = (
                "Hi [Name],\n\nThanks for sharing the agreement. Before I sign, I'd like to request a few changes:\n"
                + "\n".join(f"{i + 1}. {a}" for i, a in enumerate(asks))
                + "\n\nI think these make things clearer for both of us. Could we discuss?\n\nThanks,\n[Your name]"
            )
    options = {
        "en": [
            {
                "title": "Negotiate before signing",
                "detail": "Send the draft message below. Ask for every change to be written into the agreement, not promised verbally.",
            },
            {
                "title": "Sign, but protect yourself",
                "detail": "Fill or strike all blanks, initial every page, keep a signed copy, pay by bank/UPI, and photograph the property or record the terms you accepted.",
            },
            {
                "title": "Get a quick legal review",
                "detail": "Take this prep pack to a lawyer or free legal aid (NALSA 15100 / your District Legal Services Authority). It will save time and fees.",
            },
            {
                "title": "Walk away",
                "detail": "If the high-risk terms won't change, you may decide the deal isn't worth it.",
            },
        ],
        "hi": [
            {
                "title": "साइन से पहले बातचीत करें",
                "detail": "नीचे दिया मैसेज भेजें। हर बदलाव एग्रीमेंट में लिखवाएं, सिर्फ़ ज़ुबानी वादा न मानें।",
            },
            {
                "title": "साइन करें, पर सुरक्षित रहें",
                "detail": "सभी खाली जगहें भरें या काटें, हर पन्ने पर साइन करें, एक कॉपी रखें, भुगतान बैंक/UPI से करें, और फ़ोटो/रिकॉर्ड रखें।",
            },
            {
                "title": "जल्दी क़ानूनी सलाह लें",
                "detail": "यह प्रेप पैक वकील या मुफ़्त क़ानूनी सहायता (NALSA 15100 / ज़िला विधिक सेवा प्राधिकरण) के पास ले जाएं।",
            },
            {"title": "डील छोड़ दें", "detail": "अगर गंभीर शर्तें नहीं बदलतीं, तो आप यह डील न करने का फ़ैसला ले सकते हैं।"},
        ],
    }[lang]
    return {
        "title": ("Lawyer prep pack — " if lang != "hi" else "वकील प्रेप पैक — ")
        + TYPE_LABEL[t][1 if lang == "hi" else 0],
        "situation": analysis.get("overview", ""),
        "facts": fact_rows(analysis["facts"], lang),
        "top_concerns": [
            {
                "title": f["title"],
                "clause_id": f["clause_id"],
                "severity": f["severity"],
                "why": f["explain_hi"] if lang == "hi" and f["explain_hi"] else f["explain_en"] or f["explain_hi"],
                "law": f["law"],
            }
            for f in serious[:8]
        ],
        "questions": questions[:10],
        "documents": (DOCS_TO_BRING_HI if lang == "hi" else DOCS_TO_BRING)[t],
        "options": options,
        "message": msg,
        "counterparty": cp,
        "legal_aid": kb.LEGAL_AID[lang],
        "disclaimer": kb.DISCLAIMER[lang],
    }


# ------------------------------------------------------------------ localisation
def base_lang(lang: str) -> str:
    """Language the content is generated in before any machine translation."""
    return "hi" if lang == "hi" else "en"


def _collect(obj, paths: list[tuple], keys: set[str], skip: tuple[str, ...] = ()) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in skip:
                continue
            if k in keys and isinstance(v, str) and v.strip():
                paths.append((obj, k))
            elif k in keys and isinstance(v, list) and all(isinstance(x, str) for x in v):
                for i, x in enumerate(v):
                    if x.strip():
                        paths.append((v, i))
            else:
                _collect(v, paths, keys)
    elif isinstance(obj, list):
        for v in obj:
            _collect(v, paths, keys)


TRANSLATABLE = {
    "overview",
    "key_points",
    "title",
    "explain",
    "text",
    "label",
    "negotiate",
    "ask_lawyer",
    "disclaimer",
    "legal_aid",
    "doc_label",
    "answer",
    "note",
    "follow_up",
    "summary",
    "situation",
    "why",
    "questions",
    "documents",
    "detail",
    "message",
    "value_label",
}
_SKIP_PARENTS = ("clauses", "sources")


def localise(result: dict, lang: str) -> dict:
    """Machine-translate user-facing strings with Cloud Translation for languages beyond en/hi.

    For Hindi, only English-only fields (flag titles) are translated. Clause text is never translated,
    so citations always point at the user's original wording.
    """
    if lang == "en":
        return result
    keys = {"title"} if lang == "hi" else TRANSLATABLE
    paths: list[tuple] = []
    _collect(result, paths, keys, skip=_SKIP_PARENTS)
    if not paths:
        return result
    translated = gcp.translate([p[0][p[1]] for p in paths], lang)
    if translated is None:
        if lang != "hi":
            result["translation_note"] = "Translation service unavailable — showing English."
        return result
    for (container, key), text in zip(paths, translated, strict=True):
        container[key] = text
    result["translated_to"] = gcp.LANGUAGES[lang]["name"]
    return result
