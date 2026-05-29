/**
 * Tiny fetch wrapper that always carries cookies and parses JSON.
 *
 * For 4xx/5xx, throws an Error whose message is the parsed `detail` field
 * (or the status text).
 */

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const resp = await fetch(path, {
    method,
    headers,
    body: payload,
    credentials: "include",
  });
  const text = await resp.text();
  const data = text ? safeJSON(text) : null;
  if (!resp.ok) {
    const detail = (data && (data.detail || data.message)) || resp.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data as T;
}

function safeJSON(t: string): any {
  try {
    return JSON.parse(t);
  } catch {
    return null;
  }
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
};

// ---- types reused across components ----

export interface Me {
  user_id: string;
  org_id: string;
  org_name: string;
  org_type: "farmer" | "agronomist";
  email: string;
  name: string | null;
}

export interface Farm {
  id: string;
  name: string;
  client_name: string | null;
  contact_email: string | null;
  notes: string | null;
}

export interface Field {
  id: string;
  farm_id: string;
  name: string;
  crop: string;
  acres: number | null;
  centroid_lat: number | null;
  centroid_lon: number | null;
  planting_date: string | null;
  variety: string | null;
}

export interface Scout {
  id: string;
  field_id: string;
  status: "in_progress" | "complete" | "failed";
  started_at: string;
  completed_at: string | null;
  summary: string | null;
  notes: string | null;
}

export interface Identification {
  id: string;
  rank: number;
  taxon_scientific: string;
  taxon_common: string | null;
  lifecycle_stage: string;
  confidence: number;
  features: string[];
  evidence: string;
}

export interface PhotoWithIds {
  photo_id: string;
  thumb_path: string;
  sha256: string;
  uploaded_at: string;
  identifications: Identification[];
}

export interface ScoutDetail {
  scout: Scout;
  photos: PhotoWithIds[];
}

export interface Application {
  id: string;
  field_id: string;
  applied_at: string;
  pest_target: string | null;
  product_name: string;
  active_ingredient: string | null;
  moa_class: "IRAC" | "FRAC" | "HRAC" | null;
  moa_group: string | null;
  rate: string | null;
  units: string | null;
  rei_hours: number | null;
  phi_days: number | null;
  outcome: string | null;
  notes: string | null;
}

export interface SprayWindow {
  open: string;
  close: string;
  reason: string;
}

export interface ChemicalRec {
  product: string;
  active_ingredient: string;
  moa_class: "IRAC" | "FRAC" | "HRAC";
  moa_group: string;
  rotation_rationale: string;
  rei_hours: number;
  phi_days: number;
}

export interface AltControl {
  category: "biological" | "cultural" | "mechanical";
  name: string;
  summary: string;
  kb_link: string;
}

export interface RecCitation {
  chunk_id: number;
  quote: string;
}

export interface RecResult {
  action: "no_action" | "monitor" | "scout_again" | "treat";
  pest_focus: string;
  threshold_context: string;
  spray_window: SprayWindow | null;
  chemical: ChemicalRec | null;
  alternatives: AltControl[];
  plain_english: string;
  confidence: "high" | "medium" | "low";
  citations: RecCitation[];
}

export interface RecResponse {
  id: string;
  scout_id: string;
  result: RecResult;
  model_used: string;
  prompt_version: string;
  latency_ms: number;
  created_at: string;
}

export interface DailyForecast {
  date: string;
  provider: string;
  t_high_f: number | null;
  t_low_f: number | null;
  rain_in: number | null;
  rain_probability: number | null;
  wind_mph: number | null;
  wind_gust_mph: number | null;
  humidity_pct: number | null;
}

export interface SprayWindowDay {
  date: string;
  label: "good" | "marginal" | "poor";
  wind_mph: number | null;
  rain_probability: number | null;
  reason: string;
}

export interface FieldWeather {
  field_id: string;
  coords: { lat: number; lon: number; is_default: boolean };
  fetched_at: string | null;
  forecasts: DailyForecast[];
  spray_windows: SprayWindowDay[];
}
