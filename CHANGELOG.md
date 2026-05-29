# Changelog

Whorl follows [SemVer](https://semver.org) and [Keep a Changelog](https://keepachangelog.com).
Each `v0.x` was its own day-of-release build-in-public milestone — see
[ROADMAP.md](ROADMAP.md) for the staged narrative.

## v1.0.1 — *Launch polish* (2026-05-29)

### Added
- `CHANGELOG.md` (this file) and `CONTRIBUTING.md`.
- README hero refreshed — release/license/CI/Python badges, terminal-style
  scout trace, install + deploy quickstarts.
- `GET /api/health/deep` — verifies Postgres connectivity, returns 503 on
  DB failure (use this from external uptime checks; `/api/health` still
  returns 200 on DB-down because uvicorn is alive).

### Changed
- `scripts/seed_demo.py` now also creates one completed sample scout
  (Helicoverpa zea ID @ 95% + spinosad recommendation + Bt-k/early-planting
  alternatives + 3 citations) so demo visitors land on a populated dashboard.
- Frontend code-splits MapLibre into its own chunk: main bundle 974 KB →
  168 KB (53 KB gz). FieldMap loads lazily only when a field is selected.

## v1.0 — *Launch* (2026-05-29)

The full deploy + marketing surface for the v1.0 launch.

### Added
- `deploy/install.sh` — idempotent Ubuntu/Debian installer for a fresh VPS:
  installs Python 3.12 + Node + Docker + Caddy + restic, creates the `whorl`
  service user, materializes `/var/lib/whorl/{photos,pg,backups}`, brings up
  pgvector via `docker compose`, ingests the wiki KB, enables systemd units.
- `deploy/systemd/whorl.service` — uvicorn on `127.0.0.1:8010` with
  `NoNewPrivileges`, `ProtectSystem=full`, `ProtectHome=true`, memory caps.
- `deploy/systemd/whorl-weather.{service,timer}` — daily 04:00 pre-fetch of
  every field's 7-day forecast (calls the new `whorl weather sync` CLI).
- `deploy/systemd/whorl-backup.{service,timer}` — nightly 03:00 `pg_dump`
  plus restic snapshot of `/var/lib/whorl/photos` to Backblaze B2, with
  daily/weekly/monthly retention.
- `deploy/caddy/Caddyfile` — TLS via Let's Encrypt for `whorl.app` (marketing)
  and `app.whorl.app` (dashboard). SSE-aware reverse proxy (`flush_interval -1`,
  24 h read timeout). 25 MB body limit. HSTS + Referrer-Policy + X-Frame-Options.
- `marketing/index.html` — single-file landing page (hero, demo strip, three
  pillars, how-it-works, working waitlist form).
- `WaitlistEntry` model + `POST /api/waitlist` — no auth, idempotent on dupes,
  case-normalized email, captures user-agent + forwarded IP.
- `scripts/seed_demo.py` — materializes `demo@whorl.app` (farmer org),
  Hartman Family Farm, North 80 corn field at Manhattan-KS coordinates
  (Mesonet-in-range), and a 14-day-old IRAC 3A bifenthrin application.
- `whorl weather sync` CLI subcommand.

## v0.5 — *It streams live* (2026-05-29)

### Added
- SSE pub/sub hub broadcasting `photo_uploaded` → `id_ready` →
  `recommendation_ready` → `scout_complete` per scout via
  `GET /api/stream/scouts/{id}` with `heartbeat` keep-alive.
- Multi-photo parallel upload (`PhotoDropzone` takes N files; running counter).
- Confidence gate: top ID < 0.55 → deterministic `scout_again` result with
  concrete next-photo guidance, no LLM call. Top ID < 0.75 → `low_confidence`
  flag propagated through the SSE event → yellow border in the UI live log.
- Kansas Mesonet provider — 30-station catalog + haversine 25 km gate;
  parses the K-State REST CSV (TEMP/WSPD/PRECIP/RH) over the trailing 24 h
  into a single "today" `DailyForecast` row.
- `spray_windows()` now prefers Mesonet > OpenMeteo > NWS, in that order.
- MapLibre GL field map (OSM raster tiles); click-to-set-centroid →
  `PATCH /api/fields/{id}` persists.

### Tests
- 65 → 70 (added stream pub/sub, low-confidence event flags, scout_again
  shortcut, Mesonet CSV parse + distance gate, field PATCH cross-org).

## v0.4 — *It watches the sky* (2026-05-29)

### Added
- `FieldWeather` model: per-field, per-date, per-provider forecast row.
- `NWSProvider` (api.weather.gov, two-call `points` → `forecast`) and
  `OpenMeteoProvider` (global, sub-daily wind + rain probability). Both keyless.
- 6-hour TTL cache with upsert per `(field_id, date, provider)`.
- Spray-window classifier: wind ≥ 15 mph → `poor` (drift), 10–15 →
  `marginal`; rain prob ≥ 50% → `poor` (washoff), 30–50 → `marginal`.
- `GET /api/fields/{id}/weather` with `?refresh=true&days=N`.
- WeatherStrip 7-day dashboard component, colored by spray label.
- Recommender now consumes the spray window as a fifth input alongside
  identifications, KB excerpts, recent applications, and field context.

### Tests
- 39 → 49 (added provider parsing, classifier, cache provider-preference,
  past-date filtering).

## v0.3 — *It recommends* (2026-05-28)

### Added
- Karpathy `llm-wiki`-pattern KB: 12 hand-authored markdown pages under
  `whorl/kb/wiki/` (pests, crops, products, MOA groups, alternatives, regions),
  plus `schema.md` + `index.md` + `log.md` conventions.
- `whorl kb ingest` — YAML-frontmatter parser + paragraph-aware chunker +
  OpenAI `text-embedding-3-small` via OpenRouter → `kb_chunks` table with
  entity_kind/entity_slug + crops/pests/regions/moa_groups tags.
- Python-side cosine retrieval with tag-match boosts (pgvector HNSW deferred
  to a later release).
- `pipeline.recommend.generate_recommendation` — Qwen3-VL with strict-JSON
  system prompt enforcing MOA rotation, ≥1 alternative on every `treat`,
  REI/PHI citation, chunk_id-grounded claims.
- `Application` model + `POST /api/applications` (treatment history drives
  rotation in the recommender prompt).
- `Recommendation` model + `POST /api/scouts/{id}/recommend` + `GET
  /api/scouts/{id}/recommendation`.
- Frontend: `ApplicationsPanel` log-spray form, `RecommendationCard` with
  action chip, threshold context + citations, chemical block with MOA + REI/PHI
  tags + rotation rationale, spray window, alternatives, expandable citations.

### Tests
- 17 → 39 (added wiki loader, RAG cosine + tag boosts, ingest idempotency,
  applications CRUD + cross-org isolation, full recommend flow with mocked
  vision + embeddings + recommendation).

## v0.2 — *It knows the field* (2026-05-28)

### Added
- Magic-link auth (`POST /api/auth/magic` → `GET /api/auth/verify`) +
  signed JWT cookie via `python-jose` (HS256, 30-day rolling).
- Postgres 16 + pgvector via `docker compose` on `127.0.0.1:5433`.
- `Organization`, `User`, `AuthToken`, `Farm`, `Field`, `Scout`, `Photo`
  models + CRUD endpoints scoped to the user's org.
- Sidebar farm/field navigation; new-scout flow tied to a specific field.

## v0.1 — *It identifies* (2026-05-28)

### Added
- `POST /api/photos` (multipart) — store original + 512 px thumbnail to disk
  via `ObjectStore` interface, call Qwen3-VL through OpenRouter, return
  structured-JSON `VisionResult` (up to 3 candidates per photo).
- Fallback to Gemini Flash on two malformed-JSON retries.
- `PhotoDropzone` + minimal React + Vite + TypeScript shell.

### Initial
- AGPL-3.0, FastAPI + uvicorn, async stack, build-in-public README.
