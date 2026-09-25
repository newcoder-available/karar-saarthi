"""Unit tests for parsing, redaction and the deterministic rules engine."""

import pytest

from app import engine, kb
from app.parsing import extract_text, normalise, split_clauses
from app.privacy import redact


def analyse_text(text: str) -> dict:
    return engine.analyse(split_clauses(redact(normalise(text))[0]))


def rule_ids(result: dict) -> set[str]:
    return {f["rule_id"] for f in result["flags"]}


# ------------------------------------------------------------------ parsing
def test_split_numbered_clauses_gives_stable_ids(one_sided):
    clauses = split_clauses(normalise(one_sided))
    assert [c.id for c in clauses[:3]] == ["C1", "C2", "C3"]
    assert any(c.text.startswith("7. Rent Increase") for c in clauses)


def test_unnumbered_text_splits_by_paragraph():
    clauses = split_clauses("First paragraph about rent.\n\nSecond paragraph about deposit.")
    assert len(clauses) == 2


def test_long_blob_is_chunked_for_precise_citations():
    blob = " ".join(["This is a long sentence about obligations of the tenant."] * 60)
    clauses = split_clauses(blob)
    assert len(clauses) > 1 and all(len(c.text) <= 950 for c in clauses)


def test_extract_text_from_docx(tmp_path):
    import docx

    d = docx.Document()
    d.add_paragraph("1. Rent: Rs. 10,000 per month.")
    path = tmp_path / "a.docx"
    d.save(path)
    assert "Rent" in extract_text("a.docx", path.read_bytes())


def test_normalise_caps_length():
    assert len(normalise("x" * 100_000)) == 60_000


# ------------------------------------------------------------------ privacy
@pytest.mark.parametrize(
    "raw,label",
    [
        ("Aadhaar 2345 6789 0123", "AADHAAR"),
        ("PAN ABCDE1234F", "PAN"),
        ("call 9876543210", "PHONE"),
        ("mail me at a.b@example.com", "EMAIL"),
        ("IFSC HDFC0001234", "IFSC"),
        ("Account No. 123456789012", "ACCOUNT"),
    ],
)
def test_redaction_masks_identifiers(raw, label):
    out, counts = redact(raw)
    assert f"[{label}]" in out and counts[label] == 1


def test_redaction_leaves_money_amounts():
    out, counts = redact("Rent Rs. 25,000 per month")
    assert out == "Rent Rs. 25,000 per month" and counts == {}


# ------------------------------------------------------------------ classification & facts
@pytest.mark.parametrize(
    "fixture,expected", [("one_sided", kb.RENTAL), ("balanced", kb.RENTAL), ("gig", kb.GIG), ("offer", kb.JOB)]
)
def test_classify(fixture, expected, request):
    assert engine.classify(request.getfixturevalue(fixture))[0] == expected


def test_classify_unknown():
    assert engine.classify("Hello world. Nothing legal here.")[0] == "other"


def test_rental_key_facts(one_sided):
    facts = analyse_text(one_sided)["facts"]
    assert facts["monthly_rent"]["value"] == 25000
    assert facts["security_deposit"]["value"] == 150000
    assert facts["security_deposit"]["months_of_rent"] == 6
    assert facts["lock_in"]["value"] == "11 months"
    assert facts["late_interest_pm"]["value"] == 5


def test_notice_period_prefers_termination_clause(balanced):
    assert analyse_text(balanced)["facts"]["notice_period"]["value"] == "1 month"


def test_deposit_months_from_words():
    text = "1. Rent: Rs. 20,000 per month.\n2. Security deposit equal to three months' rent is payable."
    facts = analyse_text(text)["facts"]
    assert facts["security_deposit"]["months_of_rent"] == 3


# ------------------------------------------------------------------ flags
def test_one_sided_rental_flags(one_sided):
    ids = rule_ids(analyse_text(one_sided))
    expected = {
        "R_DEPOSIT_FORFEIT",
        "R_DEPOSIT_CAP",
        "R_RENT_HIKE_ANYTIME",
        "R_SELF_HELP_EVICTION",
        "X_BAR_COURTS",
        "R_ENTRY_NO_NOTICE",
        "R_ALL_REPAIRS_TENANT",
        "X_ONE_SIDED_ARBITRATION",
        "X_HIGH_INTEREST",
        "X_BLANKS",
    }
    assert expected <= ids


