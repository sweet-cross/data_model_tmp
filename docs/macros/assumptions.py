"""mkdocs-macros module: render scenario-assumption contract pages.

Assumption contracts are yaml-only (no bulk workbook). Each registered contract
gets a per-page render of:

  * download buttons (yaml);
  * Contract Name / Contract Type / Description metadata block;
  * primary-key statement;
  * sortable Frictionless fields table with foreign-key markers that link to
    the target dimension page when one exists.

Shared primitives live in :mod:`contracts`; this module only wires the
registry, file layout, and depth into those helpers.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from contracts import (  # noqa: E402
    foreign_key_index,
    load_contract,
    render_contract_header,
    render_contract_index,
    render_downloads,
    render_fields_table,
    render_primary_key,
)
from registry import (  # noqa: E402
    ASSUMPTIONS_YAML_DIR,
    assumption_registry,
    dimension_registry,
)

# Assumption pages live at variables/assumptions/<name>/ with
# use_directory_urls: true, i.e. three directory levels below the site root.
# `render_fields_table` uses this to build relative links to dimension pages.
_ASSUMPTION_PAGE_DEPTH = 3


def _yaml_path(contract_file: str) -> Path:
    """Return the filesystem path of an assumption yaml file."""
    return ASSUMPTIONS_YAML_DIR / f"{contract_file}.yaml"


def render_assumption(name: str) -> str:
    """Macro: return the full HTML block for a single assumption page.

    Args:
        name: the registry key. Raises ``KeyError`` when the page references
            a name missing from :data:`registry.assumption_registry`, so a
            stale hook or hand-edited stub fails the build loudly.

    Returns:
        HTML string wrapped in ``<div class="contract-page" markdown="0">`` so
        mkdocs does not re-parse the content as markdown. Composes the
        primitives from :mod:`contracts` — downloads, header, primary key,
        fields table — into the same visual language used by dimension pages.
    """
    if name not in assumption_registry:
        raise KeyError(
            f'Assumption "{name}" is referenced from a docs page but is not '
            f"in registry.py:assumption_registry. "
            f"Add an AssumptionRegistryItem for it."
        )
    item = assumption_registry[name]
    meta = load_contract(str(_yaml_path(item.contract_file)))
    schema = meta.get("tableschema") or {}
    fields = schema.get("fields") or []
    fk_index = foreign_key_index(schema)
    pk = schema.get("primaryKey") or []
    if isinstance(pk, str):
        pk = [pk]

    downloads_html = render_downloads(
        [(f"../../../downloads/assumptions/{name}.yaml", "Download contract (yaml)")]
    )
    header_html = render_contract_header(name, meta)
    pk_html = render_primary_key(schema)
    fields_html = render_fields_table(
        fields, fk_index, dimension_registry, _ASSUMPTION_PAGE_DEPTH,
        primary_key=pk,
    )
    return (
        '<div class="contract-page" markdown="0">'
        f"{downloads_html}"
        f"{header_html}"
        f"{pk_html}"
        f"{fields_html}"
        "</div>"
    )


def render_assumption_index() -> str:
    """Macro: return the sortable overview table for the assumptions section.

    Returns:
        HTML table listing every entry in :data:`registry.assumption_registry`
        with name, title, and description. Each row links to the per-contract
        page (href ``"<name>/"`` is relative to the index page at
        ``variables/assumptions/``).
    """
    entries: list[tuple[str, str, str, str | None]] = []
    for name, item in assumption_registry.items():
        meta = load_contract(str(_yaml_path(item.contract_file)))
        title = str(meta.get("title") or name).strip()
        desc = str(meta.get("description") or "").strip()
        entries.append((name, title, desc, f"{name}/"))
    return render_contract_index(entries)


def register(env):
    """Register this module's macros with the mkdocs-macros Jinja environment."""
    env.macro(render_assumption)
    env.macro(render_assumption_index)
