/* Karar-Sarthi front-end. No framework and no HTML-string injection of user or model data:
   every dynamic string is inserted with textContent to rule out XSS. */
"use strict";

const state = { analysis: null, lang: "en", langs: [], theme: "light" };

const I18N = {
  hi: {
    skip: "मुख्य सामग्री पर जाएं", tagline: "साइन करने से पहले अपना एग्रीमेंट समझें", language: "भाषा", bigger: "A+ बड़ा टेक्स्ट",
    disclaimer_short: "यह टूल दस्तावेज़ को आसान भाषा में समझाता है। यह क़ानूनी जानकारी है, क़ानूनी सलाह नहीं। मुफ़्त क़ानूनी सहायता: NALSA 15100।",
    tab_understand: "🔍 1 · समझें", tab_compare: "⚖️ 2 · तुलना करें", tab_prep: "📋 3 · वकील के लिए तैयारी", tab_about: "ℹ️ यह कैसे काम करता है",
    h_upload: "किराया एग्रीमेंट, गिग कॉन्ट्रैक्ट या ऑफ़र लेटर जांचें",
    upload_help: "PDF, Word फ़ाइल या फ़ोटो अपलोड करें, या टेक्स्ट पेस्ट करें। आधार, PAN, फ़ोन और ईमेल AI तक पहुँचने से पहले छिपा दिए जाते हैं, और कुछ भी सेव नहीं होता।",
    upload_label: "दस्तावेज़ अपलोड करें", file_hint: "PDF, DOCX, TXT या साफ़ फ़ोटो। अधिकतम 5 MB।", try_sample: "या सैंपल आज़माएं",
    paste_label: "या टेक्स्ट पेस्ट करें", use_ai: "आसान सारांश के लिए Gemini इस्तेमाल करें", analyse: "✨ यह दस्तावेज़ समझाएं",
    h_summary: "आसान शब्दों में", read_aloud: "🔊 पढ़कर सुनाएं", h_score: "निष्पक्षता जांच", h_facts: "मुख्य शर्तें",
    score_hint: "मिली समस्याओं की संख्या और गंभीरता पर आधारित। यह एक गाइड है, क़ानूनी राय नहीं।",
    h_flags: "इन क्लॉज़ को ध्यान से देखें", all: "सभी", high: "गंभीर", medium: "जांचें", low: "मामूली / जानकारी",
    h_missing: "आपके दस्तावेज़ में यह नहीं है", h_ask: "अपने दस्तावेज़ के बारे में पूछें", your_question: "आपका सवाल",
    ask_ph: "जैसे: क्या मैं 11 महीने से पहले घर छोड़ सकता हूँ?", ask: "पूछें", h_clauses: "पूरा दस्तावेज़, क्लॉज़ के हिसाब से",
    h_feedback: "क्या यह मददगार था?", yes: "👍 हाँ", no: "👎 नहीं", h_compare: "दो वर्ज़न की तुलना करें",
    compare_help: "जैसे मकान मालिक का ड्राफ़्ट बनाम बदला हुआ ड्राफ़्ट, या दो नौकरी के ऑफ़र।",
    doc_a: "दस्तावेज़ A (मूल)", doc_b: "दस्तावेज़ B (बदला हुआ)", or_paste: "या टेक्स्ट पेस्ट करें",
    compare_sample: "सैंपल लोड करें: ड्राफ़्ट बनाम बदला हुआ एग्रीमेंट", compare: "⚖️ तुलना करें", h_cmp_sum: "क्या बदला",
    term: "शर्त", fixed: "✓ B में ठीक हुआ", new_risk: "✗ B में नया", still: "! दोनों में बाक़ी",
    h_prep: "वकील प्रेप पैक", prep_help: "वकील या मुफ़्त क़ानूनी सहायता के पास ले जाने के लिए एक पेज: आपकी स्थिति, जोखिम वाले क्लॉज़, पूछने के सवाल, साथ ले जाने वाले काग़ज़, आपके विकल्प और बदलाव मांगने का मैसेज।",
    prep_empty: "पहले स्टेप 1 में दस्तावेज़ समझें।", make_prep: "प्रेप पैक बनाएं", download: "⬇ डाउनलोड (.md)", print: "🖨 प्रिंट",
    disclaimer: "करार सारथी दस्तावेज़ समझने के लिए सामान्य क़ानूनी जानकारी देता है। यह क़ानूनी सलाह नहीं है। क़ानून हर राज्य में अलग हैं और बदलते रहते हैं; फ़ैसला लेने से पहले योग्य वकील या मुफ़्त क़ानूनी सहायता (NALSA 15100) से बात करें।",
    working: "पढ़ रहे हैं और जांच रहे हैं…", evidence: "आपके दस्तावेज़ में", why: "क़ानूनी संदर्भ", ask_lawyer: "वकील से पूछें",
    negotiate: "क्या मांगें", clause: "क्लॉज़", urgent_title: "यह एक क़ानूनी नोटिस या समय-सीमा वाला दस्तावेज़ लगता है",
    urgent_body: "इसमें समय-सीमा हो सकती है। जल्द से जल्द वकील या मुफ़्त क़ानूनी सहायता से बात करें:",
    thanks: "धन्यवाद!", ai_on: "Gemini चालू", ai_off: "ऑफ़लाइन नियम मोड",
    q1: "क्या मैं जल्दी घर छोड़ सकता हूँ?", q2: "मेरी डिपॉज़िट कब लौटेगी?", q3: "किराया कब बढ़ सकता है?",
    g1: "क्या मेरा अकाउंट बिना कारण बंद हो सकता है?", g2: "मेरी कमाई से कटौती कब हो सकती है?", g3: "दुर्घटना होने पर क्या होगा?",
    e1: "अगर मैं 2 साल से पहले छोड़ूं तो क्या होगा?", e2: "नोटिस पीरियड कितना है?", e3: "क्या मैं प्रतियोगी कंपनी में जा सकता हूँ?",
  },
  en: {
    working: "Reading and checking…", evidence: "In your document", why: "Legal reference", ask_lawyer: "Ask a lawyer",
    negotiate: "What to ask for", clause: "Clause", urgent_title: "This looks like a legal notice or a document with a deadline",
    urgent_body: "There may be a time limit. Speak to a lawyer or free legal aid as soon as possible:", thanks: "Thank you!",
    ai_on: "Gemini on", ai_off: "Offline rules mode",
    p_situation: "Situation", p_terms: "Key terms", p_concerns: "Top concerns", p_questions: "Questions to ask the lawyer",
    p_docs: "Documents to bring", p_options: "Your options", p_message: "Message asking for changes", p_help: "Free legal help", copy: "📋 Copy message",
    q1: "Can I leave before the term ends?", q2: "When will I get my deposit back?", q3: "When can the rent be increased?",
    g1: "Can my account be blocked without a reason?", g2: "When can they deduct from my earnings?", g3: "What happens if I have an accident?",
    e1: "What happens if I leave before 2 years?", e2: "What is my notice period?", e3: "Can I join a competitor later?",
  },
};
const DEFAULTS = {};
const SEV_LABEL = { en: { high: "Serious", medium: "Check", low: "Minor", info: "Info" }, hi: { high: "गंभीर", medium: "जांचें", low: "मामूली", info: "जानकारी" } };

