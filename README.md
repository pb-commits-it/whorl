<h1 align="center">whorl</h1>

<p align="center">
  <b>An open-source crop-scouting dashboard.</b><br>
  Photo of a pest in. Cited recommendation out. Under 30 seconds.<br>
  Built by a PhD entomologist for Midwest farmers and crop consultants.
</p>

<p align="center">
  <a href="https://github.com/pb-commits-it/whorl/releases/tag/v1.0"><img src="https://img.shields.io/badge/release-v1.0-38bdf8" alt="v1.0"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-7137bd" alt="AGPL-3.0"></a>
  <a href="https://github.com/pb-commits-it/whorl/actions"><img src="https://img.shields.io/github/actions/workflow/status/pb-commits-it/whorl/ci.yml?branch=main" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12-blue" alt="python 3.11/3.12">
</p>

<p align="center">
  <i>v1.0 shipped 2026-05-29 — the full 0.1 → 1.0 arc is live. See <a href="CHANGELOG.md">CHANGELOG</a> · <a href="ROADMAP.md">ROADMAP</a>.</i>
</p>

```
photo  →  Helicoverpa zea (corn earworm) · larva                            95%
id     →  treat · Spinosad (IRAC 5) · REI 4 h · PHI 1 d
why    →  rotating off IRAC 3A bifenthrin 14 d ago · KSU MF743 p.12
also   →  Bt-kurstaki (biological), early planting (cultural)
when   →  don't spray Thursday — winds 18 mph (≥15 → drift risk)
done   →  scout complete · 8.5 s
```

---

## What it does

A farmer or independent crop consultant drops a phone photo of a pest, disease, or crop damage into the dashboard, picks the field it came from, and in under 30 seconds gets:

- A **scientific identification** with confidence + lifecycle stage
- The **regional economic-injury threshold** cited to extension publications by paragraph
- A **plain-English action recommendation** — including IRAC / FRAC / HRAC mode-of-action rotation against the field's recent applications history
- At least one **biological / cultural / mechanical alternative** when one exists for the pest × crop × stage
- **REI and PHI** from EPA PPLS for any chemical recommendation
- The **weather window** for treatment from NWS / Kansas Mesonet / OpenMeteo

## Status

| Tag | Name | Status |
|---|---|---|
| **v0.1** | *It identifies* | ✅ shipped |
| **v0.2** | *It knows the field* | ✅ shipped |
| **v0.3** | *It recommends* | ✅ shipped |
| **v0.4** | *It watches the sky* | ✅ shipped |
| **v0.5** | *It streams live* | ✅ shipped |
| **v1.0** | *Launch* | ✅ shipped |

See [`ROADMAP.md`](ROADMAP.md) for the staged release plan.

## Architecture

- **Backend**: FastAPI + async, served by uvicorn, deployed via systemd + Caddy on an IONOS VPS
- **Database**: self-hosted Postgres 16 + pgvector (v0.2+)
- **Vision + reasoning**: Qwen3-VL via OpenRouter (Gemini Flash fallback)
- **Knowledge base**: LLM-curated markdown wiki ([Karpathy `llm-wiki` pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) over immutable raw sources — KSU MF742–MF810, IRAC v11.1, FRAC 2024, HRAC, EPA PPLS API, Cornell NYS IPM biocontrol, ATTRA, IPM Centers, iNat, GBIF
- **Recommender enforces** MOA rotation against the field's `applications` history, surfaces ≥1 non-chemical alternative per `treat` action, respects REI / PHI, prefers selective products when beneficials are visible
- **Frontend**: React + Vite + TypeScript
- **License**: AGPL-3.0

## Try it locally

```bash
git clone https://github.com/pb-commits-it/whorl
cd whorl
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
docker compose -f deploy/docker-compose.yml up -d              # pgvector on 127.0.0.1:5433
cd web && npm install && npm run build && cd ..
cp .env.example .env                                            # add your OPENROUTER_API_KEY
.venv/bin/whorl kb ingest                                       # load the wiki
.venv/bin/python scripts/seed_demo.py                           # demo@whorl.app + sample scout
.venv/bin/whorl up --port 8011                                  # open http://127.0.0.1:8011
```

## Deploy to your own VPS

A single idempotent installer brings up the full stack on a fresh Ubuntu / Debian box:

```bash
git clone https://github.com/pb-commits-it/whorl /opt/whorl
cd /opt/whorl && sudo bash deploy/install.sh
```

This provisions Python 3.12 + Node + Docker + Caddy + restic, creates the `whorl` service user, materializes `/var/lib/whorl/{photos,pg,backups}`, brings up pgvector via `docker compose`, ingests the wiki KB, and enables four systemd units (app, daily 04:00 weather sync, nightly 03:00 restic→B2 backup). TLS lands automatically via Caddy + Let's Encrypt for `whorl.app` (marketing) and `app.whorl.app` (dashboard). Edit `.env` with `OPENROUTER_API_KEY` + `JWT_SECRET` + B2 creds, then `systemctl restart whorl`. See [`deploy/`](deploy/) for the Caddyfile + systemd units.

## Contributing

Bug reports + PRs welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md). The KB wiki under `whorl/kb/wiki/` is the highest-leverage place to PR: every page is human-readable markdown an extension entomologist or weed scientist can review and improve.

## Built by

[Paul Bergeron](https://github.com/pb-commits-it) — PhD ecology / entomology / agriculture, then a pivot into AI / agent-infrastructure engineering. Based in Wichita, KS.

## License

[AGPL-3.0](LICENSE). Closed-source hosted services running modified versions must publish their changes.
