"""mkdocs-macros module: render result-contract pages.

Thin wrapper over :mod:`contracts`. This module only wires the result
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
    RESULTS_YAML_DIR,
    dimension_registry,
    result_registry,
)

# Result pages live at variables/results/<name>/ with use_directory_urls: true,
# i.e. three directory levels below the site root.
_RESULT_PAGE_DEPTH = 3


def render_result(name: str) -> str:
    """Macro: return the full HTML block for a single result page."""
    if name not in result_registry:
        raise KeyError(
            f'Result "{name}" is referenced from a docs page but is not '
            f"in registry.py:result_registry. "
            f"Add a ContractRegistryItem for it."
        )
    item = result_registry[name]
    yaml_path = RESULTS_YAML_DIR / f"{item.contract_file}.yaml"
    meta = load_contract(str(yaml_path))
    downloads = [
        (f"../../../downloads/results/{name}.yaml", "Download contract (yaml)"),
    ]
    return render_contract_page(
        name, meta, downloads, _RESULT_PAGE_DEPTH, dimension_registry,
    )


def render_result_index() -> str:
    """Macro: return the sortable overview table for the results section."""
    return render_contract_overview(result_registry, RESULTS_YAML_DIR)


def register(env):
    """Register this module's macros with the mkdocs-macros Jinja environment."""
    env.macro(render_result)
    env.macro(render_result_index)
