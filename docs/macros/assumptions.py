"""mkdocs-macros module: render scenario-assumption contract pages.

Thin wrapper over :mod:`contracts`. This module only wires the assumption
registry, yaml directory, URL layout, and download path into the shared
``render_contract_page`` / ``render_contract_overview`` helpers.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from contracts import (  # noqa: E402
    load_contract,
    render_contract_overview,
    render_contract_page,
)
from registry import (  # noqa: E402
    ASSUMPTIONS_YAML_DIR,
    assumption_registry,
    dimension_registry,
)

# Assumption pages live at variables/assumptions/<name>/ with
# use_directory_urls: true, i.e. three directory levels below the site root.
_ASSUMPTION_PAGE_DEPTH = 3


def render_assumption(name: str) -> str:
    """Macro: return the full HTML block for a single assumption page."""
    if name not in assumption_registry:
        raise KeyError(
            f'Assumption "{name}" is referenced from a docs page but is not '
            f"in registry.py:assumption_registry. "
            f"Add a ContractRegistryItem for it."
        )
    item = assumption_registry[name]
    yaml_path = ASSUMPTIONS_YAML_DIR / f"{item.contract_file}.yaml"
    meta = load_contract(str(yaml_path))
    download_url = f"../../../downloads/assumptions/{name}.yaml"
    return render_contract_page(
        name, meta, download_url, _ASSUMPTION_PAGE_DEPTH, dimension_registry,
    )


def render_assumption_index() -> str:
    """Macro: return the sortable overview table for the assumptions section."""
    return render_contract_overview(assumption_registry, ASSUMPTIONS_YAML_DIR)


def register(env):
    """Register this module's macros with the mkdocs-macros Jinja environment."""
    env.macro(render_assumption)
    env.macro(render_assumption_index)
