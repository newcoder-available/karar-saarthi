"""HTTP API tests: behaviour, validation and security controls."""

from app import gcp, main


def post_text(client, text, **extra):
    return client.post("/api/analyse", data={"text": text, **extra})


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_index_served_with_security_headers(client):
    r = client.get("/")
    assert r.status_code == 200 and "<main" in r.text
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_samples(client):
    ids = [s["id"] for s in client.get("/api/samples").json()]
    assert "rental_one_sided" in ids
    assert "RENT AGREEMENT" in client.get("/api/samples/rental_one_sided").json()["text"]
    assert client.get("/api/samples/../../etc/passwd").status_code == 404
    assert client.get("/api/samples/nope").status_code == 404


def test_languages(client):
    langs = {x["code"]: x for x in client.get("/api/languages").json()}
    assert langs["hi"]["machine_translated"] is False and langs["ta"]["machine_translated"] is True


def test_analyse_text(client, one_sided):
    r = post_text(client, one_sided)
    assert r.status_code == 200
    body = r.json()
    assert body["doc_type"] == "rental" and body["mode"] == "rules"
    assert body["redactions"] == {"AADHAAR": 1, "PAN": 1, "PHONE": 1}
    assert "2345 6789 0123" not in str(body)
    assert r.headers["cache-control"] == "no-store"


def test_analyse_is_cached(client, gig):
    first = post_text(client, gig).json()
    second = post_text(client, gig).json()
    assert "cached" not in first and second["cached"] is True


def test_analyse_hindi(client, offer):
    body = post_text(client, offer, lang="hi").json()
    assert body["lang"] == "hi" and "ऑफ़र" in body["doc_label"]


def test_unknown_language_falls_back_to_english(client, offer):
    assert post_text(client, offer, lang="xx").json()["lang"] == "en"


def test_analyse_file_upload(client, one_sided):
    r = client.post("/api/analyse", files={"file": ("rent.txt", one_sided.encode(), "text/plain")})
    assert r.status_code == 200 and r.json()["doc_type"] == "rental"


def test_rejects_short_input(client):
    r = post_text(client, "too short")
    assert r.status_code == 422 and "error" in r.json()


def test_rejects_unsupported_file(client):
    r = client.post("/api/analyse", files={"file": ("x.exe", b"MZ" * 100, "application/octet-stream")})
    assert r.status_code == 415


def test_rejects_oversized_file(client):
    r = client.post("/api/analyse", files={"file": ("big.txt", b"a" * (main.MAX_BYTES + 10), "text/plain")})
    assert r.status_code == 413


def test_corrupt_pdf_gives_friendly_error(client):
    r = client.post("/api/analyse", files={"file": ("bad.pdf", b"%PDF-1.4 garbage", "application/pdf")})
    assert r.status_code == 422 and "garbage" not in r.json()["error"]


def test_image_without_ocr_service(client):
    r = client.post("/api/analyse", files={"file": ("photo.png", b"\x89PNG....", "image/png")})
    assert r.status_code == 422


def test_image_with_ocr(client, monkeypatch, gig):
    monkeypatch.setattr(gcp, "ocr_image", lambda data: gig)
    r = client.post("/api/analyse", files={"file": ("photo.jpg", b"\xff\xd8fake", "image/jpeg")})
    assert r.status_code == 200 and r.json()["doc_type"] == "gig"


def test_ask(client, one_sided):
    a = post_text(client, one_sided).json()
    r = client.post(
        "/api/ask",
        json={
            "question": "When will I get my deposit back?",
            "clauses": a["clauses"],
            "doc_type": "rental",
            "flags": a["flags"],
            "lang": "en",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["citations"] and body["mode"] == "rules"


def test_ask_validates_clause_ids(client):
    r = client.post("/api/ask", json={"question": "What?", "clauses": [{"id": "<script>", "text": "x"}]})
    assert r.status_code == 422


def test_ask_validates_doc_type(client):
    r = client.post("/api/ask", json={"question": "What?", "clauses": [{"id": "C1", "text": "x"}], "doc_type": "evil"})
    assert r.status_code == 422


def test_compare(client, one_sided, balanced):
    r = client.post("/api/compare", data={"text_a": one_sided, "text_b": balanced})
    body = r.json()
    assert r.status_code == 200
    assert body["score"]["b"]["value"] > body["score"]["a"]["value"]
    assert any(f["label"] == "Security deposit" and f["changed"] for f in body["facts"])
    assert body["new_in_b"] == []


def test_prep(client, gig):
    a = post_text(client, gig).json()
    a.pop("clauses")
    r = client.post("/api/prep", json={"analysis": a, "lang": "en"})
    body = r.json()
    assert r.status_code == 200
    assert body["counterparty"] == "platform"
    assert any("15100" in x for x in body["legal_aid"])
    assert "[Name]" in body["message"]


def test_prep_requires_analysis(client):
    assert client.post("/api/prep", json={"analysis": {}}).status_code == 422


def test_speak_unavailable_returns_503(client):
    assert client.post("/api/speak", json={"text": "hello", "lang": "hi"}).status_code == 503


def test_speak_returns_audio(client, monkeypatch):
    monkeypatch.setattr(gcp, "speak", lambda text, lang: b"ID3audio")
    r = client.post("/api/speak", json={"text": "hello", "lang": "hi"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"


def test_feedback_redacts_comment(client, monkeypatch):
    saved = {}
    monkeypatch.setattr(gcp, "save_feedback", lambda entry: saved.update(entry) or True)
    r = client.post("/api/feedback", json={"helpful": True, "doc_type": "rental", "comment": "call me 9876543210"})
    assert r.json() == {"saved": True}
    assert "9876543210" not in saved["comment"]


def test_kb_endpoint(client):
    rows = client.get("/api/kb").json()
    assert any(r["id"] == "X_NON_COMPETE" and "s.27" in r["reference"] for r in rows)


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT", 2)
    codes = [client.post("/api/feedback", json={"helpful": True}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_openapi_docs_available(client):
    assert client.get("/openapi.json").status_code == 200


def test_rate_limit_ignores_spoofed_forwarded_for(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT", 1)
    ok = client.post("/api/feedback", json={"helpful": True}, headers={"x-forwarded-for": "1.1.1.1, 9.9.9.9"})
    spoofed = client.post("/api/feedback", json={"helpful": True}, headers={"x-forwarded-for": "2.2.2.2, 9.9.9.9"})
    assert ok.status_code == 200 and spoofed.status_code == 429
