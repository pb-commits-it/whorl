import { useCallback, useEffect, useState } from "react";
import {
  api,
  type Farm,
  type Field,
  type Me,
  type PhotoWithIds,
  type Scout,
  type ScoutDetail,
} from "./api";

interface Props {
  me: Me;
  onLogout: () => void;
}

export default function Dashboard({ me, onLogout }: Props) {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [fieldsByFarm, setFieldsByFarm] = useState<Record<string, Field[]>>({});
  const [selectedField, setSelectedField] = useState<Field | null>(null);
  const [scouts, setScouts] = useState<Scout[]>([]);
  const [activeScoutId, setActiveScoutId] = useState<string | null>(null);
  const [scoutDetail, setScoutDetail] = useState<ScoutDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load farms initially.
  useEffect(() => {
    api
      .get<Farm[]>("/api/farms")
      .then(setFarms)
      .catch((e) => setError(e.message));
  }, []);

  // Whenever a field is selected, load its scouts.
  useEffect(() => {
    if (!selectedField) {
      setScouts([]);
      return;
    }
    api
      .get<Scout[]>(`/api/fields/${selectedField.id}/scouts`)
      .then(setScouts)
      .catch((e) => setError(e.message));
  }, [selectedField]);

  // Whenever an active scout is set, load its detail.
  useEffect(() => {
    if (!activeScoutId) {
      setScoutDetail(null);
      return;
    }
    api
      .get<ScoutDetail>(`/api/scouts/${activeScoutId}`)
      .then(setScoutDetail)
      .catch((e) => setError(e.message));
  }, [activeScoutId]);

  const ensureFieldsLoaded = useCallback(async (farmId: string) => {
    if (fieldsByFarm[farmId]) return;
    try {
      const rows = await api.get<Field[]>(`/api/farms/${farmId}/fields`);
      setFieldsByFarm((prev) => ({ ...prev, [farmId]: rows }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [fieldsByFarm]);

  async function createFarm() {
    const name = prompt(
      me.org_type === "agronomist" ? "Client farm name" : "Farm name",
    );
    if (!name) return;
    try {
      const farm = await api.post<Farm>("/api/farms", { name });
      setFarms((p) => [farm, ...p]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function createField(farmId: string) {
    const name = prompt("Field name (e.g. 'North 80')");
    if (!name) return;
    const crop = prompt(
      "Crop (corn / soybeans / wheat / sorghum / alfalfa / other)",
      "corn",
    );
    if (!crop) return;
    try {
      const field = await api.post<Field>(`/api/farms/${farmId}/fields`, {
        name,
        crop,
      });
      setFieldsByFarm((prev) => ({
        ...prev,
        [farmId]: [...(prev[farmId] || []), field],
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function startScout() {
    if (!selectedField) return;
    try {
      const scout = await api.post<Scout>("/api/scouts", {
        field_id: selectedField.id,
      });
      setScouts((p) => [scout, ...p]);
      setActiveScoutId(scout.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function logout() {
    await api.post("/api/auth/logout");
    onLogout();
  }

  return (
    <div className="dash">
      <header>
        <div className="brand">
          <span className="dot" /> whorl
        </div>
        <span className="tag">v0.2 — it knows the field</span>
        <span className="spacer" />
        <span className="who">
          {me.email} · <span className="muted">{me.org_type}</span>
        </span>
        <button className="ghost" onClick={logout}>
          sign out
        </button>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <div className="side-head">
            <h2>{me.org_type === "agronomist" ? "Client farms" : "Farms"}</h2>
            <button className="ghost small" onClick={createFarm}>
              + farm
            </button>
          </div>
          {farms.length === 0 && (
            <div className="empty">
              {me.org_type === "agronomist"
                ? "No client farms yet. Add one to start scouting."
                : "No farm yet. Add yours to start scouting."}
            </div>
          )}
          <ul className="farms">
            {farms.map((f) => (
              <FarmNode
                key={f.id}
                farm={f}
                fields={fieldsByFarm[f.id]}
                onExpand={() => ensureFieldsLoaded(f.id)}
                onCreateField={() => createField(f.id)}
                onSelectField={(field) => {
                  setSelectedField(field);
                  setActiveScoutId(null);
                  setScoutDetail(null);
                }}
                selectedFieldId={selectedField?.id}
              />
            ))}
          </ul>
        </aside>

        <main className="main">
          {error && (
            <div className="error">
              {error}
              <button className="ghost small" onClick={() => setError(null)}>
                dismiss
              </button>
            </div>
          )}
          {!selectedField && (
            <div className="placeholder">
              Pick a field from the sidebar to view its scout log, or add a new
              farm + field to get started.
            </div>
          )}
          {selectedField && (
            <FieldView
              field={selectedField}
              scouts={scouts}
              activeScoutId={activeScoutId}
              onPickScout={setActiveScoutId}
              onStartScout={startScout}
              scoutDetail={scoutDetail}
              onPhotoAdded={() => {
                if (activeScoutId)
                  api
                    .get<ScoutDetail>(`/api/scouts/${activeScoutId}`)
                    .then(setScoutDetail);
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}

// ─── sidebar farm node ─────────────────────────────────────────────────────────

interface FarmNodeProps {
  farm: Farm;
  fields: Field[] | undefined;
  onExpand: () => void;
  onCreateField: () => void;
  onSelectField: (f: Field) => void;
  selectedFieldId: string | undefined;
}

function FarmNode({
  farm,
  fields,
  onExpand,
  onCreateField,
  onSelectField,
  selectedFieldId,
}: FarmNodeProps) {
  const [open, setOpen] = useState(true);
  useEffect(() => {
    if (open && !fields) onExpand();
  }, [open, fields, onExpand]);

  return (
    <li className="farm-node">
      <div className="farm-row" onClick={() => setOpen((p) => !p)}>
        <span className={`chev ${open ? "open" : ""}`}>▸</span>
        <span className="farm-name">{farm.name}</span>
      </div>
      {open && (
        <ul className="fields">
          {(fields || []).map((f) => (
            <li
              key={f.id}
              className={`field-row ${selectedFieldId === f.id ? "sel" : ""}`}
              onClick={() => onSelectField(f)}
            >
              <span className="field-name">{f.name}</span>
              <span className="crop">{f.crop}</span>
            </li>
          ))}
          <li className="field-row add" onClick={onCreateField}>
            <span>+ field</span>
          </li>
        </ul>
      )}
    </li>
  );
}

// ─── main pane: field + scouts + new-scout + uploader ─────────────────────────

interface FieldViewProps {
  field: Field;
  scouts: Scout[];
  activeScoutId: string | null;
  onPickScout: (id: string) => void;
  onStartScout: () => void;
  scoutDetail: ScoutDetail | null;
  onPhotoAdded: () => void;
}

function FieldView({
  field,
  scouts,
  activeScoutId,
  onPickScout,
  onStartScout,
  scoutDetail,
  onPhotoAdded,
}: FieldViewProps) {
  return (
    <div>
      <div className="field-header">
        <div>
          <h1>{field.name}</h1>
          <span className="meta">
            {field.crop}
            {field.acres ? ` · ${field.acres} ac` : ""}
          </span>
        </div>
        <button className="primary" onClick={onStartScout}>
          + new scout
        </button>
      </div>

      <section className="scouts-list">
        <h2>scout log</h2>
        {scouts.length === 0 && (
          <div className="empty">
            No scouts yet on this field. Start one to drop a photo.
          </div>
        )}
        <ul>
          {scouts.map((s) => (
            <li
              key={s.id}
              className={`scout-row ${activeScoutId === s.id ? "sel" : ""}`}
              onClick={() => onPickScout(s.id)}
            >
              <span className="when">
                {new Date(s.started_at).toLocaleString()}
              </span>
              <span className={`status ${s.status}`}>{s.status}</span>
            </li>
          ))}
        </ul>
      </section>

      {activeScoutId && (
        <section className="scout-pane">
          <h2>scout · {activeScoutId.slice(0, 8)}</h2>
          <Uploader scoutId={activeScoutId} field={field} onAdded={onPhotoAdded} />
          {scoutDetail && <ScoutPhotos photos={scoutDetail.photos} />}
        </section>
      )}
    </div>
  );
}

// ─── uploader ─────────────────────────────────────────────────────────────────

function Uploader({
  scoutId,
  field,
  onAdded,
}: {
  scoutId: string;
  field: Field;
  onAdded: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(file: File) {
    setBusy(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("scout_id", scoutId);
      if (field.crop) fd.append("crop", field.crop);
      await api.post("/api/photos", fd);
      onAdded();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className={`drop ${busy ? "busy" : ""}`}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        const f = e.dataTransfer.files?.[0];
        if (f) send(f);
      }}
    >
      <div className="hint">
        <b>Drop a field photo</b>
        <label className="picker">
          {" or pick a file"}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) send(f);
            }}
          />
        </label>
      </div>
      {busy && <div className="status">analyzing…</div>}
      {error && <div className="error">{error}</div>}
    </div>
  );
}

function ScoutPhotos({ photos }: { photos: PhotoWithIds[] }) {
  if (photos.length === 0) {
    return (
      <div className="empty">
        No photos on this scout yet. Drop one above.
      </div>
    );
  }
  return (
    <div className="photo-list">
      {photos.map((p) => (
        <div key={p.photo_id} className="photo-block">
          <div className="photo-meta">
            <span className="muted">
              {new Date(p.uploaded_at).toLocaleString()}
            </span>
            <span className="muted small">
              sha {p.sha256.slice(0, 8)}…
            </span>
          </div>
          <div className="ids">
            {p.identifications.length === 0 && (
              <div className="muted">no identifications</div>
            )}
            {p.identifications.map((i) => (
              <div
                key={i.id}
                className="card"
                style={{ borderLeftColor: confColor(i.confidence) }}
              >
                <div className="row1">
                  <span className="sci">{i.taxon_scientific}</span>
                  <span className="conf">
                    {Math.round(i.confidence * 100)}%
                  </span>
                </div>
                <div className="row2">
                  <span className="common">{i.taxon_common}</span>
                  <span className="stage">{i.lifecycle_stage}</span>
                </div>
                {i.features.length > 0 && (
                  <div className="feats">{i.features.join(" · ")}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function confColor(c: number): string {
  if (c >= 0.8) return "#34d399";
  if (c >= 0.6) return "#fbbf24";
  return "#f87171";
}
