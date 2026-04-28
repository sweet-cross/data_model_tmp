"""mkdocs hook: drive dimension docs from the root-level `registry` module.

Thin wrapper around :mod:`docs.hooks._yaml_contract_hooks`. The registry is
the single source of truth: edit ``registry.py`` at the project root and
rebuild — nav, pages, and downloads update.

This hook additionally copies the shared workbook to the site's downloads
folder in ``on_post_build``. Per-dimension CSVs are produced by the
shared ``write_workbook_csvs`` helper so the logic stays in the core
module; flexible dimensions reuse the same helper.
"""

import shutil
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
    dimension_registry,
    dimensions_version,
)

_SECTION_PATH = ["Dimensions", "Dimensions"]
_PAGE_SUBPATH = "dimensions/dimensions"
_DOWNLOAD_SUBPATH = "dimensions"
_MACRO_NAME = "render_dimension"


def _renderable_registry() -> dict:
    """Registry restricted to dimensions that get a per-page render.

    `index_only` entries appear in the overview as plain rows with no link
    target — they are intentionally excluded from nav injection and stub
    generation.
    """
    return {
        name: item for name, item in dimension_registry.items() if not item.index_only
    }


def on_config(config):
    return inject_nav_entries(
        config,
        _SECTION_PATH,
        _renderable_registry(),
        _PAGE_SUBPATH,
    )


def on_files(files, config):
    return inject_stub_files_and_downloads(
        files,
        config,
        registry=_renderable_registry(),
        yaml_dir=DIMENSIONS_YAML_DIR,
        page_subpath=_PAGE_SUBPATH,
        download_subpath=_DOWNLOAD_SUBPATH,
        macro_name=_MACRO_NAME,
    )


def on_post_build(config, **kwargs):
    """Ship the shared workbook and per-dimension CSVs to the site.

    Produces:
      - downloads/dimensions.xlsx — the original workbook copied verbatim
        (canonical, latest-only path; existing bookmarks stay valid).
      - downloads/dimensions/<name>.csv — one CSV per registered dimension,
        emitted by the shared ``write_workbook_csvs`` helper (every entry
        is included, including ``index_only`` rows the overview links to).
      - downloads/dimensions/v<version>/dimensions.xlsx and
        downloads/dimensions/v<version>/<name>.csv — versioned snapshots
        consumers can pin to. Mirrors the canonical layout under a single
        version-prefixed directory. Skipped when no VERSION file is present
        (returns the sentinel ``"unversioned"``).
    """
    site_dir = Path(config["site_dir"])
    downloads = site_dir / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DIMENSIONS_XLSX, downloads / "dimensions.xlsx")
    write_workbook_csvs(
        config,
        DIMENSIONS_XLSX,
        dimension_registry,
        _DOWNLOAD_SUBPATH,
    )

    version = dimensions_version()
    if version == "unversioned":
        return

    versioned_dir = downloads / _DOWNLOAD_SUBPATH / f"v{version}"
    versioned_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DIMENSIONS_XLSX, versioned_dir / "dimensions.xlsx")
    # Re-emit per-dimension CSVs into the versioned subdir using the same
    # helper, repointed at v<version>/.
    write_workbook_csvs(
        config,
        DIMENSIONS_XLSX,
        dimension_registry,
        f"{_DOWNLOAD_SUBPATH}/v{version}",
    )
