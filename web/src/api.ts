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
