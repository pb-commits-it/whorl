/**
 * FieldMap — MapLibre + OSM raster, click-to-set-centroid.
 *
 * Pulled into its own module so it can be lazy-loaded (~700 KB of map code
 * shouldn't ship in the login/dashboard-root bundle).
 */

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, type Field } from "./api";

export default function FieldMap({ field }: { field: Field }) {
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
