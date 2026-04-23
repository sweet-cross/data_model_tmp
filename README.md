# Cross Data Model Documentation

Source for the [Cross Data Model](https://github.com/sweet-cross/cross_back) documentation site (mkdocs + Material).

## Local development

```bash
uv sync
uv run mkdocs serve         # live preview at http://127.0.0.1:8000
uv run mkdocs build --strict  # production build
```

## Contract types

The site documents three kinds of contracts, each driven from [registry.py](registry.py):

| Type | Source data | Registry | Hook | Macro module |
| --- | --- | --- | --- | --- |
| Dimensions | YAML metadata + sheet in `data/dimensions/dimensions.xlsx` | `dimension_registry` (`DimensionRegistryItem`) | [docs/hooks/dimensions.py](docs/hooks/dimensions.py) | [docs/macros/dimensions.py](docs/macros/dimensions.py) |
| Assumptions | YAML in `data/assumptions/` | `assumption_registry` (`ContractRegistryItem`) | [docs/hooks/assumptions.py](docs/hooks/assumptions.py) | [docs/macros/assumptions.py](docs/macros/assumptions.py) |
| Results | YAML in `data/results/` | `result_registry` (`ContractRegistryItem`) | [docs/hooks/results.py](docs/hooks/results.py) | [docs/macros/results.py](docs/macros/results.py) |

Shared code:

- [docs/macros/contracts.py](docs/macros/contracts.py) — rendering primitives (`load_contract`, `render_contract_header`, `render_primary_key`, `render_fields_table`, `render_contract_index`, `foreign_key_index`, `dimension_page_url`) and the high-level composers `render_contract_page` / `render_contract_overview` that the yaml-only macro modules delegate to.
- [docs/hooks/_yaml_contract_hooks.py](docs/hooks/_yaml_contract_hooks.py) — shared nav-injection, stub-page generation, and yaml-download registration for assumptions and results. Also hosts the `SHOW_CONTRACTS_IN_NAV` toggle (see below).
- [docs/stylesheets/contracts.css](docs/stylesheets/contracts.css) — card, table, and button styling shared by every contract page.

Adding a contract is always the same shape: drop a YAML (and a workbook sheet for dimensions), add one registry entry, rebuild.

## Adding a dimension

1. **Metadata YAML.** Create `data/dimensions/dim_<name>.yaml`:
    ```yaml
    name: dim_<name>
    title: <Human-readable title>
    description: |
      One or two sentences describing the dimension.
    contract_type: Dimension
    ```

2. **Excel sheet.** Add a sheet named `dim_<name>` to `data/dimensions/dimensions.xlsx`. Required columns:
    | column        | type           | notes                                    |
    | ------------- | -------------- | ---------------------------------------- |
    | `id`          | string         | unique within the sheet                  |
    | `level`       | int (0–3)      | 0 for roots                              |
    | `parent_id`   | string \| null | references another `id`; empty for roots |
    | `label`       | string         | optional, shown next to the id           |
    | `description` | string         | optional, shown as italic line below     |

3. **Registry.** Add an entry in [registry.py](registry.py):
    ```python
    "dim_<name>": DimensionRegistryItem(
        contract_file="dim_<name>",
        sheet_name="dim_<name>",
    ),
    ```

    Pass `index_only=True` for dimensions too large to render as a card tree (e.g. `dim_iso_region`). Those appear as a plain row in the overview table with no per-dimension page. The CSV is still written to `site/downloads/dimensions/` so the data stays downloadable via the shared Excel export on any rendered dimension page.

4. **Build.** `uv run mkdocs serve` (or `build --strict`). The dimension shows up on the Dimensions overview, exposes a per-dimension CSV, and is linked from every foreign-key marker pointing at it.

## Adding an assumption or result

Assumptions and results share one contract shape (yaml only, Frictionless Table Schema).

1. **Contract YAML.** Create `data/assumptions/<name>.yaml` or `data/results/<name>.yaml`:
    ```yaml
    name: <name>
    title: <Human-readable title>
    description: >
      One or two sentences describing the contract.
    contract_type: ValueVariable

    tableschema:
      primaryKey: [scenario_group, scenario_name, scenario_variant, country, year]
      foreignKeys:
        - fields: country
          reference:
            resource: dim_iso_region
            fields: id
      fields:
        - name: country
          type: string
          title: Country Code
          description: ISO 3166-1 alpha-2 country code
          constraints:
            required: true
            maxLength: 8
        # ... more fields
    ```

    Foreign keys whose `reference.resource` names a registered, non-`index_only` dimension become clickable arrows in the rendered fields table — no extra wiring needed.

2. **Registry.** Add an entry in [registry.py](registry.py):
    ```python
    # under assumption_registry
    "<name>": ContractRegistryItem(contract_file="<name>"),

    # or under result_registry
    "<name>": ContractRegistryItem(contract_file="<name>"),
    ```

3. **Build.** `uv run mkdocs build --strict`. The contract shows up on the matching overview (`Variables > Assumptions > Overview` or `Variables > Results > Overview`) and its YAML is served verbatim at `downloads/assumptions/<name>.yaml` / `downloads/results/<name>.yaml`.

## Sidebar visibility — `SHOW_CONTRACTS_IN_NAV`

Every contract type respects one toggle defined at the top of [docs/hooks/_yaml_contract_hooks.py](docs/hooks/_yaml_contract_hooks.py):

```python
SHOW_CONTRACTS_IN_NAV = False
```

- **`False` (default).** The sidebar shows only the three overview pages: `Dimensions > Overview`, `Variables > Assumptions > Overview`, `Variables > Results > Overview`. Per-contract pages are still built and link-validated (registered as `NOT_IN_NAV`); they're reached by clicking a row in the overview table. This keeps the sidebar readable once the registries grow past a handful of entries each.
- **`True`.** Each registered contract also gets a sidebar entry under its type section (dimensions, assumptions, or results).

Flip the value in that one file and all three hooks — [dimensions.py](docs/hooks/dimensions.py), [assumptions.py](docs/hooks/assumptions.py), [results.py](docs/hooks/results.py) — pick it up on the next build. Nothing else needs to change.

## What the hooks do

Each contract-type hook wires the same three mkdocs lifecycle steps to its registry:

- `on_config` — appends one nav entry per registered contract under the relevant section (`Dimensions:`, `Variables > Assumptions:`, `Variables > Results:`). No-op when `SHOW_CONTRACTS_IN_NAV` is `False`.
- `on_files` — injects a virtual stub markdown page per contract (just a macro call) and registers downloadable artefacts (CSV/xlsx for dimensions, YAML for assumptions/results).
- `on_post_build` — (dimensions only) writes the workbook and per-dimension CSVs into `site/downloads/`.

If `mkdocs.yml` ever loses a section header the nav-injection step quietly does nothing — keep this skeleton:

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