const $ = (sel) => document.querySelector(sel);
const t = (key) => (I18N[state.lang === "hi" ? "hi" : "en"][key] ?? I18N.en[key] ?? DEFAULTS[key] ?? key);

/** Create an element safely. Children may be strings (inserted as text) or nodes. */
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of children.flat()) if (c !== null && c !== undefined) el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return el;
}

/** Turn "... [C4] ..." into text with clickable citation buttons. */
function withCites(text) {
  const frag = document.createDocumentFragment();
  String(text || "").split(/(\[C\d+\])/g).forEach((part) => {
    const m = part.match(/^\[(C\d+)\]$/);
    frag.append(m ? h("button", { type: "button", class: "cite", "aria-label": `${t("clause")} ${m[1]}`, onclick: () => showClause(m[1]) }, m[1]) : document.createTextNode(part));
  });
  return frag;
}

function showClause(id) {
  const det = $("#h-clauses").closest("details");
  det.open = true;
  const li = document.getElementById(`clause-${id}`);
  if (!li) return;
  li.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
  li.focus({ preventScroll: true });
  li.classList.add("flash");
  setTimeout(() => li.classList.remove("flash"), 1600);
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const isJson = (res.headers.get("content-type") || "").includes("json");
  const body = isJson ? await res.json() : await res.blob();
  if (!res.ok) throw new Error((isJson && body.error) || `Request failed (${res.status})`);
  return body;
}

