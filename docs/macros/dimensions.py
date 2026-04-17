"""mkdocs-macros module: render dimension trees and the dimension index."""

import html
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

# create_docs/ lives at <project_root>/create_docs/, this file at
# <project_root>/docs/macros/dimensions.py — neither parent is on sys.path
# when mkdocs loads the macros module, so add the project root explicitly.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from create_docs.registry import (  # noqa: E402
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
    listed in `create_docs.registry.dimension_registry` — the nav is the source
    of truth for which dimensions are documented, but the registry must have a
    matching entry to resolve the YAML and Excel sheet.
    """
    if name not in dimension_registry:
        raise KeyError(
            f'Dimension "{name}" is referenced from a docs page but is not '
            f'in create_docs/registry.py:dimension_registry. '
            f'Add a DimensionRegistryItem for it.'
        )
    item = dimension_registry[name]
    meta = _load_yaml(item.contract_file)
    df = _load_sheet(item.sheet_name)
    roots, children_map = _build_tree(df)
    desc = _clean(meta.get("description"))
    desc_html = f'<p class="dim-page-desc">{html.escape(desc)}</p>' if desc else ""
    tree_html = "".join(_render_node(r, children_map, 0) for r in roots)
    return (
        '<div class="dim-page" markdown="0">'
        f'{_render_downloads(name)}'
        f'{desc_html}'
        f'<div class="dim-tree">{tree_html}</div>'
        '</div>'
    )


def render_dimension_index() -> str:
    """Macro: return the HTML list of all registered dimensions for the overview page."""
    items = []
    for name, reg in dimension_registry.items():
        meta = _load_yaml(reg.contract_file)
        title = _clean(meta.get("title")) or name
        desc = _clean(meta.get("description"))
        desc_html = f'<p>{html.escape(desc)}</p>' if desc else ""
        items.append(
            '<li class="dim-index-item">'
            f'<a href="{name}/"><strong>{html.escape(title)}</strong> '
            f'<code>{html.escape(name)}</code></a>'
            f'{desc_html}'
            '</li>'
        )
    if not items:
        return '<p><em>No dimensions registered.</em></p>'
    return f'<ul class="dim-index">{"".join(items)}</ul>'


def define_env(env):
    """mkdocs-macros entry point: register macros with the Jinja environment."""
    env.macro(render_dimension)
    env.macro(render_dimension_index)
