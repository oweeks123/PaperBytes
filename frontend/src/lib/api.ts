// API client + types + mapping from the /random response to the card model.
// The card intentionally has no forest plot and no rarity tier.

export interface Outcome {
  name: string;
  measure: string | null;
  value: string | null;
  confidence_interval: string | null;
  p_value: string | null;
}

export interface Appraisal {
  study_design: string;
  population: string;
  intervention: string;
  comparator: string;
  outcomes: Outcome[];
  risk_of_bias: string;
  level_of_evidence: string;
  limitations: string;
}

export interface RandomArticle {
  pmid: string;
  title: string;
  journal: string | null;
  authors: string[];
  publication_date: string | null;
  doi: string | null;
  pubmed_url: string;
  abstract: string | null;
  summary: string;
  specialties: string[];
  appraisal: Appraisal;
  cached: boolean;
  mock: boolean;
}

export interface Geo {
  ip: string;
  country_code: string;
  country_name: string;
  flag: string;
  ad_policy: string;
}

export type Tone = 'ink' | 'good' | 'warn' | 'bad';
export interface Pip {
  label: string;
  filled: number;
  tone: Tone;
  value: string;
}
export interface AppraisalRow {
  label: string;
  value: string;
  soft: boolean;
}

export interface CardModel {
  pmid: string;
  title: string;
  journal: string;
  date: string;
  authors: string;
  doi: string;
  url: string;
  specialties: string[];
  design: string;
  levelOfEvidence: string;
  fresh: boolean;
  mock: boolean;
  warnings: string[];
  summaryParagraphs: string[];
  pips: Pip[];
  appraisalRows: AppraisalRow[];
  limitations: string;
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { detail?: string }).detail || `HTTP ${res.status}`);
  return data as T;
}

export const getRandom = (daysBack = 30) => json<RandomArticle>(`/random?days_back=${daysBack}`);
export const getGeo = (country?: string) =>
  json<Geo>(`/geo${country ? `?country=${encodeURIComponent(country)}` : ''}`);

export async function downloadPdf(pmid: string, reflection: string | null = null): Promise<void> {
  const res = await fetch(`/articles/${encodeURIComponent(pmid)}/summary.pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reflection })
  });
  if (!res.ok) throw new Error('Could not generate the PDF');
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement('a');
  a.href = url;
  a.download = `paperbytes-${pmid}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// --- derivations -----------------------------------------------------------
function shortDesign(d: string): string {
  const s = d.toLowerCase();
  if (/systematic review|meta.?analysis/.test(s)) return 'SR / meta-analysis';
  if (/randomi[sz]ed|\brct\b/.test(s)) return 'RCT';
  if (/cohort/.test(s)) return 'Cohort';
  if (/case.?control/.test(s)) return 'Case-control';
  if (/cross.?sectional/.test(s)) return 'Cross-sectional';
  if (/case series|case report/.test(s)) return 'Case series';
  return d.length > 22 ? d.slice(0, 20) + '…' : d;
}

function designRank(design: string): number {
  const d = design.toLowerCase();
  if (/systematic review|meta.?analysis/.test(d)) return 6;
  if (/randomi[sz]ed|\brct\b/.test(d)) return 5;
  if (/cohort/.test(d)) return 4;
  if (/case.?control|cross.?sectional|observational/.test(d)) return 3;
  return 2;
}

function levelInfo(level: string): { filled: number; tone: Tone } {
  const m = level.match(/[1-5]/);
  const n = m ? parseInt(m[0], 10) : 3;
  return { filled: Math.max(1, 7 - n), tone: n <= 2 ? 'good' : n <= 3 ? 'ink' : 'warn' };
}

// The AI's level_of_evidence is sometimes a whole sentence; the gem needs a short
// code. Prefer a CEBM level (1a..5), else a GRADE initial, else a short fallback.
function shortLevel(level: string): string {
  const cebm = level.match(/\b([1-5][a-c]?)\b/i);
  if (cebm) return cebm[1].toLowerCase();
  const grade = level.match(/very low|high|moderate|low/i);
  if (grade) return grade[0][0].toUpperCase();
  const trimmed = level.trim();
  return trimmed.length <= 4 ? trimmed || '—' : trimmed.slice(0, 3) + '…';
}

function robInfo(rob: string): { filled: number; tone: Tone; value: string; warn: string | null } {
  const r = rob.toLowerCase();
  if (/\blow\b/.test(r)) return { filled: 5, tone: 'good', value: 'Low', warn: null };
  if (/high/.test(r)) return { filled: 1, tone: 'bad', value: 'High', warn: 'High risk of bias' };
  if (/unclear|not (detailed|assessed|reported|described)|some concern|no .*assessment/.test(r))
    return { filled: 3, tone: 'warn', value: 'Unclear', warn: 'Risk of bias unclear' };
  return { filled: 3, tone: 'ink', value: 'See notes', warn: null };
}

export function toCard(a: RandomArticle): CardModel {
  const ap = a.appraisal;
  const rob = robInfo(ap.risk_of_bias || '');
  const level = levelInfo(ap.level_of_evidence || '');
  const rank = designRank(ap.study_design || '');

  const warnings: string[] = [];
  if (rob.warn) warnings.push(rob.warn);
  if (ap.outcomes.length && ap.outcomes.every((o) => !o.p_value && !o.confidence_interval))
    warnings.push('Effect estimates limited');

  const authors = a.authors.slice(0, 6).join(', ') + (a.authors.length > 6 ? ' et al.' : '');
  const levelGem = shortLevel(ap.level_of_evidence || '');

  return {
    pmid: a.pmid,
    title: a.title,
    journal: a.journal || '',
    date: a.publication_date || '',
    authors,
    doi: a.doi || '',
    url: a.pubmed_url,
    specialties: a.specialties.slice(0, 4),
    design: ap.study_design || 'Not specified',
    levelOfEvidence: levelGem,
    fresh: !a.cached,
    mock: a.mock,
    warnings,
    summaryParagraphs: a.summary.split(/\n{2,}/).map((s) => s.trim()).filter(Boolean) || [a.summary],
    pips: [
      { label: 'Level of evidence', filled: level.filled, tone: level.tone, value: levelGem },
      { label: 'Study design', filled: rank, tone: rank >= 5 ? 'good' : 'ink', value: shortDesign(ap.study_design || '') },
      { label: 'Risk of bias', filled: rob.filled, tone: rob.tone, value: rob.value },
      { label: 'Outcomes reported', filled: Math.min(6, ap.outcomes.length), tone: 'ink', value: String(ap.outcomes.length) }
    ],
    appraisalRows: [
      { label: 'Population', value: ap.population, soft: false },
      { label: 'Intervention', value: ap.intervention, soft: false },
      { label: 'Comparator', value: ap.comparator, soft: false },
      { label: 'Risk of bias', value: ap.risk_of_bias, soft: true }
    ],
    limitations: ap.limitations || ''
  };
}