function setBusy(el, on, msg) {
  el.hidden = !on;
  el.textContent = on ? msg || t("working") : "";
}

function showError(el, err) {
  el.hidden = !err;
  el.textContent = err ? String(err.message || err) : "";
  if (err) el.focus?.();
}

/* ------------------------------------------------------------ Theme toggler */
function initTheme() {
  let savedTheme;
  try { savedTheme = localStorage.getItem("ks-theme"); } catch { /* ignore */ }
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  state.theme = savedTheme || (prefersDark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", state.theme);
  updateThemeIcon();

  const toggleBtn = $("#theme-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      state.theme = state.theme === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", state.theme);
      try { localStorage.setItem("ks-theme", state.theme); } catch { /* ignore */ }
      updateThemeIcon();
    });
  }
}

function updateThemeIcon() {
  const icon = $("#theme-icon");
  if (icon) icon.textContent = state.theme === "dark" ? "☀️" : "🌙";
}

/* ------------------------------------------------------------ i18n chrome */
function applyChrome() {
  const dict = I18N[state.lang === "hi" ? "hi" : "en"];
  document.documentElement.lang = state.lang;
  document.documentElement.dir = state.lang === "ur" ? "rtl" : "ltr";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (!(key in DEFAULTS)) DEFAULTS[key] = el.textContent;
    el.textContent = dict[key] ?? DEFAULTS[key];
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.dataset.i18nPlaceholder;
    if (!(key + "_ph" in DEFAULTS)) DEFAULTS[key + "_ph"] = el.placeholder;
    el.placeholder = dict[key] ?? DEFAULTS[key + "_ph"];
  });
}

/* ------------------------------------------------------------ tabs (WAI-ARIA pattern) */
function initTabs() {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const select = (tab, focus = true) => {
    tabs.forEach((x) => {
      const on = x === tab;
      x.setAttribute("aria-selected", on);
      x.tabIndex = on ? 0 : -1;
      document.getElementById(x.getAttribute("aria-controls")).hidden = !on;
    });
    if (focus) tab.focus();
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", (e) => {
      const map = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 };
      if (e.key in map) { e.preventDefault(); select(tabs[(map[e.key] + tabs.length) % tabs.length]); }
    });
  });
  state.selectTab = (id) => select(document.getElementById(id), false);
}

