"""mkdocs hook: drive dimension docs from the root-level `registry` module.

Three lifecycle steps:

  * `on_config`     — append one nav entry per registered dimension under
                       the existing `Dimensions:` section in mkdocs.yml.
  * `on_files`      — inject one virtual stub markdown page per registered
                       dimension; the stub just calls `render_dimension(name)`.
  * `on_post_build` — write the per-dimension CSV downloads and the shared
                       full-workbook xlsx into <site>/downloads/.

The registry is the single source of truth: edit `registry.py` at the project
root and rebuild — nav, pages, and downloads update.
"""

import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml

from mkdocs.structure.files import File

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from registry import (  # noqa: E402
    DIMENSIONS_XLSX,
    DIMENSIONS_YAML_DIR,
    dimension_registry,
)

DIM_SECTION_TITLE = "Dimensions"
STUB_TEMPLATE = '# {title}\n\n{{{{ render_dimension("{name}") }}}}\n'


def _title_for(contract_file: str, fallback: str) -> str:
    """Read the YAML metadata and return its `title`, falling back to the dimension name."""
    yaml_path = DIMENSIONS_YAML_DIR / f"{contract_file}.yaml"
    with yaml_path.open("r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}
    return (meta.get("title") or fallback).strip()


def on_config(config):
    """Append one nav entry per registered dimension under the Dimensions section.

    The user keeps a placeholder section in mkdocs.yml::

        nav:
          - Dimensions:
              - Overview: dimensions/index.md

    and this hook adds the per-dimension pages from the registry.
    """
    nav = config.get("nav") or []
    for entry in nav:
        if isinstance(entry, dict) and DIM_SECTION_TITLE in entry:
            children = entry[DIM_SECTION_TITLE] or []
            for name, item in dimension_registry.items():
                if item.index_only:
                    continue
                children.append({name: f"dimensions/{name}.md"})
            entry[DIM_SECTION_TITLE] = children
            break
    return config


def on_files(files, config):
    """Inject one virtual stub markdown file per renderable dimension.

    `index_only` dimensions are intentionally skipped — they appear in the
    overview table as plain rows with no link target.
    """
    for name, item in dimension_registry.items():
        if item.index_only:
            continue
        title = _title_for(item.contract_file, name)
        files.append(
            File.generated(
                config,
                f"dimensions/{name}.md",
                content=STUB_TEMPLATE.format(title=title, name=name),
            )
        )
    return files


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
