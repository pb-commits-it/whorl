# Contributing to whorl

Thanks for considering a PR. Whorl is built in public, AGPL-3.0, and the kind
of project that gets much better with regional, on-the-ground domain
knowledge. If you've ever lost a soybean field to bean leaf beetle, or argued
with an extension agent about resistance management, you have something to
contribute here.

## What's most valuable

In rough priority order:

1. **KB wiki content** — `whorl/kb/wiki/` is plain markdown an extension
   entomologist, weed scientist, or agronomist can read and improve. Every
   new pest, MOA group, regional resistance note, or alternative-control
   page is directly visible in the recommender output.
2. **Bug reports against the recommender** — if you can produce a photo +
   field-history combination that returns wrong, unsafe, or non-cited
   advice, that's a high-value issue. Include the scout ID + the photo if
   possible.
3. **Additional weather providers** — currently NWS + OpenMeteo + Kansas
   Mesonet. Other state mesonets (Iowa, Nebraska, Oklahoma, Missouri) would
   meaningfully improve recommendations across the v0.3 region.
4. **EPA PPLS sync code** — a `whorl/kb/sources/epa_ppls.py` plugin that
   keeps `products/*.md` REI/PHI rows current with the EPA API.
5. **Frontend polish** — the dashboard is functional but plain. A11y, mobile
   layout, and an actual map polygon-draw UI are all open.

## Code conventions

- **Python 3.11 / 3.12.** Type hints everywhere. `from __future__ import
  annotations` at the top of every file.
- **Async all the way.** Routes, DB access, HTTP calls all use the async
  stack. New synchronous IO inside a request handler is a smell.
- **No stubs.** Every function ships fully working. `pass` /
  `NotImplementedError` / placeholder TODOs are blocked at review.
- **Lint with ruff.** `ruff check whorl tests` must be clean.
- **Tests with pytest.** New routes and pipeline code get tests. Mock
  external services with `respx`.
- **No AI attribution in commits.** No `Co-Authored-By: ...AI...` trailers,
  no "Generated with" footers in committed artifacts.

## Local development

```bash
git clone https://github.com/pb-commits-it/whorl
cd whorl
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
docker compose -f deploy/docker-compose.yml up -d
cd web && npm install && npm run build && cd ..
cp .env.example .env       # set OPENROUTER_API_KEY (sk-or-...)
.venv/bin/whorl kb ingest
.venv/bin/python scripts/seed_demo.py
.venv/bin/whorl up --port 8011
```

Run the test suite:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check whorl tests
cd web && npx tsc --noEmit && npm run build
```

CI runs all three on Python 3.11 + 3.12 and Node 20.

## Writing wiki pages

Every page in `whorl/kb/wiki/` has YAML frontmatter (slug, sources,
last_reviewed) and uses `[[wikilinks]]` for cross-references. See
[`whorl/kb/wiki/schema.md`](whorl/kb/wiki/schema.md) for the page templates
and conventions. After editing, run `.venv/bin/whorl kb ingest` to re-embed
the changed pages, then start a scout against the live app to see your
content show up in recommendations.

## Filing issues

- **Bug**: a reproduction case (steps, expected vs. actual, scout ID if it
  was a recommender call).
- **Feature**: the user problem first, then the proposed shape.
- **Wiki suggestion**: cite the source. KSU MF / UNL CropWatch / extension
  PDFs preferred over Wikipedia.

## License

By contributing, you agree your work is licensed under AGPL-3.0 alongside
the rest of the project.