/* ------------------------------------------------------------ analyse */
async function analyse(e) {
  e.preventDefault();
  const err = $("#analyse-error");
  showError(err, null);
  const fd = new FormData();
  const file = $("#file").files[0];
  const text = $("#text").value.trim();
  if (!file && text.length < 40) return showError(err, state.lang === "hi" ? "कृपया दस्तावेज़ अपलोड करें या टेक्स्ट पेस्ट करें।" : "Please upload a document or paste its text.");
  if (file) fd.append("file", file); else fd.append("text", text);
  fd.append("lang", state.lang);
  fd.append("ai", $("#use-ai").checked);
  const btn = $("#analyse-btn");
  btn.disabled = true;
  setBusy($("#progress"), true);
  try {
    state.analysis = await api("/api/analyse", { method: "POST", body: fd });
    renderAnalysis(state.analysis);
    $("#prep-btn").disabled = false;
    $("#prep-empty").hidden = true;
    $("#h-summary").focus?.();
  } catch (ex) {
    showError(err, ex);
  } finally {
    btn.disabled = false;
    setBusy($("#progress"), false);
  }
}

function renderAnalysis(a) {
  $("#results").hidden = false;

  const urgent = $("#urgent");
  urgent.replaceChildren();
  urgent.hidden = !(a.urgent && a.urgent.length);
  if (!urgent.hidden) {
    urgent.append(h("h2", {}, "⚠ " + t("urgent_title")), h("p", {}, t("urgent_body")), h("ul", { class: "bullets" }, a.legal_aid.map((x) => h("li", {}, x))));
  }

  $("#doc-label").textContent = a.doc_label;
  $("#overview").replaceChildren(withCites(a.overview));
  $("#key-points").replaceChildren(...a.key_points.map((p) => h("li", {}, withCites(p))));
  $("#score-meter").value = a.score.value;
  $("#score-meter").textContent = `${a.score.value}/100`;
  $("#score-text").textContent = `${a.score.value}/100 — ${a.score.label}`;

  $("#facts tbody").replaceChildren(...a.fact_rows.map((r) =>
    h("tr", {}, h("th", { scope: "row" }, r.label), h("td", {}, r.value, " ", r.clause ? withCites(`[${r.clause}]`) : ""))));
  if (!a.fact_rows.length) $("#facts tbody").append(h("tr", {}, h("td", { colspan: 2 }, "—")));

  const modeText = a.mode === "gemini" ? `Explained with Gemini${a.guardrail && a.guardrail.ai_flags_rejected ? ` · ${a.guardrail.ai_flags_rejected} unverified AI claim(s) discarded` : ""}` : "Explained by the rules engine (offline mode).";
  $("#mode-note").textContent = [modeText, a.translated_to ? `Machine-translated to ${a.translated_to}.` : "", a.translation_note || "", a.cached ? "Loaded from cache." : ""].filter(Boolean).join(" ");

  renderFlags("all");
  const miss = a.missing || [];
  $("#missing-wrap").hidden = !miss.length;
  $("#missing").replaceChildren(...miss.map((m) => h("li", {}, m.text || m.label)));

  $("#clauses").replaceChildren(...a.clauses.map((c) => h("li", { id: `clause-${c.id}`, tabindex: "-1" }, h("span", { class: "cid" }, c.id), c.text)));
  const red = Object.entries(a.redactions || {}).map(([k, v]) => `${v} ${k}`).join(", ");
  $("#redaction-note").textContent = red ? `Masked before analysis: ${red}.` : "No personal identifiers detected.";

  const qs = { rental: ["q1", "q2", "q3"], gig: ["g1", "g2", "g3"], employment: ["e1", "e2", "e3"] }[a.doc_type] || ["q1"];
  $("#suggested").replaceChildren(...qs.map((k) => h("button", { type: "button", class: "chip", onclick: () => { $("#question").value = t(k); ask(); } }, t(k))));
  $("#chat").replaceChildren();
  document.querySelector('.filter [data-sev="all"]').click();
}

