"""mkdocs-macros module: render dimension trees and the dimension index."""

import html
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

# registry.py lives at <project_root>/registry.py; this file at
# <project_root>/docs/macros/dimensions.py. The project root is not on sys.path
# when mkdocs loads the macros module, so add it explicitly.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from registry import (  # noqa: E402
    DIMENSIONS_XLSX,
    DIMENSIONS_YAML_DIR,
    dimension_registry,
)

MAX_DEPTH = 3


@lru_cache(maxsize=None)
def _load_yaml(contract_file: str) -> dict:
    """Read and parse the metadata YAML for a dimension. Cached per build."""
    with (DIMENSIONS_YAML_DIR / f"{contract_file}.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=None)
def _load_sheet(sheet_name: str) -> pd.DataFrame:
    """Read a dimension sheet from the workbook into a DataFrame. Cached per build."""
    df = pd.read_excel(DIMENSIONS_XLSX, sheet_name=sheet_name)
    return df[["id", "level", "parent_id", "label", "description"]].copy()


def _norm_key(value) -> object:
    """Coerce a parent_id cell to None when missing; pass through str/int otherwise."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _build_tree(df: pd.DataFrame) -> tuple[list[dict], dict[object, list[dict]]]:
    """Group rows by parent_id and return (root nodes, parent → children map)."""
    nodes = df.to_dict(orient="records")
    children: dict[object, list[dict]] = {}
    for n in nodes:
        n["parent_id"] = _norm_key(n["parent_id"])
        children.setdefault(n["parent_id"], []).append(n)
    return children.get(None, []), children


def _clean(value) -> str:
    """Strip a value to a printable string; return '' for None / NaN / 'nan'."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def contract_type_label(meta: dict) -> str:
    """Return `contract_type` from a metadata dict, defaulting to 'General'.

    Centralised so future macros (beyond dimensions) can reuse the same fallback.
    """
    return _clean(meta.get("contract_type")) or "General"


def _render_header(node: dict) -> str:
    """Render the `id label` header row, escaping for HTML. Drops the label if absent."""
    node_id = _clean(node["id"])
    label = _clean(node.get("label"))
    id_html = f'<code class="dim-id">{html.escape(node_id)}</code>'
    if label:
        return f'{id_html}<span class="dim-label">&nbsp;{html.escape(label)}</span>'
    return id_html


def _render_node(node: dict, children_map: dict, depth: int) -> str:
    """Recursively render one node as a card. Leaves use the same card markup as nodes —
    they are wrapped in `<details>` too but get no children block and no `open` attribute,
    so they look identical to a collapsed node. CSS disables their toggle affordance.
    """
    kids = children_map.get(node["id"], [])
    is_leaf = not kids or depth >= MAX_DEPTH
    level_cls = f"dim-level-{min(depth, MAX_DEPTH)}"
    leaf_cls = " dim-leaf" if is_leaf else ""
    header = _render_header(node)
    desc = _clean(node.get("description"))
    desc_html = f'<div class="dim-desc">{html.escape(desc)}</div>' if desc else ""
    if is_leaf:
        children_html = ""
    else:
        kids_html = "".join(_render_node(c, children_map, depth + 1) for c in kids)
        children_html = f'<div class="dim-children">{kids_html}</div>'
    return (
        f'<details class="dim-card{leaf_cls} {level_cls}">'
        f'<summary class="dim-head">{header}</summary>'
        f'{desc_html}'
        f'{children_html}'
        f'</details>'
    )


def _render_downloads(name: str) -> str:
    """Render the row of CSV + Excel download buttons for a dimension page."""
    csv_href = f"../../downloads/dimensions/{name}.csv"
    xlsx_href = "../../downloads/dimensions.xlsx"
    return (
        '<div class="dim-downloads">'
        f'<a class="dim-download-btn" href="{csv_href}" download>Download CSV</a>'
        f'<a class="dim-download-btn" href="{xlsx_href}" download>Download all dimensions (xlsx)</a>'
        '</div>'
    )


def render_dimension(name: str) -> str:
    """Macro: return the full HTML block for a single dimension page (downloads + tree).

    Fails the build with a clear message if the page references a dimension not
    listed in `registry.dimension_registry` — the nav is the source of truth
    for which dimensions are documented, but the registry must have a matching
    entry to resolve the YAML and Excel sheet. `index_only` dimensions have no
    page by design and should never reach this macro; if they do, the hook
    configuration has drifted from the registry.
    """
    if name not in dimension_registry:
        raise KeyError(
            f'Dimension "{name}" is referenced from a docs page but is not '
            f'in registry.py:dimension_registry. '
            f'Add a DimensionRegistryItem for it.'
        )
    item = dimension_registry[name]
    if item.index_only:
        raise ValueError(
            f'Dimension "{name}" is marked index_only in the registry; '
            f'no per-dimension page should be generated for it.'
        )
    meta = _load_yaml(item.contract_file)
    df = _load_sheet(item.sheet_name)
    roots, children_map = _build_tree(df)
    contract_name = _clean(meta.get("name")) or name
    ctype = contract_type_label(meta)
    desc = _clean(meta.get("description"))
    meta_rows = [
        ('Contract Name', f'<code>{html.escape(contract_name)}</code>'),
        ('Contract Type', html.escape(ctype)),
    ]
    if desc:
        meta_rows.append(('Description', html.escape(desc)))
    meta_html = '<dl class="dim-meta">' + "".join(
        f'<dt>{label}</dt><dd>{value}</dd>' for label, value in meta_rows
    ) + '</dl>'
    tree_html = "".join(_render_node(r, children_map, 0) for r in roots)
    return (
        '<div class="dim-page" markdown="0">'
        f'{_render_downloads(name)}'
        f'{meta_html}'
        f'<div class="dim-tree">{tree_html}</div>'
        '</div>'
    )


def render_dimension_index() -> str:
    """Macro: return an HTML table of all registered dimensions for the overview page.

    The table is marked `sortable` so the vendored tablesort.js wires click-to-sort
    on the header row. The first cell holds a link; a CSS overlay on that link
    stretches across the whole row so clicking anywhere on the row navigates.
    """
    rows = []
    for name, reg in dimension_registry.items():
        meta = _load_yaml(reg.contract_file)
        title = _clean(meta.get("title")) or name
        desc = _clean(meta.get("description"))
        name_html = html.escape(name)
        if reg.index_only:
            # No per-dimension page exists — render the name as plain code and
            # skip the row-overlay styling (class difference suppresses it).
            name_cell = f'<code>{name_html}</code>'
            row_class = "dim-index-row dim-index-row-static"
        else:
            name_cell = f'<a href="{name_html}/"><code>{name_html}</code></a>'
            row_class = "dim-index-row"
        rows.append(
            f'<tr class="{row_class}">'
            f'<td class="dim-index-name">{name_cell}</td>'
            f'<td>{html.escape(title)}</td>'
            f'<td>{html.escape(desc)}</td>'
            '</tr>'
        )
    if not rows:
        return '<p><em>No dimensions registered.</em></p>'
    return (
        '<div class="dim-index" markdown="0">'
        '<table class="dim-index-table sortable">'
        '<thead><tr>'
        '<th>Name</th><th>Title</th><th>Description</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
        '</div>'
    )


def define_env(env):
    """mkdocs-macros entry point: register macros with the Jinja environment."""
    env.macro(render_dimension)
    env.macro(render_dimension_index)
