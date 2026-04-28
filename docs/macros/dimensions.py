"""mkdocs-macros module: render dimension trees and the dimension index.

Dimensions are hierarchical reference data (up to three levels). Each page
combines the shared contract primitives from :mod:`contracts` — downloads,
metadata header — with a dimension-specific collapsible card tree built from
the workbook.
"""

import html
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from contracts import (  # noqa: E402
    clean,
    load_contract,
    render_contract_header,
    render_contract_index,
    render_downloads,
    workbook_dimension_downloads,
)
from registry import (  # noqa: E402
    DIMENSIONS_XLSX,
    DIMENSIONS_YAML_DIR,
    dimension_registry,
    dimensions_version,
)

MAX_DEPTH = 3

# Dimension pages live at dimensions/dimensions/<name>/ with
# use_directory_urls: true — three directory levels below the site root.
# Path matches ``_PAGE_SUBPATH`` in docs/hooks/dimensions.py; update both
# together.
_DIM_PAGE_DEPTH = 3


@lru_cache(maxsize=None)
def _load_sheet(sheet_name: str) -> pd.DataFrame:
    """Read a dimension sheet from the workbook into a DataFrame. Cached per build."""
    df = pd.read_excel(DIMENSIONS_XLSX, sheet_name=sheet_name)
    return df[["id", "level", "parent_id", "label", "description"]].copy()


def _yaml_path(contract_file: str) -> str:
    """Return the yaml path as a string for :func:`contracts.load_contract`."""
    return str(DIMENSIONS_YAML_DIR / f"{contract_file}.yaml")


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


def _render_header(node: dict) -> str:
    """Render the `id label` header row, escaping for HTML. Drops the label if absent."""
    node_id = clean(node["id"])
    label = clean(node.get("label"))
    id_html = f'<code class="dim-id">{html.escape(node_id)}</code>'
    if label:
        return f'{id_html}<span class="dim-label">&nbsp;{html.escape(label)}</span>'
    return id_html


def _render_node(node: dict, children_map: dict, depth: int) -> str:
    """Recursively render one node as a card.

    Leaves use the same card markup as nodes — they are wrapped in
    ``<details>`` too but get no children block and no ``open`` attribute, so
    they look identical to a collapsed node. CSS disables their toggle
    affordance.
    """
    kids = children_map.get(node["id"], [])
    is_leaf = not kids or depth >= MAX_DEPTH
    level_cls = f"dim-level-{min(depth, MAX_DEPTH)}"
    leaf_cls = " dim-leaf" if is_leaf else ""
    header = _render_header(node)
    desc = clean(node.get("description"))
    desc_html = f'<div class="dim-desc">{html.escape(desc)}</div>' if desc else ""
    if is_leaf:
        children_html = ""
    else:
        kids_html = "".join(_render_node(c, children_map, depth + 1) for c in kids)
        children_html = f'<div class="dim-children">{kids_html}</div>'
    return (
        f'<details class="dim-card{leaf_cls} {level_cls}">'
        f'<summary class="dim-head">{header}</summary>'
        f"{desc_html}"
        f"{children_html}"
        "</details>"
    )


def render_dimension(name: str) -> str:
    """Macro: return the full HTML block for a single dimension page.

    Args:
        name: the registry key. Raises ``KeyError`` when not in
            :data:`registry.dimension_registry` and ``ValueError`` when
            ``index_only`` is set (those dimensions have no per-page render).

    Returns:
        HTML string composed of: download buttons, contract metadata header,
        and the collapsible card tree. Wrapped in
        ``<div class="contract-page" markdown="0">`` so mkdocs does not
        re-parse the HTML as markdown.
    """
    if name not in dimension_registry:
        raise KeyError(
            f'Dimension "{name}" is referenced from a docs page but is not '
            f"in registry.py:dimension_registry. "
            f"Add a DimensionRegistryItem for it."
        )
    item = dimension_registry[name]
    if item.index_only:
        raise ValueError(
            f'Dimension "{name}" is marked index_only in the registry; '
            f"no per-dimension page should be generated for it."
        )
    meta = load_contract(_yaml_path(item.contract_file))
    df = _load_sheet(item.sheet_name)
    roots, children_map = _build_tree(df)
    version = dimensions_version()
    downloads_html = render_downloads(
        workbook_dimension_downloads(name, _DIM_PAGE_DEPTH, version=version)
    )
    header_html = render_contract_header(name, meta, version=version)
    tree_html = "".join(_render_node(r, children_map, 0) for r in roots)
    return (
        '<div class="contract-page" markdown="0">'
        f"{header_html}"
        f'<div class="dim-tree">{tree_html}</div>'
        f"{downloads_html}"
        "</div>"
    )


def render_dimensions_version_badge() -> str:
    """Macro: render a small bundle-version badge for the dimensions overview.

    Returns:
        HTML string (a single ``<div class="dimensions-version-badge">``).
        Reads the bundle version from :func:`registry.dimensions_version`.
    """
    v = dimensions_version()
    display = f"v{v}" if v != "unversioned" else v
    return (
        '<div class="dimensions-version-badge">'
        '<span class="dimensions-version-label">Dimension data bundle:</span> '
        f"<code>{html.escape(display)}</code>"
        "</div>"
    )


def render_dimension_index() -> str:
    """Macro: return the sortable overview table of every registered dimension.

    Returns:
        HTML table; index-only dimensions render as plain-text rows (no link)
        because they have no per-dimension page to navigate to.
    """
    entries: list[tuple[str, str, str, str | None]] = []
    for name, item in dimension_registry.items():
        meta = load_contract(_yaml_path(item.contract_file))
        title = clean(meta.get("title")) or name
        desc = clean(meta.get("description"))
        href = None if item.index_only else f"{name}/"
        entries.append((name, title, desc, href))
    return render_contract_index(entries)


def register(env):
    """Register this module's macros with the mkdocs-macros Jinja environment."""
    env.macro(render_dimension)
    env.macro(render_dimension_index)
    env.macro(render_dimensions_version_badge)
