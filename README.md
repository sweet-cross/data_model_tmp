# Cross Data Model Documentation

Source for the [Cross Data Model](https://github.com/sweet-cross/cross_back) documentation site (mkdocs + Material).

## Local development

```bash
uv sync
uv run mkdocs serve         # live preview at http://127.0.0.1:8000
uv run mkdocs build --strict  # production build
```

## Adding a dimension to the docs

`create_docs/registry.py` is the **single source of truth** for which dimensions are documented. Adding to it is enough — the build hook injects the page, the nav entry, and the download artefacts at build time. `mkdocs.yml` does not need to change.

### Steps

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

3. **Registry.** Add an entry in [create_docs/registry.py](create_docs/registry.py):
    ```python
    "dim_<name>": DimensionRegistryItem(
        contract_file="dim_<name>",
        sheet_name="dim_<name>",
    ),
    ```

4. **Build.** `uv run mkdocs serve` (or `build --strict`). The dimension appears in the top nav, on the overview index, and exposes a per-dimension CSV plus the shared "Download all dimensions (xlsx)" link.

That's it — no `mkdocs.yml` edit, no stub file to commit.

### What the hook does

[docs/hooks/dimensions.py](docs/hooks/dimensions.py) wires three mkdocs lifecycle steps to the registry:

- `on_config` — appends one nav entry per registered dimension under the `Dimensions:` placeholder defined in `mkdocs.yml`.
- `on_files` — injects a virtual stub markdown page (`dimensions/dim_<name>.md`) for each registered dimension. The stub just calls the `render_dimension(name)` macro.
- `on_post_build` — writes `site/downloads/dimensions.xlsx` (the original workbook copied verbatim) and `site/downloads/dimensions/dim_<name>.csv` for each registered dimension.

If `mkdocs.yml` ever loses the `Dimensions:` section header, the nav-injection step quietly does nothing — keep this skeleton in `mkdocs.yml`:

```yaml
nav:
  - Home: index.md
  - Dimensions:
      - Overview: dimensions/index.md
```

## How the rendering works

- [docs/macros/dimensions.py](docs/macros/dimensions.py) — mkdocs-macros module. Reads YAML metadata and the matching Excel sheet at build time, builds the parent → children tree, and emits nested `<details>` cards. Exposes the macros `render_dimension(name)` and `render_dimension_index()`. Raises a clear `KeyError` (which fails the build) if a page references a dimension missing from the registry.
- [docs/hooks/dimensions.py](docs/hooks/dimensions.py) — registry-driven nav, virtual stub pages, and download artefacts (see above).
- [docs/stylesheets/dimensions.css](docs/stylesheets/dimensions.css) — card / chevron / button styling, dark-mode safe via Material's CSS variables.
- [create_docs/registry.py](create_docs/registry.py) — the registry itself plus the `DIMENSIONS_YAML_DIR` and `DIMENSIONS_XLSX` path constants used by the macro and hook.
