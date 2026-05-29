import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  api,
  type AltControl,
  type Application,
  type Farm,
  type Field,
  type FieldWeather,
  type Me,
  type PhotoWithIds,
  type RecResponse,
  type RecResult,
  type Scout,
  type ScoutDetail,
  type StreamIdReady,
  type StreamPhotoUploaded,
  type StreamRecommendationReady,
  type StreamScoutComplete,
} from "./api";

// v0.5 — server-sent events: per-scout live progress feed. Cleans up on
// unmount or when scoutId changes. Auto-reconnects on disconnect.
type SSEHandlers = {
  onPhotoUploaded?: (e: StreamPhotoUploaded) => void;
  onIdReady?: (e: StreamIdReady) => void;
  onRecommendationReady?: (e: StreamRecommendationReady) => void;
  onScoutComplete?: (e: StreamScoutComplete) => void;
  onConnected?: () => void;
  onError?: () => void;
};
function useScoutStream(scoutId: string | null, handlers: SSEHandlers) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!scoutId) return;
    const url = `/api/stream/scouts/${scoutId}`;
    const es = new EventSource(url, { withCredentials: true });
    const on = (name: string, fn: (data: unknown) => void) =>
      es.addEventListener(name, (ev) => {
        try { fn(JSON.parse((ev as MessageEvent).data)); } catch { /* ignore */ }
      });
    on("connected", () => handlersRef.current.onConnected?.());
    on("photo_uploaded", (d) => handlersRef.current.onPhotoUploaded?.(d as StreamPhotoUploaded));
    on("id_ready",       (d) => handlersRef.current.onIdReady?.(d as StreamIdReady));
    on("recommendation_ready", (d) => handlersRef.current.onRecommendationReady?.(d as StreamRecommendationReady));
    on("scout_complete", (d) => handlersRef.current.onScoutComplete?.(d as StreamScoutComplete));
    es.onerror = () => handlersRef.current.onError?.();
    return () => es.close();
  }, [scoutId]);
}

interface Props {
  me: Me;
  onLogout: () => void;
}

