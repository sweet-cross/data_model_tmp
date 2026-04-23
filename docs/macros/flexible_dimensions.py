"""mkdocs-macros module: render flexible-dimension contract pages.

Flexible dimensions are flat-schema contracts whose data lives as a sheet in
the shared dimensions workbook. The page composition mirrors assumption/
result pages (yaml metadata + Frictionless fields table) with one extra
piece: when the registry entry has ``show_data=True`` the sheet is also
rendered inline as a sortable data table, and CSV/xlsx download buttons are
added next to the yaml one.
"""

import sys
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from contracts import (  # noqa: E402
    load_contract,
    render_contract_overview,
    render_contract_page,
    render_data_table,
    workbook_dimension_downloads,
)
from registry import (  # noqa: E402
    DIMENSIONS_XLSX,
    DIMENSIONS_YAML_DIR,
    dimension_registry,
    flexible_dimension_registry,
)

# Flexible-dimension pages live at dimensions/flexible/<name>/ with
# use_directory_urls: true, i.e. three directory levels below the site root.
_FLEX_DIM_PAGE_DEPTH = 3


def render_flexible_dimension(name: str) -> str:
    """Macro: return the full HTML block for a single flexible-dimension page."""
    if name not in flexible_dimension_registry:
        raise KeyError(
            f'Flexible dimension "{name}" is referenced from a docs page '
            f"but is not in registry.py:flexible_dimension_registry. "
            f"Add a FlexibleDimensionRegistryItem for it."
        )
    item = flexible_dimension_registry[name]
    meta = load_contract(str(DIMENSIONS_YAML_DIR / f"{item.contract_file}.yaml"))
    downloads = workbook_dimension_downloads(
        name, _FLEX_DIM_PAGE_DEPTH, include_csv=item.show_data,
    )
    extra = ""
    if item.show_data:
        df = pd.read_excel(DIMENSIONS_XLSX, sheet_name=item.sheet_name)
        schema = meta.get("tableschema") or {}
        extra = render_data_table(df, schema.get("fields") or [])
    return render_contract_page(
        name, meta, downloads, _FLEX_DIM_PAGE_DEPTH, dimension_registry,
        extra_body_html=extra,
    )


def render_flexible_dimension_index() -> str:
    """Macro: return the sortable overview table for the flexible-dimensions section."""
    return render_contract_overview(
        flexible_dimension_registry, DIMENSIONS_YAML_DIR,
    )


def register(env):
    """Register this module's macros with the mkdocs-macros Jinja environment."""
    env.macro(render_flexible_dimension)
    env.macro(render_flexible_dimension_index)
