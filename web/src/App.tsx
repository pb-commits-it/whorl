import { useCallback, useState } from "react";

type Kind = "egg" | "larva" | "nymph" | "adult" | "damage_only" | "disease" | "unknown";

interface Candidate {
  scientific_name: string;
  common_name: string;
  lifecycle_stage: Kind;
  confidence: number;
  visible_features: string[];
  evidence: "organism" | "damage_only";
}

interface VisionResult {
  candidates: Candidate[];
  image_quality: "good" | "marginal" | "poor";
  notes: string;
}

interface UploadResult {
  photo_id: string;
  stored_path: string;
  thumb_path: string;
  sha256: string;
  width: number;
  height: number;
  bytes: number;
  vision: VisionResult;
  model_used: string;
}

const CROPS = ["corn", "soybeans", "wheat", "sorghum", "alfalfa", "other"];
const STATES = ["KS", "NE", "IA", "MO", "OK", "other"];

function confColor(c: number): string {
  if (c >= 0.8) return "#34d399";
  if (c >= 0.6) return "#fbbf24";
  return "#f87171";
}

export default function App() {
  const [crop, setCrop] = useState("corn");
  const [state, setState] = useState("KS");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const upload = useCallback(
    async (file: File) => {
      setBusy(true);
      setError(null);
      setResult(null);
      setPreview(URL.createObjectURL(file));
      try {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("crop", crop);
        fd.append("state", state);
        const resp = await fetch("/api/photos", { method: "POST", body: fd });
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(`${resp.status}: ${text}`);
        }
        const data = (await resp.json()) as UploadResult;
        setResult(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [crop, state],
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (file) upload(file);
    },
    [upload],
  );

  const onPick = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) upload(file);
    },
    [upload],
  );

  return (
    <div className="app">
      <header>
        <div className="brand">
          <span className="dot" /> whorl
        </div>
        <span className="tag">v0.1 — it identifies</span>
      </header>

      <main>
        <div className="controls">
          <label>
            <span>Crop</span>
            <select value={crop} onChange={(e) => setCrop(e.target.value)}>
              {CROPS.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label>
            <span>State</span>
            <select value={state} onChange={(e) => setState(e.target.value)}>
              {STATES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
        </div>

        <div
          className={`drop ${busy ? "busy" : ""}`}
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
        >
          {preview && <img src={preview} alt="preview" className="preview" />}
          {!preview && (
            <div className="hint">
              <b>Drop a field photo here</b>
              or
              <label className="picker">
                {" pick a file"}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={onPick}
                />
              </label>
            </div>
          )}
          {busy && <div className="status">analyzing…</div>}
        </div>

        {error && <div className="error">{error}</div>}

        {result && (
          <section className="result">
            <h2>Candidates</h2>
            {result.vision.candidates.length === 0 && (
              <p className="empty">
                No candidates returned. Image quality:{" "}
                <b>{result.vision.image_quality}</b>.
              </p>
            )}
            <div className="cards">
              {result.vision.candidates.map((c, i) => (
                <div
                  key={i}
                  className="card"
                  style={{ borderLeftColor: confColor(c.confidence) }}
                >
                  <div className="row1">
                    <span className="sci">{c.scientific_name}</span>
                    <span className="conf">
                      {Math.round(c.confidence * 100)}%
                    </span>
                  </div>
                  <div className="row2">
                    <span className="common">{c.common_name}</span>
                    <span className="stage">{c.lifecycle_stage}</span>
                  </div>
                  {c.visible_features.length > 0 && (
                    <div className="feats">
                      {c.visible_features.join(" · ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="notes">
              <span className="k">model</span>
              <span className="v">{result.model_used}</span>
              <span className="k">image quality</span>
              <span className="v">{result.vision.image_quality}</span>
              {result.vision.notes && (
                <>
                  <span className="k">notes</span>
                  <span className="v">{result.vision.notes}</span>
                </>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
