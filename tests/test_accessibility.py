"""Accessibility checks.

1. Static checks on the HTML (always run).
2. Full axe-core WCAG 2.1 AA audit in a real browser across every UI state
   (runs when Playwright and axe-core are installed: `npm i axe-core` and
   `pip install playwright`).
"""

import os
import re
import threading
import time
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def _tags():
    c = _Collector()
    c.feed(HTML)
    return c.tags


def test_document_language_and_title():
    assert re.search(r'<html lang="en"', HTML)
    assert "<title>" in HTML


def test_skip_link_targets_main():
    assert 'class="skip-link" href="#main"' in HTML and 'id="main"' in HTML


def test_single_h1():
    assert HTML.count("<h1") == 1


def test_every_form_control_has_a_label():
    tags = _tags()
    label_for = {a.get("for") for t, a in tags if t == "label"}
    for tag, attrs in tags:
        if tag in ("input", "textarea", "select") and attrs.get("type") != "checkbox":
            assert attrs.get("id") in label_for or "aria-label" in attrs, attrs


def test_tabs_follow_aria_pattern():
    tags = _tags()
    tabs = [a for t, a in tags if a.get("role") == "tab"]
    panels = {a["id"] for t, a in tags if a.get("role") == "tabpanel"}
    assert tabs and all(a["aria-controls"] in panels for a in tabs)
    assert "ArrowRight" in JS and "Home" in JS and "End" in JS


def test_live_regions_for_async_updates():
    assert HTML.count('aria-live="polite"') >= 3
    assert 'role="alert"' in HTML


def test_focus_and_motion_preferences():
    assert ":focus-visible" in CSS
    assert "prefers-reduced-motion" in CSS and "prefers-color-scheme: dark" in CSS


def test_touch_targets_are_at_least_40px():
    assert "min-height: 44px" in CSS


def test_no_unsafe_html_injection_in_js():
    assert "innerHTML" not in JS and "insertAdjacentHTML" not in JS and "eval(" not in JS


def test_severity_not_conveyed_by_colour_alone():
    # every severity badge carries a text label
    assert "SEV_LABEL" in JS and "class: `sev ${f.severity}`" in JS


# ------------------------------------------------------------------ browser audit
AXE = Path(os.getenv("AXE_PATH", ROOT / "node_modules" / "axe-core" / "axe.min.js"))


@pytest.fixture(scope="module")
def live_server():
    uvicorn = pytest.importorskip("uvicorn")
    from app.main import app

    config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    yield "http://127.0.0.1:8765"
    server.should_exit = True


@pytest.mark.skipif(not AXE.exists(), reason="axe-core not installed (npm i axe-core)")
def test_axe_wcag_aa_all_states(live_server):
    sync_api = pytest.importorskip("playwright.sync_api")
    axe = AXE.read_text(encoding="utf-8")
    rules = "{runOnly: ['wcag2a','wcag2aa','wcag21aa','best-practice']}"
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        for scheme in ("light", "dark"):
            page = browser.new_page(color_scheme=scheme, bypass_csp=True)
            page.goto(live_server)
            page.wait_for_selector("#samples .chip")

            def audit(state, page=page, scheme=scheme):
                page.add_script_tag(content=axe)
                violations = page.evaluate(f"async () => (await axe.run(document, {rules})).violations.map(v => v.id)")
                assert violations == [], f"{scheme}/{state}: {violations}"

            audit("initial")
            page.click("#samples .chip >> nth=0")
            page.wait_for_function("document.querySelector('#text').value.length > 0")
            page.click("#analyse-btn")
            page.wait_for_selector("#results:not([hidden])")
            audit("results")
            page.click("#tab-prep")
            page.click("#prep-btn")
            page.wait_for_selector("#prep:not([hidden])")
            audit("prep")
            page.click("#tab-compare")
            page.click("#compare-sample")
            page.wait_for_function("document.querySelector('#text-b').value.length > 0")
            page.click("#compare-form button[type=submit]")
            page.wait_for_selector("#compare-results:not([hidden])")
            audit("compare")
        browser.close()
