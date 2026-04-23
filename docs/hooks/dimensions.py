"""mkdocs hook: drive dimension docs from the root-level `registry` module.

Thin wrapper around :mod:`docs.hooks._yaml_contract_hooks` for the shared
nav + stub-page plumbing, plus a dimension-specific `on_post_build` that
emits the workbook and per-dimension CSV downloads.

The registry is the single source of truth: edit `registry.py` at the
project root and rebuild — nav, pages, and downloads update.
"""

import shutil
import sys
from pathlib import Path

import pandas as pd

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
)
from registry import (  # noqa: E402
    DIMENSIONS_XLSX,
    DIMENSIONS_YAML_DIR,
    dimension_registry,
)

_SECTION_PATH = ["Dimensions"]
_PAGE_SUBPATH = "dimensions"
_MACRO_NAME = "render_dimension"


def _renderable_registry() -> dict:
    """Registry restricted to dimensions that get a per-page render.

    `index_only` entries appear in the overview as plain rows with no link
    target — they are intentionally excluded from nav injection and stub
    generation.
    """
    return {
        name: item
        for name, item in dimension_registry.items()
        if not item.index_only
    }


def on_config(config):
    return inject_nav_entries(
        config, _SECTION_PATH, _renderable_registry(), _PAGE_SUBPATH,
    )


def on_files(files, config):
    return inject_stub_files_and_downloads(
        files,
        config,
        registry=_renderable_registry(),
        yaml_dir=DIMENSIONS_YAML_DIR,
        page_subpath=_PAGE_SUBPATH,
        macro_name=_MACRO_NAME,
    )


def on_post_build(config, **kwargs):
    """Write download artefacts under <site>/downloads/ after the build finishes.

    Produces:
      - downloads/dimensions.xlsx — the original workbook copied verbatim.
      - downloads/dimensions/<name>.csv — one CSV per registered dimension,
        UTF-8 with BOM so it opens cleanly in Excel.
    """
    site_dir = Path(config["site_dir"])
    downloads = site_dir / "downloads"
    per_dim = downloads / "dimensions"
    per_dim.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(DIMENSIONS_XLSX, downloads / "dimensions.xlsx")

    for name, item in dimension_registry.items():
        df = pd.read_excel(DIMENSIONS_XLSX, sheet_name=item.sheet_name)
        df.to_csv(per_dim / f"{name}.csv", index=False, encoding="utf-8-sig")
