/* PaperBytes demo UI — plain vanilla JS, no build step.
   Calls the FastAPI backend on the same origin (served from /ui), so no CORS. */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/** GET a JSON endpoint with query params. Throws on non-2xx with the detail. */
async function apiGet(path, params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== "" && v !== null && v !== undefined)
  );
  const url = qs.toString() ? `${path}?${qs}` : path;
  const res = await fetch(url);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
  return body;
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

const pubmedUrl = (pmid) => `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`;

/** Format the PartialDate object returned by /search, or a plain string. */
function fmtDate(d) {
  if (!d) return "";
  if (typeof d === "string") return d;
  const parts = [d.year, d.month, d.day].filter((x) => x != null);
  return parts.join("/");
}

/* ---------------------------------------------------------------- tabs --- */
$$(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    $$(".tab").forEach((t) => t.classList.toggle("is-active", t === tab));
    const name = tab.dataset.tab;
    $$(".tabpane").forEach((p) => p.classList.toggle("is-active", p.id === `tab-${name}`));
  })
);

/* ------------------------------------------------- geo / tier / ads --- */
let geoInfo = null;
let currentTier = "free"; // free | free_registered | paid — set by the switcher
let lastArticle = null;

async function loadGeo() {
  const el = $("#geo");
  try {
    // ?country=US in the page URL previews another country locally.
    const override = new URLSearchParams(location.search).get("country");
    geoInfo = await apiGet("/geo", override ? { country: override } : {});
    el.textContent = `${geoInfo.flag} ${geoInfo.country_name}`;
    el.title = `Detected from IP ${geoInfo.ip} · ad policy: ${geoInfo.ad_policy}`;
  } catch {
    el.textContent = "🏳 unknown";
  }
  updateAds();
}

function updateAds() {
  const slot = $("#ad-slot");
  if (!slot) return;
  const registered = currentTier !== "free";
  const uk = geoInfo && geoInfo.ad_policy === "uk";
  if (registered && uk) {
    slot.className = "ad-slot pharma";
    slot.innerHTML =
      `<span class="ad-label">Advertisement · Pharma / POM — ${esc(geoInfo.country_name)} (placeholder)</span>` +
      `<div class="ad-body">Prescription-only medication advertising slot — registered practitioners, UK rules.</div>`;
  } else {
    slot.className = "ad-slot adsense";
    slot.innerHTML =
      `<span class="ad-label">Advertisement · Google AdSense (placeholder)</span>` +
      `<div class="ad-body">Generic advertising slot.</div>`;
  }
}

function updateTierNote() {
  const n = $("#tier-note");
  if (n) n.textContent = currentTier === "free" ? "" : "Demo: registration simulated (real sign-up in the next phase).";
}

$("#tier-select").addEventListener("change", (e) => {
  currentTier = e.target.value;
  updateAds();
  updateTierNote();
  if (lastArticle) $("#home-article").innerHTML = renderHomeArticle(lastArticle);
});