function renderFlags(sev) {
  const a = state.analysis;
  if (!a) return;
  const sevLabels = SEV_LABEL[state.lang === "hi" ? "hi" : "en"];
  const list = a.flags.filter((f) => sev === "all" || f.severity === sev || (sev === "low" && f.severity === "info"));
  $("#flags").replaceChildren(...list.map((f) => h("li", { class: `flag ${f.severity}` },
    h("h3", {}, h("span", { class: `sev ${f.severity}` }, sevLabels[f.severity]), f.source === "ai-verified" ? h("span", { class: "sev ai" }, "AI · verified quote") : null, f.title,
      f.clause_id ? withCites(`[${f.clause_id}]`) : null),
    h("p", {}, f.explain),
    f.evidence ? h("blockquote", { "aria-label": t("evidence") }, f.evidence) : null,
    h("details", {}, h("summary", {}, `${t("negotiate")} · ${t("ask_lawyer")} · ${t("why")}`),
      h("p", {}, h("strong", {}, t("negotiate") + ": "), f.negotiate),
      h("p", {}, h("strong", {}, t("ask_lawyer") + ": "), f.ask_lawyer),
      h("p", { class: "law" }, h("strong", {}, t("why") + ": "), f.law)))));
  if (!list.length) $("#flags").append(h("li", { class: "hint" }, "—"));
}

/* ------------------------------------------------------------ ask */
async function ask(e) {
  e?.preventDefault();
  const q = $("#question").value.trim();
  if (q.length < 3 || !state.analysis) return;
  const chat = $("#chat");
  chat.append(h("div", { class: "msg user" }, q));
  $("#question").value = "";
  const pending = h("div", { class: "msg bot" }, t("working"));
  chat.append(pending);
  try {
    const a = state.analysis;
    const r = await api("/api/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, clauses: a.clauses, doc_type: a.doc_type, flags: a.flags.map(({ clause_id, title, law, explain_en, explain_hi, ask_lawyer }) => ({ clause_id, title, law, explain_en, explain_hi, ask_lawyer })), lang: state.lang }),
    });
    pending.replaceChildren(r.note ? h("span", { class: "note" }, r.note) : "", withCites(r.answer),
      r.follow_up ? h("span", { class: "note" }, "\n" + t("ask_lawyer") + ": " + r.follow_up) : "");
  } catch (ex) {
    pending.textContent = ex.message;
  }
}

/* ------------------------------------------------------------ compare */
async function compare(e) {
  e.preventDefault();
  const err = $("#compare-error");
  showError(err, null);
  const fd = new FormData();
  for (const s of ["a", "b"]) {
    const f = $(`#file-${s}`).files[0];
    const tx = $(`#text-${s}`).value.trim();
    if (!f && tx.length < 40) return showError(err, `Please add document ${s.toUpperCase()}.`);
    if (f) fd.append(`file_${s}`, f); else fd.append(`text_${s}`, tx);
  }
  fd.append("lang", state.lang);
  setBusy($("#compare-progress"), true);
  try {
    const r = await api("/api/compare", { method: "POST", body: fd });
    $("#compare-results").hidden = false;
    $("#cmp-summary").textContent = r.summary;
    $("#cmp-scores").replaceChildren(
      h("div", { class: "score-box" }, "A", h("strong", {}, `${r.score.a.value}/100`), r.score.a.band),
      h("div", { class: "score-box" }, "B", h("strong", {}, `${r.score.b.value}/100`), r.score.b.band));
    $("#cmp-facts tbody").replaceChildren(...r.facts.map((f) => h("tr", { class: f.changed ? "changed" : "" },
      h("th", { scope: "row" }, f.label + (f.changed ? " •" : "")), h("td", {}, f.a), h("td", {}, f.b))));
    const li = (x) => h("li", {}, x.title);
    const fill = (id, arr) => $(id).replaceChildren(...(arr.length ? arr.map(li) : [h("li", {}, "—")]));
    fill("#cmp-fixed", r.fixed_in_b); fill("#cmp-new", r.new_in_b); fill("#cmp-both", r.in_both);
    $("#h-cmp-sum").focus?.();
  } catch (ex) {
    showError(err, ex);
  } finally {
    setBusy($("#compare-progress"), false);
  }
}

