# Roadmap

whorl ships in public, in stages. Each release is a self-contained, *working* slice — no half-built stubs. Tags below map to GitHub releases.

---

### v0.1 — *It identifies*
The pipe end to end.
- `POST /api/photos` → JSON pest IDs from Qwen3-VL with confidence + lifecycle stage
- Structured-output parsing (Pydantic); Gemini Flash fallback on malformed JSON
- Local-disk photo storage behind an `ObjectStore` protocol
- Minimal upload UI (drag-drop + result card)
- No auth, no DB

*Exit: drop a phone photo of a pest in the browser → see a plausible scientific ID within ~10s.*

### v0.2 — *It knows the field*
- Magic-link auth (Resend) + signed JWT cookies
- Postgres 16 + pgvector via Docker Compose; Alembic migrations
- Tables: organizations / users / farms / fields / scouts / photos / identifications / **applications** (treatment history)
- Multi-tenant RLS
- Sidebar farm/field tree; scout list

*Exit: every photo lives in a field's scout log forever.*

### v0.3 — *It recommends*
- LLM-curated wiki (`kb/wiki/`) built by a maintainer agent from KSU MFs + IRAC/FRAC/HRAC + EPA PPLS + Cornell biocontrol + ATTRA
- Two-pass retrieval (wiki first, raw fallback)
- Recommender enforces MOA rotation against the field's `applications`, surfaces ≥1 alt control, cites REI/PHI

*Exit: scouting a corn-earworm photo on a field with a recent IRAC 3A spray returns an IRAC 5/28 recommendation, a biological alternative, and REI/PHI.*

### v0.4 — *It watches the sky* ✅ shipped 2026-05-29
- NWS + OpenMeteo wired (keyless), Kansas Mesonet deferred to v0.5
- 6-hour-cached `field_weather` per field + provider
- Spray-window classifier (good / marginal / poor) — wind ≥15 mph = drift risk; rain ≥50% = washoff risk
- 7-day forecast strip in the field view, colored by spray label
- Recommender consumes the spray window as a fifth input — recommendations now reason about which day to spray
- Field map (MapLibre GL) deferred to v0.5

*Exit met: scouting a corn-earworm photo on a 14-day-old IRAC 3A field, in current central-KS conditions (6 of 7 days "poor" due to 17–23 mph winds), returns Spinosad (IRAC 5) + Bt-k + early-planting + the line "all days are marginal or poor due to high winds and/or rain — wait for favorable conditions." 8.5s end-to-end.*

### v0.5 — *It streams live*
- SSE on `/app/scout/new`: pest IDs stream in as Qwen returns them
- Multi-photo flow; confidence handling + `scout_again` fallback

*Exit: the hero GIF — four pest IDs landing in ~6 seconds.*

### v1.0 — *Launch*
- Deployed at `app.whorl.app` via systemd + Caddy on IONOS VPS Linux L
- Seeded demo org for the demo video
- 60s demo video + LinkedIn launch post + Show HN

*Exit: anyone can sign up at whorl.app, drop a phone photo, and act on a real recommendation.*
