"""mkdocs hook: drive assumption docs from the root-level `registry` module.

Three lifecycle steps:

  * ``on_config``  — append one nav entry per registered assumption under the
                      nested ``Variables > Assumptions:`` section in mkdocs.yml.
  * ``on_files``   — inject one virtual stub markdown page per registered
                      assumption, and register the source yaml contracts as
                      binary downloads (shipped verbatim to
                      ``site/downloads/assumptions/<name>.yaml``).

The registry is the single source of truth: edit ``registry.py`` at the
project root and rebuild — nav, pages, and downloads update.
"""

import sys
from pathlib import Path

import yaml

from mkdocs.structure.files import File, InclusionLevel

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from registry import (  # noqa: E402
    ASSUMPTIONS_YAML_DIR,
    assumption_registry,
)

VARIABLES_SECTION_TITLE = "Variables"
ASSUMPTIONS_SECTION_TITLE = "Assumptions"
STUB_TEMPLATE = '# {title}\n\n{{{{ render_assumption("{name}") }}}}\n'


def _title_for(contract_file: str, fallback: str) -> str:
    """Return the yaml ``title`` for an assumption, falling back to the registry name."""
    yaml_path = ASSUMPTIONS_YAML_DIR / f"{contract_file}.yaml"
    with yaml_path.open("r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}
    return str(meta.get("title") or fallback).strip()


def _find_section(nav: list, title: str) -> list | None:
    """Return the children list of the top-level nav section with this title, or None."""
    for entry in nav:
        if isinstance(entry, dict) and title in entry:
            children = entry[title]
            if children is None:
                entry[title] = []
                return entry[title]
            return children
    return None


def on_config(config):
    """Append a nav entry per registered assumption under Variables > Assumptions.

    The user keeps a placeholder section in mkdocs.yml::

        nav:
          - Variables:
              - Assumptions:
                  - Overview: variables/assumptions/index.md

    and this hook fills in the per-assumption pages from the registry.
    """
    nav = config.get("nav") or []
    variables_children = _find_section(nav, VARIABLES_SECTION_TITLE)
    if variables_children is None:
        return config
    assumptions_children = _find_section(
        variables_children, ASSUMPTIONS_SECTION_TITLE
    )
    if assumptions_children is None:
        return config
    for name in assumption_registry:
        assumptions_children.append({name: f"variables/assumptions/{name}.md"})
    return config


def on_files(files, config):
    """Inject stub markdown pages + register yaml contract downloads.

    For every registered assumption:

      * a virtual markdown page at ``variables/assumptions/<name>.md`` whose
        body is just a ``render_assumption`` macro call;
      * a binary asset at ``downloads/assumptions/<name>.yaml`` — the source
        yaml copied verbatim. Marked ``NOT_IN_NAV`` explicitly so mkdocs'
        link validator keeps it in the built site (without an explicit
        inclusion level the file defaults to UNDEFINED, which the validator
        treats as excluded).
    """
    for name, item in assumption_registry.items():
        title = _title_for(item.contract_file, name)
        files.append(
            File.generated(
                config,
                f"variables/assumptions/{name}.md",
                content=STUB_TEMPLATE.format(title=title, name=name),
            )
        )
        yaml_src = ASSUMPTIONS_YAML_DIR / f"{item.contract_file}.yaml"
        if yaml_src.is_file():
            files.append(
                File.generated(
                    config,
                    src_uri=f"downloads/assumptions/{name}.yaml",
                    abs_src_path=str(yaml_src),
                    inclusion=InclusionLevel.NOT_IN_NAV,
                )
            )
    return files