def test_balanced_rental_has_no_risk_flags(balanced):
    result = analyse_text(balanced)
    assert all(f["severity"] == kb.INFO for f in result["flags"])
    assert result["score"]["value"] == 100
    assert result["missing"] == []


def test_gig_flags(gig):
    ids = rule_ids(analyse_text(gig))
    assert {
        "G_DEACTIVATE_DISCRETION",
        "G_UNILATERAL_PAYOUT",
        "G_DEDUCTIONS_PENALTIES",
        "X_NON_COMPETE",
        "G_UNLIMITED_INDEMNITY",
        "G_NOT_EMPLOYEE",
    } <= ids


def test_offer_letter_flags(offer):
    ids = rule_ids(analyse_text(offer))
    assert {"E_TRAINING_BOND", "E_ORIGINAL_DOCS", "E_FORFEIT_SALARY", "X_NON_COMPETE", "G_IP_ALL"} <= ids


def test_every_flag_quotes_its_clause(one_sided):
    result = analyse_text(one_sided)
    clauses = {c.id: c.text for c in split_clauses(redact(normalise(one_sided))[0])}
    for f in result["flags"]:
        core = f["evidence"].strip("…").strip()[:40]
        assert core in clauses[f["clause_id"]], f["rule_id"]


def test_structural_repairs_by_owner_is_not_flagged(balanced):
    assert "R_ALL_REPAIRS_TENANT" not in rule_ids(analyse_text(balanced))


def test_flags_sorted_by_severity(one_sided):
    order = [kb.SEVERITY_ORDER[f["severity"]] for f in analyse_text(one_sided)["flags"]]
    assert order == sorted(order)


def test_blank_flag_reported_once(one_sided):
    assert sum(f["rule_id"] == "X_BLANKS" for f in analyse_text(one_sided)["flags"]) == 1


def test_missing_protections_detected():
    result = analyse_text("1. The tenant shall pay rent of Rs. 10,000 per month to the landlord for the premises.")
    ids = {m["id"] for m in result["missing"]}
    assert {"M_DEPOSIT_REFUND", "M_MAINTENANCE", "M_INVENTORY"} <= ids


# ------------------------------------------------------------------ urgency & score
def test_urgency_detects_legal_notice():
    hits = engine.urgency(
        "LEGAL NOTICE. You are required to pay within 15 days of receipt of this notice, failing which legal proceedings will follow."
    )
    assert hits


def test_urgency_ignores_ordinary_agreement(one_sided):
    assert engine.urgency(one_sided) == []


def test_score_bands():
    assert engine.score([], [])["band"] == "Looks balanced"
    high = [{"severity": kb.HIGH}] * 8
    assert engine.score(high, [])["value"] == 0


# ------------------------------------------------------------------ retrieval
def test_retrieve_finds_deposit_clause(one_sided):
    clauses = split_clauses(normalise(one_sided))
    top = engine.retrieve("When will I get my deposit back?", clauses)[0][0]
    assert "Security Deposit" in top.text


def test_retrieve_no_match_returns_empty(one_sided):
    assert engine.retrieve("zzzz qqqq", split_clauses(normalise(one_sided))) == []


# ------------------------------------------------------------------ knowledge base integrity
def test_kb_rules_are_complete():
    ids = [r.id for r in kb.RULES]
    assert len(ids) == len(set(ids))
    for r in kb.RULES:
        assert r.patterns and r.explain_en and r.explain_hi and r.law and r.ask_lawyer and r.negotiate
        assert r.severity in kb.SEVERITY_ORDER
        assert set(r.types) <= set(kb.ANY)


def test_kb_patterns_compile():
    import re

    for r in kb.RULES:
        for p in r.patterns + r.all_of + r.none_of:
            re.compile(p)


def test_retrieve_understands_hindi_questions(gig):
    clauses = split_clauses(normalise(gig))
    top = engine.retrieve("क्या मेरा अकाउंट बिना कारण बंद हो सकता है?", clauses)[0][0]
    assert "Deactivation" in top.text
