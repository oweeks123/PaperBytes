/* PaperBytes demo UI — plain vanilla JS, no build step.
   Calls the FastAPI backend on the same origin (served from /ui), so no CORS. */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

let token = localStorage.getItem("pb_token") || null;
function authHeaders() {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** GET a JSON endpoint with query params. Throws on non-2xx with the detail. */
async function apiGet(path, params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== "" && v !== null && v !== undefined)
  );
  const url = qs.toString() ? `${path}?${qs}` : path;
  const res = await fetch(url, { headers: authHeaders() });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
  return body;
}

/** Non-GET JSON request (POST/PATCH/DELETE) with auth + optional body. */
async function api(method, path, body) {
  const opts = { method, headers: { ...authHeaders() } };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

/* ---------------------------------------------------------------- tabs --- */
$$(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    $$(".tab").forEach((t) => t.classList.toggle("is-active", t === tab));
    const name = tab.dataset.tab;
    $$(".tabpane").forEach((p) => p.classList.toggle("is-active", p.id === `tab-${name}`));
    if (name === "reading") loadReadingList($("#reading-search").value.trim());
  })
);

/* ------------------------------------------------- geo / tier / ads --- */
let geoInfo = null;
let user = null; // logged-in practitioner (or null)
let currentTier = "free"; // derived: user.tier when logged in, else "free"
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

/* ---- account / session ---- */
function tierLabel(t) {
  return t === "paid" ? "Paid" : t === "free_registered" ? "Free (registered)" : "Free";
}

function openTabFromHash() {
  const nav = document.querySelector(".tabs");
  if (nav && nav.hidden) return; // no tabs for non-paid tiers
  const name = location.hash.replace("#", "");
  const tab = name && document.querySelector(`.tab[data-tab="${name}"]`);
  if (tab) tab.click();
}

function afterAuthChange() {
  currentTier = user ? user.tier : "free";
  renderAccount();
  updateAds();
  updateTierNote();
  updateNav();
  if (lastArticle) $("#home-article").innerHTML = renderHomeArticle(lastArticle);
  openTabFromHash();
}

function setSession(u) {
  user = u;
  token = u.token;
  localStorage.setItem("pb_token", token);
  afterAuthChange();
}

function clearSession() {
  user = null;
  token = null;
  localStorage.removeItem("pb_token");
  afterAuthChange();
}

async function restoreSession() {
  if (!token) return afterAuthChange();
  try {
    user = await apiGet("/auth/me");
  } catch {
    token = null;
    localStorage.removeItem("pb_token");
  }
  afterAuthChange();
}

function renderAccount() {
  const el = $("#account");
  if (!el) return;
  if (!user) {
    el.innerHTML = `<button class="btn ghost small" id="acct-open">Register / sign in</button>`;
    $("#acct-open").onclick = openAuthModal;
    return;
  }
  const upgrade = user.tier === "free_registered" ? `<button class="btn small" id="acct-upgrade">Upgrade to paid</button>` : "";
  const downgrade = user.tier === "paid" ? `<button class="btn ghost small" id="acct-downgrade">Downgrade</button>` : "";
  el.innerHTML =
    `<span class="acct-email" title="${esc(user.email)}">${esc(user.email)}</span>` +
    `<span class="acct-tier ${esc(user.tier)}">${tierLabel(user.tier)}</span>` +
    upgrade + downgrade +
    `<button class="btn ghost small" id="acct-signout">Sign out</button>`;
  const up = $("#acct-upgrade");
  if (up) up.onclick = async () => setSession(await api("POST", "/auth/upgrade"));
  const dn = $("#acct-downgrade");
  if (dn) dn.onclick = async () => setSession(await api("POST", "/auth/downgrade"));
  $("#acct-signout").onclick = clearSession;
}

/* ---- auth modal ---- */
function openAuthModal() {
  $("#auth-error").textContent = "";
  $("#auth-modal").hidden = false;
  $("#auth-email").focus();
}
function closeAuthModal() {
  $("#auth-modal").hidden = true;
}
$("#auth-cancel").onclick = closeAuthModal;
$("#auth-modal").addEventListener("click", (e) => {
  if (e.target.id === "auth-modal") closeAuthModal();
});
$("#auth-submit").onclick = async () => {
  const email = $("#auth-email").value.trim();
  const professional_registration = $("#auth-reg").value.trim();
  const err = $("#auth-error");
  err.textContent = "";
  try {
    const u = await api("POST", "/auth/register", { email, professional_registration });
    closeAuthModal();
    setSession(u);
  } catch (e) {
    err.textContent = e.message;
  }
};

