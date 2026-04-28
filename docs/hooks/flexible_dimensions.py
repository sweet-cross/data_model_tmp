"""mkdocs hook: drive flexible-dimension docs from the root-level `registry` module.

Thin wrapper around :mod:`docs.hooks._yaml_contract_hooks`. Nav + stub
pages come from the shared helpers; per-contract CSVs (for entries with
``show_data=True``) are emitted by the shared ``write_workbook_csvs``
helper and land alongside the regular-dimension CSVs produced by
:mod:`dimensions`.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# `SHOW_CONTRACTS_IN_NAV` is the single toggle shared by every contract-type
# hook in this repo. See docs/hooks/_yaml_contract_hooks.py for the full
# comment — flip it there, not here.
from _yaml_contract_hooks import (  # noqa: E402
    inject_nav_entries,
    inject_stub_files_and_downloads,
    write_workbook_csvs,
)
from registry import (  # noqa: E402
    DIMENSIONS_XLSX,
    DIMENSIONS_YAML_DIR,
    dimensions_version,
    flexible_dimension_registry,
)

_SECTION_PATH = ["Dimensions", "Flexible Dimensions"]
_PAGE_SUBPATH = "dimensions/flexible"
_DOWNLOAD_SUBPATH = "dimensions"
_MACRO_NAME = "render_flexible_dimension"


def on_config(config):
    return inject_nav_entries(
        config, _SECTION_PATH, flexible_dimension_registry, _PAGE_SUBPATH,
    )


def on_files(files, config):
    return inject_stub_files_and_downloads(
        files,
        config,
        registry=flexible_dimension_registry,
        yaml_dir=DIMENSIONS_YAML_DIR,
        page_subpath=_PAGE_SUBPATH,
        download_subpath=_DOWNLOAD_SUBPATH,
        macro_name=_MACRO_NAME,
    )


def on_post_build(config, **kwargs):
    """Emit per-contract CSVs for flexible-dimension entries with show_data=True.

    Also re-emits them under ``downloads/dimensions/v<version>/`` when a
    bundle version is set, mirroring the snapshot layout written by
    :mod:`dimensions`.
    """
    write_workbook_csvs(
        config,
        DIMENSIONS_XLSX,
        flexible_dimension_registry,
        _DOWNLOAD_SUBPATH,
        include_item=lambda item: item.show_data,
    )
    version = dimensions_version()
    if version == "unversioned":
        return
    write_workbook_csvs(
        config,
        DIMENSIONS_XLSX,
        flexible_dimension_registry,
        f"{_DOWNLOAD_SUBPATH}/v{version}",
        include_item=lambda item: item.show_data,
    )