export default function Dashboard({ me, onLogout }: Props) {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [fieldsByFarm, setFieldsByFarm] = useState<Record<string, Field[]>>({});
  const [selectedField, setSelectedField] = useState<Field | null>(null);
  const [scouts, setScouts] = useState<Scout[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [activeScoutId, setActiveScoutId] = useState<string | null>(null);
  const [scoutDetail, setScoutDetail] = useState<ScoutDetail | null>(null);
  const [recommendation, setRecommendation] = useState<RecResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Farm[]>("/api/farms").then(setFarms).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selectedField) {
      setScouts([]);
      setApplications([]);
      return;
    }
    const fid = selectedField.id;
    api.get<Scout[]>(`/api/fields/${fid}/scouts`).then(setScouts).catch((e) => setError(e.message));
    api
      .get<Application[]>(`/api/fields/${fid}/applications`)
      .then(setApplications)
      .catch((e) => setError(e.message));
  }, [selectedField]);

  useEffect(() => {
    if (!activeScoutId) {
      setScoutDetail(null);
      setRecommendation(null);
      return;
    }
    api.get<ScoutDetail>(`/api/scouts/${activeScoutId}`).then(setScoutDetail).catch((e) => setError(e.message));
    api
      .get<RecResponse | null>(`/api/scouts/${activeScoutId}/recommendation`)
      .then((r) => setRecommendation(r ?? null))
      .catch(() => setRecommendation(null));
  }, [activeScoutId]);

  const ensureFieldsLoaded = useCallback(
    async (farmId: string) => {
      if (fieldsByFarm[farmId]) return;
      try {
        const rows = await api.get<Field[]>(`/api/farms/${farmId}/fields`);
        setFieldsByFarm((prev) => ({ ...prev, [farmId]: rows }));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    },
    [fieldsByFarm],
  );

  async function createFarm() {
    const name = prompt(me.org_type === "agronomist" ? "Client farm name" : "Farm name");
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
    const crop = prompt("Crop (corn / soybeans / wheat / sorghum / alfalfa / other)", "corn");
    if (!crop) return;
    try {
      const field = await api.post<Field>(`/api/farms/${farmId}/fields`, { name, crop });
      setFieldsByFarm((prev) => ({ ...prev, [farmId]: [...(prev[farmId] || []), field] }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function startScout() {
    if (!selectedField) return;
    try {
      const scout = await api.post<Scout>("/api/scouts", { field_id: selectedField.id });
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
        <div className="brand"><span className="dot" /> whorl</div>
        <span className="tag">v0.3 — it recommends</span>
        <span className="spacer" />
        <span className="who">
          {me.email} · <span className="muted">{me.org_type}</span>
        </span>
        <button className="ghost" onClick={logout}>sign out</button>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <div className="side-head">
            <h2>{me.org_type === "agronomist" ? "Client farms" : "Farms"}</h2>
            <button className="ghost small" onClick={createFarm}>+ farm</button>
          </div>
          {farms.length === 0 && (
            <div className="empty">
              {me.org_type === "agronomist"
                ? "No client farms yet."
                : "No farm yet. Add one to start scouting."}
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
                  setRecommendation(null);
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
              <button className="ghost small" onClick={() => setError(null)}>dismiss</button>
            </div>
          )}
          {!selectedField && (
            <div className="placeholder">
              Pick a field from the sidebar, or add a new farm + field to get started.
            </div>
          )}
          {selectedField && (
            <FieldView
              field={selectedField}
              applications={applications}
              onApplicationAdded={(a) => setApplications((p) => [a, ...p])}
              scouts={scouts}
              activeScoutId={activeScoutId}
              onPickScout={setActiveScoutId}
              onStartScout={startScout}
              scoutDetail={scoutDetail}
              recommendation={recommendation}
              onRecommendation={setRecommendation}
              onPhotoAdded={() => {
                if (activeScoutId) {
                  api.get<ScoutDetail>(`/api/scouts/${activeScoutId}`).then(setScoutDetail);
                }
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}

interface FarmNodeProps {
  farm: Farm;
  fields: Field[] | undefined;
  onExpand: () => void;
  onCreateField: () => void;
  onSelectField: (f: Field) => void;
  selectedFieldId: string | undefined;
}

function FarmNode({ farm, fields, onExpand, onCreateField, onSelectField, selectedFieldId }: FarmNodeProps) {
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

interface FieldViewProps {
  field: Field;
  applications: Application[];
  onApplicationAdded: (a: Application) => void;
  scouts: Scout[];
  activeScoutId: string | null;
  onPickScout: (id: string) => void;
  onStartScout: () => void;
  scoutDetail: ScoutDetail | null;
  recommendation: RecResponse | null;
  onRecommendation: (r: RecResponse | null) => void;
  onPhotoAdded: () => void;
}

function FieldView(p: FieldViewProps) {
  return (
    <div>
      <div className="field-header">
        <div>
          <h1>{p.field.name}</h1>
          <span className="meta">
            {p.field.crop}
            {p.field.acres ? ` · ${p.field.acres} ac` : ""}
          </span>
        </div>
        <button className="primary" onClick={p.onStartScout}>+ new scout</button>
      </div>

      <FieldMap field={p.field} />

      <WeatherStrip field={p.field} />

      <ApplicationsPanel
        field={p.field}
        applications={p.applications}
        onAdded={p.onApplicationAdded}
      />

      <section className="scouts-list">
        <h2>scout log</h2>
        {p.scouts.length === 0 && (
          <div className="empty">No scouts yet on this field. Start one to drop a photo.</div>
        )}
        <ul>
          {p.scouts.map((s) => (
            <li
              key={s.id}
              className={`scout-row ${p.activeScoutId === s.id ? "sel" : ""}`}
              onClick={() => p.onPickScout(s.id)}
            >
              <span className="when">{new Date(s.started_at).toLocaleString()}</span>
              <span className={`status ${s.status}`}>{s.status}</span>
            </li>
          ))}
        </ul>
      </section>

      {p.activeScoutId && (
        <ScoutPane
          scoutId={p.activeScoutId}
          field={p.field}
          detail={p.scoutDetail}
          recommendation={p.recommendation}
          onRecommendation={p.onRecommendation}
          onPhotoAdded={p.onPhotoAdded}
        />
      )}
    </div>
  );
}

function FieldMap({ field }: { field: Field }) {
  // v0.5 MapLibre. OSM raster tiles (no API key, attribution required).
  // Click to set the field's centroid; PATCH /api/fields/:id persists it.
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const [lat, setLat] = useState<number | null>(field.centroid_lat ?? null);
  const [lon, setLon] = useState<number | null>(field.centroid_lon ?? null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    const startLat = field.centroid_lat ?? 38.5266;
    const startLon = field.centroid_lon ?? -97.5777;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
            maxzoom: 19,
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center: [startLon, startLat],
      zoom: field.centroid_lat ? 13 : 6,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }));
    mapRef.current = map;

    if (field.centroid_lat != null && field.centroid_lon != null) {
      markerRef.current = new maplibregl.Marker({ color: "#38bdf8" })
        .setLngLat([field.centroid_lon, field.centroid_lat])
        .addTo(map);
    }

    map.on("click", (e) => {
      const { lng, lat: clat } = e.lngLat;
      setLat(clat);
      setLon(lng);
      setSaved(false);
      if (markerRef.current) {
        markerRef.current.setLngLat([lng, clat]);
      } else {
        markerRef.current = new maplibregl.Marker({ color: "#38bdf8" })
          .setLngLat([lng, clat])
          .addTo(map);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
    // We intentionally rebuild the map when switching fields.
  }, [field.id]);

  async function save() {
    if (lat == null || lon == null) return;
    setSaving(true);
    setSaved(false);
    try {
      await api.patch(`/api/fields/${field.id}`, {
        centroid_lat: lat,
        centroid_lon: lon,
      });
      setSaved(true);
    } catch {
      // surface via existing error path; map UX recovers on next click
    } finally {
      setSaving(false);
    }
  }

  const dirty =
    lat != null && lon != null &&
    (lat !== field.centroid_lat || lon !== field.centroid_lon);

  return (
    <section className="field-map-wrap">
      <div className="field-map-head">
        <h2>field location</h2>
        <div className="muted small">
          {lat != null && lon != null
            ? `${lat.toFixed(4)}, ${lon.toFixed(4)}`
            : "click the map to set this field's centroid"}
          {dirty && (
            <button className="primary small" onClick={save} disabled={saving}>
              {saving ? "saving…" : "save centroid"}
            </button>
          )}
          {saved && !dirty && <span className="ok">✓ saved</span>}
        </div>
      </div>
      <div className="field-map" ref={containerRef} />
    </section>
  );
}

function WeatherStrip({ field }: { field: Field }) {
  const [data, setData] = useState<FieldWeather | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async (force: boolean) => {
    setLoading(true);
    setErr(null);
    try {
      const qs = force ? "?refresh=true" : "";
      const w = await api.get<FieldWeather>(`/api/fields/${field.id}/weather${qs}`);
      setData(w);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "weather fetch failed");
    } finally {
      setLoading(false);
    }
  }, [field.id]);

  useEffect(() => { setData(null); load(false); }, [field.id, load]);

  if (loading && !data) {
    return <section className="weather-strip"><div className="muted">loading forecast…</div></section>;
  }
  if (err) {
    return (
      <section className="weather-strip">
        <div className="weather-head">
          <h2>spray window forecast</h2>
          <button className="ghost small" onClick={() => load(true)}>retry</button>
        </div>
        <div className="error inline">{err}</div>
      </section>
    );
  }
  if (!data || data.spray_windows.length === 0) {
    return (
      <section className="weather-strip">
        <div className="weather-head">
          <h2>spray window forecast</h2>
          <button className="ghost small" onClick={() => load(true)}>refresh</button>
        </div>
        <div className="muted">No forecast available right now.</div>
      </section>
    );
  }

  const fetchedNote = data.fetched_at
    ? `updated ${new Date(data.fetched_at).toLocaleTimeString()}`
    : null;

  return (
    <section className="weather-strip">
      <div className="weather-head">
        <h2>spray window forecast</h2>
        <div className="weather-meta muted">
          {data.coords.is_default ? "central KS default" : `${data.coords.lat.toFixed(3)}, ${data.coords.lon.toFixed(3)}`}
          {fetchedNote ? ` · ${fetchedNote}` : ""}
          <button className="ghost small" onClick={() => load(true)} disabled={loading}>
            {loading ? "…" : "refresh"}
          </button>
        </div>
      </div>
      <ul className="weather-days">
        {data.spray_windows.map((d) => {
          const fc = data.forecasts.find((f) => f.date === d.date);
          return (
            <li key={d.date} className={`weather-day ${d.label}`} title={d.reason}>
              <div className="day-name">{new Date(d.date + "T12:00").toLocaleDateString(undefined, { weekday: "short" })}</div>
              <div className="day-temp">
                {fc?.t_high_f != null ? `${Math.round(fc.t_high_f)}°` : "—"}
                <span className="muted">
                  {fc?.t_low_f != null ? ` / ${Math.round(fc.t_low_f)}°` : ""}
                </span>
              </div>
              <div className="day-wind">
                {d.wind_mph != null ? `${Math.round(d.wind_mph)} mph` : "—"}
              </div>
              <div className="day-rain">
                {d.rain_probability != null ? `${Math.round(d.rain_probability * 100)}% rain` : ""}
              </div>
              <div className={`label-pill ${d.label}`}>{d.label}</div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function ApplicationsPanel({
  field,
  applications,
  onAdded,
}: {
  field: Field;
  applications: Application[];
  onAdded: (a: Application) => void;
}) {
  const [open, setOpen] = useState(false);

  async function logSpray(form: NewApplication) {
    const body = {
      field_id: field.id,
      applied_at: new Date(form.applied_at).toISOString(),
      product_name: form.product_name,
      active_ingredient: form.active_ingredient || null,
      moa_class: form.moa_class || null,
      moa_group: form.moa_group || null,
      pest_target: form.pest_target || null,
      rate: form.rate || null,
      rei_hours: form.rei_hours ? Number(form.rei_hours) : null,
      phi_days: form.phi_days ? Number(form.phi_days) : null,
    };
    const a = await api.post<Application>("/api/applications", body);
    onAdded(a);
    setOpen(false);
  }

  return (
    <section className="apps-panel">
      <div className="apps-head">
        <h2>applications · treatment history</h2>
        <button className="ghost small" onClick={() => setOpen((p) => !p)}>
          {open ? "cancel" : "+ log spray"}
        </button>
      </div>
      {open && <LogApplicationForm onSubmit={logSpray} />}
      {applications.length === 0 && (
        <div className="empty">No applications logged. The recommender uses these to enforce MOA rotation.</div>
      )}
      <ul className="apps-list">
        {applications.map((a) => (
          <li key={a.id} className="app-row">
            <div className="left">
              <div className="prod">{a.product_name}</div>
              <div className="ai muted">{a.active_ingredient || "—"}</div>
            </div>
            <div className="mid">
              {a.moa_class && a.moa_group && (
                <span className="moa">{a.moa_class} {a.moa_group}</span>
              )}
              {a.pest_target && <span className="pest muted">on {a.pest_target}</span>}
            </div>
            <div className="right muted">
              {new Date(a.applied_at).toLocaleDateString()}
              {a.rei_hours != null && <span className="rei"> · REI {a.rei_hours}h</span>}
              {a.phi_days != null && <span className="phi"> · PHI {a.phi_days}d</span>}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

interface NewApplication {
  applied_at: string;
  product_name: string;
  active_ingredient: string;
  moa_class: "IRAC" | "FRAC" | "HRAC" | "";
  moa_group: string;
  pest_target: string;
  rate: string;
  rei_hours: string;
  phi_days: string;
}

function LogApplicationForm({ onSubmit }: { onSubmit: (form: NewApplication) => Promise<void> }) {
  const today = new Date().toISOString().slice(0, 16);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [form, setForm] = useState<NewApplication>({
    applied_at: today,
    product_name: "",
    active_ingredient: "",
    moa_class: "IRAC",
    moa_group: "",
    pest_target: "",
    rate: "",
    rei_hours: "",
    phi_days: "",
  });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await onSubmit(form);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function set<K extends keyof NewApplication>(k: K, v: NewApplication[K]) {
    setForm((p) => ({ ...p, [k]: v }));
  }

  return (
    <form className="app-form" onSubmit={submit}>
      <div className="grid">
        <label>
          <span>Applied at</span>
          <input
            type="datetime-local"
            value={form.applied_at}
            onChange={(e) => set("applied_at", e.target.value)}
            required
          />
        </label>
        <label>
          <span>Product name</span>
          <input
            type="text"
            value={form.product_name}
            onChange={(e) => set("product_name", e.target.value)}
            placeholder="Brigade 2EC"
            required
          />
        </label>
        <label>
          <span>Active ingredient</span>
          <input
            type="text"
            value={form.active_ingredient}
            onChange={(e) => set("active_ingredient", e.target.value)}
            placeholder="bifenthrin"
          />
        </label>
        <label>
          <span>Pest target</span>
          <input
            type="text"
            value={form.pest_target}
            onChange={(e) => set("pest_target", e.target.value)}
            placeholder="Helicoverpa zea"
          />
        </label>
        <label>
          <span>MOA class</span>
          <select
            value={form.moa_class}
            onChange={(e) => set("moa_class", e.target.value as NewApplication["moa_class"])}
          >
            <option value="IRAC">IRAC</option>
            <option value="FRAC">FRAC</option>
            <option value="HRAC">HRAC</option>
            <option value="">(none)</option>
          </select>
        </label>
        <label>
          <span>MOA group</span>
          <input
            type="text"
            value={form.moa_group}
            onChange={(e) => set("moa_group", e.target.value)}
            placeholder="3A"
          />
        </label>
        <label>
          <span>Rate</span>
          <input
            type="text"
            value={form.rate}
            onChange={(e) => set("rate", e.target.value)}
            placeholder="6.4 oz/ac"
          />
        </label>
        <label>
          <span>REI (hours)</span>
          <input
            type="number"
            value={form.rei_hours}
            onChange={(e) => set("rei_hours", e.target.value)}
            min={0}
          />
        </label>
        <label>
          <span>PHI (days)</span>
          <input
            type="number"
            value={form.phi_days}
            onChange={(e) => set("phi_days", e.target.value)}
            min={0}
          />
        </label>
      </div>
      <div className="actions">
        <button className="primary small" type="submit" disabled={busy}>
          {busy ? "saving…" : "log application"}
        </button>
      </div>
      {err && <div className="error">{err}</div>}
    </form>
  );
}

interface ScoutPaneProps {
  scoutId: string;
  field: Field;
  detail: ScoutDetail | null;
  recommendation: RecResponse | null;
  onRecommendation: (r: RecResponse | null) => void;
  onPhotoAdded: () => void;
}

function ScoutPane({ scoutId, field, detail, recommendation, onRecommendation, onPhotoAdded }: ScoutPaneProps) {
  const hasIdentifications = (detail?.photos.flatMap((p) => p.identifications).length ?? 0) > 0;
  const [recBusy, setRecBusy] = useState(false);
  const [recErr, setRecErr] = useState<string | null>(null);

  // v0.5 live event log — appears above the photo grid as IDs stream in.
  const [liveEvents, setLiveEvents] = useState<Array<
    { kind: "uploaded"; at: number; thumb: string }
    | { kind: "id"; at: number; pest: string; common: string; stage: string; conf: number; lowConf: boolean; needsRescout: boolean }
    | { kind: "rec"; at: number; action: string; pest: string }
    | { kind: "done"; at: number; latencyMs: number }
  >>([]);
  const [streamStatus, setStreamStatus] = useState<"connecting" | "live" | "lost">("connecting");

  useScoutStream(scoutId, {
    onConnected: () => setStreamStatus("live"),
    onError: () => setStreamStatus("lost"),
    onPhotoUploaded: (e) => {
      setLiveEvents((prev) => [...prev, { kind: "uploaded", at: Date.now(), thumb: e.thumb_path }]);
    },
    onIdReady: (e) => {
      const c = e.candidates[0];
      setLiveEvents((prev) => [...prev, {
        kind: "id", at: Date.now(),
        pest: c?.scientific_name ?? "(no candidate)",
        common: c?.common_name ?? "",
        stage: c?.lifecycle_stage ?? "",
        conf: e.top_confidence,
        lowConf: e.low_confidence,
        needsRescout: e.needs_rescout,
      }]);
      onPhotoAdded(); // refresh ScoutDetail too
    },
    onRecommendationReady: (e) => {
      setLiveEvents((prev) => [...prev, { kind: "rec", at: Date.now(), action: e.action, pest: e.pest_focus }]);
    },
    onScoutComplete: (e) => {
      setLiveEvents((prev) => [...prev, { kind: "done", at: Date.now(), latencyMs: e.latency_ms }]);
    },
  });

  async function generate() {
    setRecBusy(true);
    setRecErr(null);
    try {
      const r = await api.post<RecResponse>(`/api/scouts/${scoutId}/recommend`);
      onRecommendation(r);
    } catch (e) {
      setRecErr(e instanceof Error ? e.message : String(e));
    } finally {
      setRecBusy(false);
    }
  }

  return (
    <section className="scout-pane">
      <h2>
        scout · {scoutId.slice(0, 8)}
        <span className={`stream-dot ${streamStatus}`} title={`stream ${streamStatus}`}>●</span>
      </h2>
      <Uploader scoutId={scoutId} field={field} onAdded={onPhotoAdded} />
      {liveEvents.length > 0 && <LiveEventLog events={liveEvents} />}
      {detail && <ScoutPhotos photos={detail.photos} />}
      {hasIdentifications && !recommendation && (
        <div className="reco-cta">
          <button className="primary" onClick={generate} disabled={recBusy}>
            {recBusy ? "thinking…" : "generate recommendation"}
          </button>
          <span className="muted small">
            Uses your applications history to enforce MOA rotation; cites the wiki by paragraph.
          </span>
        </div>
      )}
      {recErr && <div className="error">{recErr}</div>}
      {recommendation && <RecommendationCard rec={recommendation} />}
    </section>
  );
}

function LiveEventLog({ events }: { events: Array<
  | { kind: "uploaded"; at: number; thumb: string }
  | { kind: "id"; at: number; pest: string; common: string; stage: string; conf: number; lowConf: boolean; needsRescout: boolean }
  | { kind: "rec"; at: number; action: string; pest: string }
  | { kind: "done"; at: number; latencyMs: number }
> }) {
  return (
    <ul className="live-log">
      {events.map((e, i) => {
        if (e.kind === "uploaded") {
          return <li key={i} className="ev uploaded"><span className="ev-tag">photo</span> uploaded</li>;
        }
        if (e.kind === "id") {
          const cls = e.needsRescout ? "ev id needs-rescout" : e.lowConf ? "ev id low-conf" : "ev id";
          return (
            <li key={i} className={cls}>
              <span className="ev-tag">id</span>
              <b>{e.pest}</b>
              {e.common && <span className="muted"> ({e.common})</span>}
              {e.stage && <span className="muted"> · {e.stage}</span>}
              <span className="conf">{(e.conf * 100).toFixed(0)}%</span>
              {e.needsRescout && <span className="badge rescout">needs rescout</span>}
              {!e.needsRescout && e.lowConf && <span className="badge lowconf">low confidence</span>}
            </li>
          );
        }
        if (e.kind === "rec") {
          return (
            <li key={i} className="ev rec">
              <span className="ev-tag">rec</span>
              <b>{e.action}</b> · {e.pest}
            </li>
          );
        }
        return (
          <li key={i} className="ev done">
            <span className="ev-tag">done</span>
            scout complete · {(e.latencyMs / 1000).toFixed(1)}s
          </li>
        );
      })}
    </ul>
  );
}

function Uploader({ scoutId, field, onAdded }: { scoutId: string; field: Field; onAdded: () => void }) {
  // v0.5: multi-file upload. Each photo is POSTed in parallel; UI shows a
  // running counter so the dropzone makes sense for a 4-photo scout.
  const [inFlight, setInFlight] = useState(0);
  const [done, setDone] = useState(0);
  const [error, setError] = useState<string | null>(null);

  async function sendOne(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("scout_id", scoutId);
    if (field.crop) fd.append("crop", field.crop);
    try {
      await api.post("/api/photos", fd);
      onAdded();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    }
  }

  async function sendMany(files: FileList | File[]) {
    const list = Array.from(files);
    if (list.length === 0) return;
    setError(null);
    setInFlight((n) => n + list.length);
    setDone(0);
    await Promise.allSettled(list.map((f) =>
      sendOne(f).finally(() => setDone((d) => d + 1)),
    ));
    setInFlight((n) => Math.max(0, n - list.length));
  }

  const busy = inFlight > 0;
  return (
    <div
      className={`drop ${busy ? "busy" : ""}`}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        if (e.dataTransfer.files?.length) sendMany(e.dataTransfer.files);
      }}
    >
      <div className="hint">
        <b>Drop field photos</b>
        <label className="picker">
          {" or pick files"}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={(e) => {
              if (e.target.files?.length) sendMany(e.target.files);
              e.target.value = "";
            }}
          />
        </label>
      </div>
      {busy && (
        <div className="status">analyzing… {done}/{inFlight}</div>
      )}
      {error && <div className="error">{error}</div>}
    </div>
  );
}

function ScoutPhotos({ photos }: { photos: PhotoWithIds[] }) {
  if (photos.length === 0) {
    return <div className="empty">No photos on this scout yet. Drop one above.</div>;
  }
  return (
    <div className="photo-list">
      {photos.map((p) => (
        <div key={p.photo_id} className="photo-block">
          <div className="photo-meta">
            <span className="muted">{new Date(p.uploaded_at).toLocaleString()}</span>
            <span className="muted small">sha {p.sha256.slice(0, 8)}…</span>
          </div>
          <div className="ids">
            {p.identifications.length === 0 && <div className="muted">no identifications</div>}
            {p.identifications.map((i) => (
              <div key={i.id} className="card" style={{ borderLeftColor: confColor(i.confidence) }}>
                <div className="row1">
                  <span className="sci">{i.taxon_scientific}</span>
                  <span className="conf">{Math.round(i.confidence * 100)}%</span>
                </div>
                <div className="row2">
                  <span className="common">{i.taxon_common}</span>
                  <span className="stage">{i.lifecycle_stage}</span>
                </div>
                {i.features.length > 0 && <div className="feats">{i.features.join(" · ")}</div>}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function actionColor(a: RecResult["action"]): string {
  switch (a) {
    case "treat":
      return "#f87171";
    case "monitor":
      return "#fbbf24";
    case "scout_again":
      return "#38bdf8";
    case "no_action":
      return "#34d399";
  }
}

function altIcon(c: AltControl["category"]): string {
  if (c === "biological") return "🧬";
  if (c === "cultural") return "🌾";
  return "🪤";
}

function RecommendationCard({ rec }: { rec: RecResponse }) {
  const r = rec.result;
  return (
    <div className="reco" style={{ borderColor: actionColor(r.action) }}>
      <div className="reco-head">
        <span className="reco-action" style={{ color: actionColor(r.action) }}>
          {r.action.toUpperCase().replace("_", " ")}
        </span>
        <span className="reco-pest">{r.pest_focus}</span>
        <span className={`reco-conf ${r.confidence}`}>confidence {r.confidence}</span>
      </div>
      <p className="reco-plain">{r.plain_english}</p>
      {r.threshold_context && (
        <p className="reco-threshold muted">{r.threshold_context}</p>
      )}

      {r.chemical && (
        <div className="reco-section">
          <h3>chemical recommendation</h3>
          <div className="reco-chem">
            <div className="chem-product">{r.chemical.product}</div>
            <div className="chem-ai muted">{r.chemical.active_ingredient}</div>
            <div className="chem-tags">
              <span className="tag moa">{r.chemical.moa_class} {r.chemical.moa_group}</span>
              <span className="tag rei">REI {r.chemical.rei_hours}h</span>
              <span className="tag phi">PHI {r.chemical.phi_days}d</span>
            </div>
            <div className="chem-rot">
              <span className="muted">rotation:</span> {r.chemical.rotation_rationale}
            </div>
          </div>
        </div>
      )}

      {r.spray_window && (
        <div className="reco-section">
          <h3>spray window</h3>
          <div className="spray">
            <b>{r.spray_window.open}</b> → <b>{r.spray_window.close}</b>
            <div className="muted">{r.spray_window.reason}</div>
          </div>
        </div>
      )}

      {r.alternatives.length > 0 && (
        <div className="reco-section">
          <h3>alternatives</h3>
          <ul className="alts">
            {r.alternatives.map((a, i) => (
              <li key={i}>
                <span className="alt-icon">{altIcon(a.category)}</span>
                <div>
                  <div className="alt-name">{a.name} <span className="muted">· {a.category}</span></div>
                  <div className="alt-sum muted">{a.summary}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {r.citations.length > 0 && (
        <details className="reco-section">
          <summary>citations · {r.citations.length}</summary>
          <ul className="cits">
            {r.citations.map((c, i) => (
              <li key={i}><span className="muted">[{c.chunk_id}]</span> {c.quote}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="reco-foot muted small">
        {rec.model_used} · {rec.latency_ms}ms · prompt {rec.prompt_version}
      </div>
    </div>
  );
}

function confColor(c: number): string {
  if (c >= 0.8) return "#34d399";
  if (c >= 0.6) return "#fbbf24";
  return "#f87171";
}
