# Whorl wiki — conventions

This is the schema doc the wiki maintainer agent reads on every ingest pass.
It's also a reference for humans editing pages directly.

## Page kinds

| Folder | Slug pattern | Frontmatter required |
|---|---|---|
| `pests/` | `<species-slug>` | `scientific_name`, `common_names`, `taxonomy`, `hosts`, `regions`, `critical_stages` |
| `crops/` | `<crop-slug>` | `name`, `aliases`, `regions` |
| `products/` | `<active-ingredient-slug>` | `name`, `active_ingredient`, `moa_class`, `moa_group`, `rei_hours`, `phi_days` |
| `moa/` | `<class>-<group>-<short>` | `moa_class`, `moa_group`, `chemical_class` |
| `alt-controls/biological/` | `<slug>` | `name`, `category: biological`, `targets`, `mode` |
| `alt-controls/cultural/` | `<slug>` | `name`, `category: cultural` |
| `alt-controls/mechanical/` | `<slug>` | `name`, `category: mechanical` |
| `regions/` | `<state-code-lower>` | `state_code`, `state_name`, `crops` |

## Cross-references

Use `[[products/spinosad]]`, `[[pests/helicoverpa-zea]]`, etc. Links are
unresolved during ingest — they exist for humans + the lint pass.

## Citation format

Inline citations use `[source-slug, page-or-paragraph]`. The source-slug
matches an entry in the `kb_sources` table. Examples:

- `[ksu-mf743, p.12]`
- `[irac-moa-v11.1]`
- `[epa-ppls-spinosad]`

## Anti-rules

- Never recommend a chemical without an MOA group.
- Never assert a threshold without a citation.
- Never invent a label restriction (REI / PHI) that isn't in the cited
  EPA PPLS entry.