/* ---- nav visibility: tabs (Home + Reading list) show for paid only ---- */
function updateNav() {
  const nav = document.querySelector(".tabs");
  const paid = currentTier === "paid";
  if (nav) nav.hidden = !paid;
  // Free / free-registered tiers have only the Home view — keep it visible.
  if (!paid) {
    $$(".tab").forEach((t) => t.classList.toggle("is-active", t.dataset.tab === "home"));
    $$(".tabpane").forEach((p) => p.classList.toggle("is-active", p.id === "tab-home"));
  }
}

async function downloadPdfWith(pmid, reflection) {
  const res = await fetch(`/articles/${encodeURIComponent(pmid)}/summary.pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
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
async function downloadPdf(pmid) {
  const ta = document.getElementById("reflection-input");
  return downloadPdfWith(pmid, ta ? ta.value : null);
}
window.downloadPdf = downloadPdf;

/* ---- paid: add-to-reading-list + reading-list tab ---- */
async function addToReadingList(pmid) {
  const ta = document.getElementById("reflection-input");
  try {
    await api("POST", "/reading-list", { pubmed_id: pmid, reflection: ta ? ta.value : null });
    const btn = document.getElementById("add-list-btn");
    if (btn) {
      btn.textContent = "✓ Added to reading list";
      btn.disabled = true;
    }
  } catch (err) {
    alert("Could not add: " + err.message);
  }
}
window.addToReadingList = addToReadingList;

function readingCard(it) {
  const meta = [it.journal && `<b>${esc(it.journal)}</b>`, `PMID ${esc(it.pubmed_id)}`, it.updated_at ? `updated ${esc(it.updated_at.slice(0, 10))}` : null]
    .filter(Boolean).join(" · ");
  return `<article class="card">
    <h3><a href="${esc(it.pubmed_url)}" target="_blank" rel="noreferrer">${esc(it.title)}</a></h3>
    <div class="sub">${meta}</div>
    <div class="summary">${esc(it.summary)}</div>
    <div class="reflection">
      <label>Your reflection <span class="muted">(stored)</span></label>
      <textarea class="reflist-input" data-pmid="${esc(it.pubmed_id)}">${esc(it.reflection || "")}</textarea>
    </div>
    <div class="home-actions">
      <button class="btn small" onclick="saveReflection('${esc(it.pubmed_id)}')">Save reflection</button>
      <button class="btn ghost small" onclick="downloadReadingPdf('${esc(it.pubmed_id)}')">⬇ PDF</button>
      <button class="btn ghost small danger" onclick="removeReading('${esc(it.pubmed_id)}')">Remove</button>
    </div>
  </article>`;
}

async function loadReadingList(q) {
  const meta = $("#reading-meta");
  const out = $("#reading-results");
  meta.className = "meta";
  meta.textContent = "Loading…";
  out.innerHTML = "";
  try {
    const items = await apiGet("/reading-list", q ? { q } : {});
    meta.textContent = `${items.length} item${items.length === 1 ? "" : "s"}${q ? ` matching “${esc(q)}”` : ""}.`;
    out.innerHTML = items.length
      ? items.map(readingCard).join("")
      : `<div class="empty">Nothing saved yet. Open a paper on Home and click “Add to reading list”.</div>`;
  } catch (err) {
    meta.className = "meta err";
    meta.textContent = `Error: ${err.message}`;
  }
}

async function saveReflection(pmid) {
  const ta = document.querySelector(`.reflist-input[data-pmid="${pmid}"]`);
  if (!ta) return;
  try {
    await api("PATCH", `/reading-list/${encodeURIComponent(pmid)}`, { reflection: ta.value });
    ta.classList.add("saved");
    setTimeout(() => ta.classList.remove("saved"), 1200);
  } catch (err) {
    alert("Could not save: " + err.message);
  }
}
async function downloadReadingPdf(pmid) {
  const ta = document.querySelector(`.reflist-input[data-pmid="${pmid}"]`);
  return downloadPdfWith(pmid, ta ? ta.value : null);
}
async function removeReading(pmid) {
  try {
    await api("DELETE", `/reading-list/${encodeURIComponent(pmid)}`);
    loadReadingList($("#reading-search").value.trim());
  } catch (err) {
    alert("Could not remove: " + err.message);
  }
}
window.saveReflection = saveReflection;
window.downloadReadingPdf = downloadReadingPdf;
window.removeReading = removeReading;

$("#reading-form").addEventListener("submit", (e) => {
  e.preventDefault();
  loadReadingList($("#reading-search").value.trim());
});

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
      ? "stored when you add to your reading list; also included in your PDF"
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
      ${currentTier === "paid" ? `<button class="btn" id="add-list-btn" onclick="addToReadingList('${esc(a.pmid)}')">★ Add to reading list</button>` : ""}
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

/* ------------------------------------------------------------- startup --- */
restoreSession(); // restore login -> sets tier, account widget, reading tab
loadHealth();
loadGeo(); // country flag + ad policy
loadRandom(); // free-tier home: show a random appraised paper on load