async function downloadPdf(pmid) {
  const ta = document.getElementById("reflection-input");
  const reflection = ta ? ta.value : null;
  const res = await fetch(`/articles/${encodeURIComponent(pmid)}/summary.pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reflection }),
  });
  if (!res.ok) {
    alert("Could not generate the PDF.");
    return;
  }
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = `paperbytes-${pmid}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
window.downloadPdf = downloadPdf;

/* -------------------------------------------------------------- health --- */
async function loadHealth() {
  const el = $("#health");
  try {
    const h = await apiGet("/");
    el.classList.add("ok");
    el.textContent = `● ${h.model} · ${h.journals} journals · ${h.ncbi_rate_limit}/s`;
  } catch (e) {
    el.classList.add("err");
    el.textContent = `● API unreachable`;
  }
}

/* ------------------------------------------------------- article cards --- */
function pubMedCard(a) {
  const meta = [
    a.journal && `<b>${esc(a.journal)}</b>`,
    fmtDate(a.publication_date),
    a.authors?.length ? `${a.authors.length} author${a.authors.length > 1 ? "s" : ""}` : null,
    a.doi ? `doi:${esc(a.doi)}` : null,
  ].filter(Boolean).join(" · ");

  const pts = (a.publication_types || []).map((p) => `<span class="tag pt">${esc(p)}</span>`).join("");
  const mesh = (a.mesh_terms || [])
    .slice(0, 8)
    .map((m) => `<span class="tag ${m.major_topic ? "major" : ""}">${esc(m.term)}</span>`)
    .join("");
  const abstract = a.abstract ? `<p class="abstract">${esc(a.abstract.slice(0, 320))}${a.abstract.length > 320 ? "…" : ""}</p>` : "";

  return `<article class="card">
    <h3><a href="${pubmedUrl(a.pmid)}" target="_blank" rel="noreferrer">${esc(a.title)}</a></h3>
    <div class="sub">${meta} · PMID ${esc(a.pmid)}</div>
    ${abstract}
    <div class="tags">${pts}${mesh}</div>
  </article>`;
}

function storedCard(a) {
  const meta = [
    a.journal && `<b>${esc(a.journal)}</b>`,
    fmtDate(a.publication_date),
    a.sent ? "sent" : "unsent",
  ].filter(Boolean).join(" · ");
  const specs = (a.ai_specialties || []).map((s) => `<span class="tag pt">${esc(s)}</span>`).join("");
  const summary = a.ai_summary ? `<div class="summary">${esc(a.ai_summary)}</div>` : "";
  return `<article class="card">
    <h3><a href="${esc(a.pubmed_url || pubmedUrl(a.pubmed_id))}" target="_blank" rel="noreferrer">${esc(a.title)}</a></h3>
    <div class="sub">${meta} · PMID ${esc(a.pubmed_id)}</div>
    ${summary}
    <div class="tags">${specs}</div>
  </article>`;
}

/* ----------------------------------------------------------- home tab --- */
function outcomesTable(outcomes) {
  if (!outcomes || !outcomes.length) return "";
  const rows = outcomes
    .map(
      (o) => `<tr>
        <td>${esc(o.name)}</td><td>${esc(o.measure || "—")}</td><td>${esc(o.value || "—")}</td>
        <td>${esc(o.confidence_interval || "—")}</td><td>${esc(o.p_value || "—")}</td></tr>`
    )
    .join("");
  return `<h4 class="ap-h">Reported statistics</h4>
    <table class="stats-table">
      <thead><tr><th>Outcome</th><th>Measure</th><th>Value</th><th>95% CI</th><th>p</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
}

function appraisalTable(ap) {
  if (!ap) return "";
  const row = (k, v) => `<tr><th>${k}</th><td>${esc(v || "—")}</td></tr>`;
  return `<h4 class="ap-h">Critical appraisal</h4>
    <table class="appraisal-table"><tbody>
      ${row("Study design", ap.study_design)}
      ${row("Population", ap.population)}
      ${row("Intervention", ap.intervention)}
      ${row("Comparator", ap.comparator)}
      ${row("Risk of bias", ap.risk_of_bias)}
      ${row("Level of evidence", ap.level_of_evidence)}
      ${row("Limitations", ap.limitations)}
    </tbody></table>
    ${outcomesTable(ap.outcomes)}`;
}

function renderHomeArticle(a) {
  const meta = [
    a.journal && `<b>${esc(a.journal)}</b>`,
    a.publication_date,
    a.authors?.length ? esc(a.authors.slice(0, 6).join(", ")) + (a.authors.length > 6 ? " et al." : "") : null,
    a.doi ? `doi:${esc(a.doi)}` : null,
  ].filter(Boolean).join(" · ");

  const badge = a.cached
    ? `<span class="badge cached">cached</span>`
    : `<span class="badge fresh">freshly appraised</span>`;
  const mockBadge = a.mock ? `<span class="badge mock">MOCK — add AI credits for real appraisal</span>` : "";
  const specs = (a.specialties || []).map((s) => `<span class="tag pt">${esc(s)}</span>`).join("");

  // Reflection box: registered tiers only. Free-registered = transient (PDF only);
  // paid = will be saved with the reading list (next phase).
  const reflectionNote =
    currentTier === "paid"
      ? "saved with your reading list (coming next phase)"
      : "not stored — included in your PDF, discarded on refresh";
  const reflectionBox =
    currentTier === "free"
      ? ""
      : `<div class="reflection">
           <label for="reflection-input">Your reflection <span class="muted">(${reflectionNote})</span></label>
           <textarea id="reflection-input" placeholder="Add a reflection to include in the PDF…"></textarea>
         </div>`;

  return `<article class="card home-card">
    <div class="home-badges">${mockBadge}${badge}${specs}</div>
    <h2><a href="${esc(a.pubmed_url)}" target="_blank" rel="noreferrer">${esc(a.title)}</a></h2>
    <div class="sub">${meta} · PMID ${esc(a.pmid)}</div>
    <div class="summary">${esc(a.summary)}</div>
    ${appraisalTable(a.appraisal)}
    ${reflectionBox}
    <div class="home-actions">
      <button class="btn" onclick="downloadPdf('${esc(a.pmid)}')">⬇ Download summary (PDF)</button>
      <a class="btn ghost" href="${esc(a.pubmed_url)}" target="_blank" rel="noreferrer">View on PubMed</a>
    </div>
  </article>`;
}

async function loadRandom() {
  const out = $("#home-article");
  const btn = $("#home-next");
  btn.disabled = true;
  out.innerHTML = `<div class="spin">Fetching a random paper… new papers are AI-appraised on the fly (a few seconds); seen papers are instant.</div>`;
  try {
    const a = await apiGet("/random", { days_back: 30 });
    lastArticle = a;
    out.innerHTML = renderHomeArticle(a);
  } catch (err) {
    out.innerHTML = `<div class="meta err">Error: ${esc(err.message)}</div>`;
  } finally {
    btn.disabled = false;
  }
}
$("#home-next").addEventListener("click", loadRandom);

/* --------------------------------------------------------- search tab --- */
$("#search-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const meta = $("#search-meta");
  const out = $("#search-results");
  meta.className = "meta";
  meta.textContent = "Searching PubMed…";
  out.innerHTML = "";
  const btn = $("button", f);
  btn.disabled = true;
  try {
    const data = await apiGet("/search", {
      days_back: f.days_back.value,
      date_field: f.date_field.value,
      journal_scope: f.journal_scope.value,
      restrict_humans: f.restrict_humans.checked,
      restrict_english: f.restrict_english.checked,
      limit: f.limit.value,
    });
    meta.innerHTML =
      `Showing <b>${data.returned}</b> of <b>${data.total_count}</b> matches.` +
      `<details class="term-wrap"><summary>Resolved NCBI query</summary>` +
      `<span class="term">${esc(data.resolved_term)}</span></details>`;
    out.innerHTML = data.articles.length
      ? data.articles.map(pubMedCard).join("")
      : `<div class="empty">No articles for these filters. Try widening the window or journal scope.</div>`;
  } catch (err) {
    meta.className = "meta err";
    meta.textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
});

/* --------------------------------------------------------- stored tab --- */
$("#stored-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const meta = $("#stored-meta");
  const out = $("#stored-results");
  meta.className = "meta";
  meta.textContent = "Loading…";
  out.innerHTML = "";
  try {
    const data = await apiGet("/articles", {
      specialty: f.specialty.value.trim(),
      journal: f.journal.value.trim(),
      sent: f.sent.value,
      limit: f.limit.value,
    });
    meta.innerHTML = `<b>${data.total}</b> stored article${data.total === 1 ? "" : "s"} match.`;
    out.innerHTML = data.articles.length
      ? data.articles.map(storedCard).join("")
      : `<div class="empty">No stored articles yet — run <code>POST /fetch</code> (needs PUBMED_EMAIL + ANTHROPIC_API_KEY) to populate the database.</div>`;
  } catch (err) {
    meta.className = "meta err";
    meta.textContent = `Error: ${err.message}`;
  }
});

/* ---------------------------------------------------- specialties tab --- */
async function loadSpecialties() {
  const meta = $("#specialties-meta");
  const out = $("#specialties-results");
  meta.className = "meta";
  meta.textContent = "Loading…";
  out.innerHTML = "";
  try {
    const data = await apiGet("/specialties");
    const entries = Object.entries(data);
    meta.textContent = `${entries.length} specialt${entries.length === 1 ? "y" : "ies"} across stored articles.`;
    out.innerHTML = entries.length
      ? entries.map(([name, n]) => `<span class="chip">${esc(name)}<b>${n}</b></span>`).join("")
      : `<div class="empty">No specialties yet — populate the database via <code>POST /fetch</code> first.</div>`;
  } catch (err) {
    meta.className = "meta err";
    meta.textContent = `Error: ${err.message}`;
  }
}
$("#specialties-refresh").addEventListener("click", loadSpecialties);

/* ------------------------------------------------------------- startup --- */
// Optional ?tier= preset (preview a tier without the switcher).
const _tierParam = new URLSearchParams(location.search).get("tier");
if (_tierParam && ["free", "free_registered", "paid"].includes(_tierParam)) {
  currentTier = _tierParam;
  $("#tier-select").value = _tierParam;
  updateTierNote();
}
loadHealth();
loadGeo(); // country flag + ad policy
loadRandom(); // free-tier home: show a random appraised paper on load