/* ------------------------------------------------------------ prep pack */
async function makePrep() {
  if (!state.analysis) return;
  setBusy($("#prep-progress"), true);
  try {
    const { clauses, ...analysis } = state.analysis;
    const p = await api("/api/prep", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ analysis, lang: state.lang, ai: $("#use-ai").checked }) });
    state.prep = p;
    const sec = (title, ...kids) => h("section", {}, h("h3", {}, title), ...kids);
    $("#prep").replaceChildren(
      h("h2", { id: "prep-title" }, p.title),
      p.situation ? sec(t("p_situation"), h("p", {}, withCites(p.situation))) : "",
      p.facts.length ? sec(t("p_terms"), h("ul", { class: "bullets" }, p.facts.map((f) => h("li", {}, `${f.label}: ${f.value}`)))) : "",
      sec(t("p_concerns"), h("ol", { class: "bullets" }, p.top_concerns.map((c) => h("li", {}, h("strong", {}, `${c.title} `), c.clause_id ? withCites(`[${c.clause_id}]`) : "", h("br"), c.why, h("br"), h("span", { class: "law" }, c.law))))),
      sec(t("p_questions"), h("ol", { class: "bullets" }, p.questions.map((q) => h("li", {}, q)))),
      sec(t("p_docs"), h("ul", { class: "bullets" }, p.documents.map((d) => h("li", {}, "☐ " + d)))),
      sec(t("p_options"), h("ul", { class: "bullets" }, p.options.map((o) => h("li", {}, h("strong", {}, o.title + ": "), o.detail)))),
      sec(`${t("p_message")} (${p.counterparty})`, h("pre", { id: "prep-message" }, p.message),
        h("button", { type: "button", class: "btn ghost", onclick: copyMessage }, t("copy")), h("span", { id: "copy-status", role: "status" })),
      sec(t("p_help"), h("ul", { class: "bullets" }, p.legal_aid.map((x) => h("li", {}, x)))),
      h("p", { class: "hint" }, p.disclaimer));
    $("#prep").hidden = false;
    $("#prep-download").hidden = false;
    $("#prep-print").hidden = false;
    $("#prep-title").setAttribute("tabindex", "-1");
    $("#prep-title").focus();
  } catch (ex) {
    $("#prep-progress").hidden = false;
    $("#prep-progress").textContent = ex.message;
    return;
  }
  setBusy($("#prep-progress"), false);
}

async function copyMessage() {
  try { await navigator.clipboard.writeText(state.prep.message); $("#copy-status").textContent = " Copied"; }
  catch { $("#copy-status").textContent = " Select the text and copy manually"; }
}

function prepMarkdown(p) {
  const L = [`# ${p.title}`, "", p.situation, "", "## Key terms", ...p.facts.map((f) => `- ${f.label}: ${f.value}`), "",
    "## Top concerns", ...p.top_concerns.map((c, i) => `${i + 1}. **${c.title}** (${c.clause_id || "—"}) — ${c.why}\n   _${c.law}_`), "",
    "## Questions to ask the lawyer", ...p.questions.map((q, i) => `${i + 1}. ${q}`), "",
    "## Documents to bring", ...p.documents.map((d) => `- [ ] ${d}`), "",
    "## Options", ...p.options.map((o) => `- **${o.title}:** ${o.detail}`), "",
    `## Message to the ${p.counterparty}`, "", "```", p.message, "```", "", "## Free legal help", ...p.legal_aid.map((x) => `- ${x}`), "", `> ${p.disclaimer}`];
  return L.join("\n");
}

