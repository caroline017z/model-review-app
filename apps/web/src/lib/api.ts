/**
 * 38DN API Client — typed wrappers around the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

// --- Types ---

export interface CandidateProject {
  id: string;
  name: string;
  dc: number;
  developer: string;
  state: string;
  utility: string;
  program: string;
  toggled_on: boolean;
  suggested: boolean;
  proj_number: number | null;
  col_letter: string;
  dev_sibling: boolean;
}

export interface UploadResponse {
  model_id: string;
  filename: string;
  project_count: number;
  projects: CandidateProject[];
}

export interface ReviewResponse {
  projects: ProjectPayload[];
  portfolio: PortfolioPayload;
}

export interface ProjectPayload {
  name: string;
  sub: string;
  projNumber: number | null;
  developer: string;
  state: string;
  utility: string;
  program: string;
  verdict: "CLEAN" | "REVIEW" | "REWORK REQUIRED";
  irrPct: number;
  nppPerW: number;
  equityK: number;
  leverageScale: number;
  sponsorFraction: number;
  kpis: Record<string, string>;
  findings: Finding[];
  variance: { labels: string[]; x: number[]; txt: string[]; colors: string[] };
  stack: { model: number[]; bible: number[]; illustrative?: boolean; assumptions?: Record<string, unknown> };
  cashflow: { opCF: number[]; taxBn: number[]; terminal: number[] };
  tornado: { labels: string[]; lo: number[]; hi: number[] };
  wrappedEpcComponents: { label: string; value: number }[];
  references: {
    bibleHeader: string;
    bible: { k: string; v: string; s?: string }[];
    marketHeader: string;
    market: { k: string; v: string; s?: string }[];
    marketMatched: boolean;
    opex: { k: string; v: string; s?: string }[];
  };
  rateComp1: Record<string, unknown>;
  propertyTax: Record<string, unknown>;
  fullMapping?: BibleMappingCategory[];
}

export interface BibleMappingRow {
  row: number;
  label: string;
  unit: string;
  expected: string | number | null;
  actual: string | number | null;
  status: "OK" | "OFF" | "OUT" | "MISSING" | "REVIEW";
  source: string;
  tol: number | null;
  range: [number, number] | null;
}

export interface BibleMappingCategory {
  category: string;
  rows: BibleMappingRow[];
}

export interface Finding {
  field: string;
  short: string;
  bible: string;
  model: string;
  delta: number | null;
  deltaUnit: string;
  impact: number | null;
  status: "OFF" | "OUT" | "MISSING" | "REVIEW";
  source: string;
}

export interface PortfolioPayload {
  off: number;
  out: number;
  missing: number;
  review: number;
  count: number;
  totalMw: number;
  reviewed: number;
  pending: number;
  modelName: string;
  bibleLabel: string;
  loadedDate: string;
  reviewer: string;
  heatmap: { projects: string[]; fields: string[]; z: number[][] };
  constants: {
    irrPctPerCent: number;
    calibrationSponsorFraction: number;
    haircutImpactPerPct: number;
    opexNpvFactor: number;
    opexTermYears: number;
  };
}

// --- API Functions ---

export async function uploadModel(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/models/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${await res.text()}`);
  return res.json();
}

export async function runReview(
  modelId: string,
  projectIds?: string[],
  modelLabel?: string,
): Promise<ReviewResponse> {
  return apiFetch("/api/review", {
    method: "POST",
    body: JSON.stringify({
      model_id: modelId,
      project_ids: projectIds,
      model_label: modelLabel || "Model",
    }),
  });
}

export async function downloadWalk(
  m1Id: string,
  m2Id: string,
  m1Label: string,
  m2Label: string,
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/walk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ m1_id: m1Id, m2_id: m2Id, m1_label: m1Label, m2_label: m2Label }),
  });
  if (!res.ok) throw new Error(`Walk failed: ${await res.text()}`);
  return res.blob();
}

export async function exportReview(body: {
  model_label: string;
  reviewer: string;
  bible_label: string;
  projects: unknown[];
}): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Export failed: ${await res.text()}`);
  return res.blob();
}

export async function getBenchmarks() {
  return apiFetch<{ benchmarks: Record<string, unknown>; overrides: Record<string, unknown> }>(
    "/api/benchmarks",
  );
}
