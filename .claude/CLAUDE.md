# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                           # install dependencies
uv run mkdocs serve               # live preview at http://127.0.0.1:8000
uv run mkdocs build --strict      # production build (strict = fail on broken links)
```

## Architecture

This is a **registry-driven, data-to-docs pipeline** built with MkDocs. The central source of truth is [registry.py](registry.py), which maps contract names to their source files. Adding a contract is always: drop a data file, add one registry entry, rebuild.

### Three contract types

| Type | Data source | Registry key | Hook | Macro |
|------|-------------|-------------|------|-------|
| Dimensions | YAML metadata + sheet in `data/dimensions/dimensions.xlsx` | `dimension_registry` | [docs/hooks/dimensions.py](docs/hooks/dimensions.py) | [docs/macros/dimensions.py](docs/macros/dimensions.py) |
| Assumptions | YAML in `data/assumptions/` | `assumption_registry` | [docs/hooks/assumptions.py](docs/hooks/assumptions.py) | [docs/macros/assumptions.py](docs/macros/assumptions.py) |
| Results | YAML in `data/results/` | `result_registry` | [docs/hooks/results.py](docs/hooks/results.py) | [docs/macros/results.py](docs/macros/results.py) |

### Build pipeline

Each hook wires three MkDocs lifecycle steps:
- **`on_config`** — appends nav entries per contract (no-op when `SHOW_CONTRACTS_IN_NAV = False`)
- **`on_files`** — injects a virtual stub markdown page per contract (just a macro call) and registers downloadable artefacts
- **`on_post_build`** — (dimensions only) writes CSVs and the workbook into `site/downloads/`

### Shared code

- [docs/hooks/_yaml_contract_hooks.py](docs/hooks/_yaml_contract_hooks.py) — shared nav-injection, stub-page generation, and YAML-download registration for assumptions and results. Contains the `SHOW_CONTRACTS_IN_NAV` toggle (default `False` — contracts are reachable via overview tables but not in the sidebar).
- [docs/macros/contracts.py](docs/macros/contracts.py) — rendering primitives (`load_contract`, `render_contract_header`, `render_primary_key`, `render_fields_table`, `render_contract_index`, `foreign_key_index`, `dimension_page_url`) and the high-level composers `render_contract_page` / `render_contract_overview` that the type-specific macro modules delegate to.
- [docs/stylesheets/contracts.css](docs/stylesheets/contracts.css) — shared card, table, and button styling.

### Foreign key links

Foreign keys whose `reference.resource` names a registered, non-`index_only` dimension automatically become clickable arrows in the rendered fields table — no extra wiring needed.

## Adding a dimension

1. Create `data/dimensions/dim_<name>.yaml` with `name`, `title`, `description`, `contract_type: Dimension`.
2. Add a sheet `dim_<name>` to `data/dimensions/dimensions.xlsx` with columns: `id`, `level` (0–3), `parent_id`, `label`, `description`.
3. Add to `dimension_registry` in [registry.py](registry.py):
   ```python
   "dim_<name>": DimensionRegistryItem(contract_file="dim_<name>", sheet_name="dim_<name>"),
   ```
   Use `index_only=True` for dimensions too large to render as a card tree — they appear as a plain row in the overview with a downloadable CSV but no per-dimension page.

## Adding an assumption or result

1. Create `data/assumptions/<name>.yaml` or `data/results/<name>.yaml` using [Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/) with `name`, `title`, `description`, `contract_type: ValueVariable`, and a `tableschema` block.
2. Add to `assumption_registry` or `result_registry` in [registry.py](registry.py):
   ```python
   "<name>": ContractRegistryItem(contract_file="<name>"),
   ```

## CI/CD

- **`check_excel_changes.yml`** — runs on every PR; validates Excel changes via [.github/scripts/excel_diff.py](.github/scripts/excel_diff.py) and posts a diff report as a PR comment.
- **`main_post_merge.yml`** — triggers the docs build on push to `main`.
- **`build_publish_docs.yml`** — builds with `mkdocs build --strict` and deploys to GitHub Pages (also callable as a reusable workflow).

## `mkdocs.yml` nav skeleton

The hook nav-injection silently does nothing if section headers are missing. Keep at minimum:

```yaml
nav:
  - Home: index.md
  - Dimensions:
      - Overview: dimensions/index.md
  - Variables:
      - Overview: variables/index.md
      - Assumptions:
          - Overview: variables/assumptions/index.md
      - Results:
          - Overview: variables/results/index.md
```