function downloadPrep() {
  const blob = new Blob([prepMarkdown(state.prep)], { type: "text/markdown" });
  const a = h("a", { href: URL.createObjectURL(blob), download: "karar-sarthi-prep-pack.md" });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/* ------------------------------------------------------------ read aloud: Cloud TTS, device voice fallback */
let audio;
async function readAloud() {
  const a = state.analysis;
  if (!a) return;
  const text = [a.overview, ...a.key_points].join(". ").replace(/\[C\d+\]/g, "");
  if (audio && !audio.paused) { audio.pause(); return; }
  if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
  try {
    const blob = await api("/api/speak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: text.slice(0, 3000), lang: state.lang }) });
    audio = new Audio(URL.createObjectURL(blob));
    await audio.play();
  } catch {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = (state.langs.find((l) => l.code === state.lang) || {}).tts || "en-IN";
    u.rate = 0.95;
    speechSynthesis.speak(u);
  }
}

/* ------------------------------------------------------------ init */
async function init() {
  initTheme();
  applyChrome();
  initTabs();
  try { state.lang = localStorage.getItem("ks-lang") || "en"; } catch { /* storage unavailable */ }

  const [health, langs, samples, kbRows] = await Promise.all([api("/api/health"), api("/api/languages"), api("/api/samples"), api("/api/kb")]).catch(() => [{}, [], [], []]);
  state.langs = langs;
  const sel = $("#lang");
  sel.replaceChildren(...langs.map((l) => h("option", { value: l.code }, `${l.native}${l.machine_translated ? " *" : ""}`)));
  sel.value = state.lang;
  sel.addEventListener("change", () => {
    state.lang = sel.value;
    try { localStorage.setItem("ks-lang", state.lang); } catch { /* ignore */ }
    applyChrome();
    if (state.analysis) $("#analyse-form").requestSubmit();
  });
  applyChrome();

  const pill = $("#ai-status");
  pill.textContent = health.ai ? `${t("ai_on")} · ${health.model}` : t("ai_off");
  pill.classList.toggle("on", !!health.ai);

  $("#samples").replaceChildren(...samples.map((s) => h("button", { type: "button", class: "chip", "aria-pressed": "false", onclick: async (ev) => {
    const r = await api(`/api/samples/${s.id}`);
    $("#text").value = r.text; $("#file").value = "";
    document.querySelectorAll("#samples .chip").forEach((c) => c.setAttribute("aria-pressed", c === ev.currentTarget));
  } }, s.label)));

  $("#kb-table tbody").replaceChildren(...kbRows.map((r) => h("tr", {}, h("td", {}, r.title), h("td", {}, r.applies_to.join(", ")), h("td", {}, r.reference))));

  $("#analyse-form").addEventListener("submit", analyse);
  $("#ask-form").addEventListener("submit", ask);
  $("#compare-form").addEventListener("submit", compare);
  $("#compare-sample").addEventListener("click", async () => {
    const [a, b] = await Promise.all([api("/api/samples/rental_one_sided"), api("/api/samples/rental_balanced")]);
    $("#text-a").value = a.text; $("#text-b").value = b.text;
  });
  $("#prep-btn").addEventListener("click", makePrep);
  $("#prep-download").addEventListener("click", downloadPrep);
  $("#prep-print").addEventListener("click", () => window.print());
  $("#speak-summary").addEventListener("click", readAloud);
  document.querySelectorAll(".filter .chip").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".filter .chip").forEach((x) => x.setAttribute("aria-pressed", x === b));
    renderFlags(b.dataset.sev);
  }));
  document.querySelectorAll("[data-helpful]").forEach((b) => b.addEventListener("click", async () => {
    try {
      await api("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ helpful: b.dataset.helpful === "true", doc_type: state.analysis?.doc_type || "other", lang: state.lang }) });
    } catch { /* feedback is best-effort */ }
    $("#feedback-status").textContent = t("thanks");
  }));
  const big = $("#text-size");
  big.addEventListener("click", () => {
    const on = document.documentElement.classList.toggle("large");
    big.setAttribute("aria-pressed", on);
  });
  ["#h-summary", "#h-cmp-sum"].forEach((s) => $(s).setAttribute("tabindex", "-1"));
}

document.addEventListener("DOMContentLoaded", init);
