"""mkdocs hook: drive assumption docs from the root-level `registry` module.

Thin wrapper around :mod:`docs.hooks._yaml_contract_hooks`. The registry is
the single source of truth: edit ``registry.py`` at the project root and
rebuild — nav, pages, and downloads update.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _yaml_contract_hooks import (  # noqa: E402
    inject_nav_entries,
    inject_stub_files_and_downloads,
)
from registry import (  # noqa: E402
    ASSUMPTIONS_YAML_DIR,
    assumption_registry,
)

_SECTION_PATH = ["Variables", "Assumptions"]
_PAGE_SUBPATH = "variables/assumptions"
_DOWNLOAD_SUBPATH = "assumptions"
_MACRO_NAME = "render_assumption"


def on_config(config):
    return inject_nav_entries(
        config, _SECTION_PATH, assumption_registry, _PAGE_SUBPATH,
        strip_prefix="scenass_",
    )


def on_files(files, config):
    return inject_stub_files_and_downloads(
        files,
        config,
        registry=assumption_registry,
        yaml_dir=ASSUMPTIONS_YAML_DIR,
        page_subpath=_PAGE_SUBPATH,
        download_subpath=_DOWNLOAD_SUBPATH,
        macro_name=_MACRO_NAME,
    )
