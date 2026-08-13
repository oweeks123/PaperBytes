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
loadHealth();
$("#search-form").dispatchEvent(new Event("submit")); // run a default search on load
