"""Shared mkdocs-hook logic for every contract type (dimensions, assumptions, results).

Each contract section needs two common pieces of build-time plumbing:

  * append one nav entry per registered contract under a named section in
    ``mkdocs.yml``;
  * inject a virtual markdown stub page per contract whose body is a single
    macro call.

Yaml-only contract types (assumptions, results) also register the source yaml
as a ``NOT_IN_NAV`` binary download so mkdocs ships it verbatim to
``site/downloads/<type>/<name>.yaml``. Dimension downloads (CSV + workbook)
are produced separately in :mod:`dimensions`'s ``on_post_build``.

The per-type hook modules only supply their registry, paths, nav section
titles, and macro name — the logic lives here. The leading underscore keeps
this module from being picked up as an mkdocs hook itself (hooks are
explicitly listed in ``mkdocs.yml``).
"""

from pathlib import Path

import yaml

from mkdocs.structure.files import File, InclusionLevel

# ---------------------------------------------------------------------------
# Nav-visibility toggle for every contract type (dimensions, assumptions,
# results). This is the single source of truth — flip it here and every
# contract-type hook picks up the change.
#
# When ``False`` the sidebar shows only the three overview pages:
#   - Dimensions > Overview
#   - Variables > Assumptions > Overview
#   - Variables > Results > Overview
# Per-contract pages are still built and link-validated (``NOT_IN_NAV``),
# reachable by clicking a row in the overview table.
#
# When ``True`` each registered contract also gets a sidebar entry.
# ---------------------------------------------------------------------------
SHOW_CONTRACTS_IN_NAV = False


def _title_for(yaml_path: Path, fallback: str) -> str:
    """Return the yaml ``title`` for a contract, falling back to the given name."""
    with yaml_path.open("r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}
    return str(meta.get("title") or fallback).strip()


def _find_section(nav: list, title: str) -> list | None:
    """Return the children list of the top-level nav section with this title."""
    for entry in nav:
        if isinstance(entry, dict) and title in entry:
            children = entry[title]
            if children is None:
                entry[title] = []
                return entry[title]
            return children
    return None


def inject_nav_entries(
    config,
    section_path: list[str],
    registry: dict,
    page_subpath: str,
):
    """Append one nav entry per registry item under a nested nav section.

    Args:
        config: the mkdocs config dict received by ``on_config``.
        section_path: titles of the nav sections to traverse, outer to inner
            (e.g. ``["Variables", "Assumptions"]``). The innermost list is
            the one entries are appended to. If any section in the path is
            missing the config is returned unchanged.
        registry: mapping of registry key → registry item. Only the keys are
            used here.
        page_subpath: URL prefix for the per-contract markdown pages, e.g.
            ``"variables/assumptions"`` — each entry becomes
            ``{name: f"{page_subpath}/{name}.md"}``.

    Returns:
        The (possibly-mutated) config dict.
    """
    if not SHOW_CONTRACTS_IN_NAV:
        return config
    nav = config.get("nav") or []
    children = nav
    for title in section_path:
        children = _find_section(children, title)
        if children is None:
            return config
    for name in registry:
        children.append({name: f"{page_subpath}/{name}.md"})
    return config


def inject_stub_files_and_downloads(
    files,
    config,
    registry: dict,
    yaml_dir: Path,
    page_subpath: str,
    macro_name: str,
    download_subpath: str | None = None,
):
    """Inject per-contract stub pages and (optionally) source yaml downloads.

    For each registry entry:

      * a virtual markdown page at ``<page_subpath>/<name>.md`` whose body is
        ``{{ <macro_name>("<name>") }}`` — the macro is resolved at render
        time by ``mkdocs-macros``;
      * when ``download_subpath`` is given: a binary asset at
        ``downloads/<download_subpath>/<name>.yaml`` — the source yaml copied
        verbatim. Marked ``NOT_IN_NAV`` explicitly so the link validator
        keeps it in the built site.

    Args:
        files: the mkdocs files collection received by ``on_files``.
        config: the mkdocs config dict.
        registry: mapping of registry key → item with a ``contract_file`` attr.
        yaml_dir: directory holding the ``<contract_file>.yaml`` sources.
        page_subpath: URL prefix for the stub pages (see
            :func:`inject_nav_entries`).
        macro_name: name of the mkdocs-macros macro to invoke from each
            stub, e.g. ``"render_assumption"``.
        download_subpath: URL segment under ``downloads/`` for the copied
            yaml files, e.g. ``"assumptions"``. Pass ``None`` (default) to
            skip yaml download registration — used by the dimensions hook,
            whose downloads are produced in ``on_post_build`` as CSVs.

    Returns:
        The (possibly-mutated) files collection.
    """
    stub_template = '# {title}\n\n{{{{ {macro}("{name}") }}}}\n'
    stub_inclusion = (
        InclusionLevel.INCLUDED if SHOW_CONTRACTS_IN_NAV
        else InclusionLevel.NOT_IN_NAV
    )
    for name, item in registry.items():
        yaml_src = yaml_dir / f"{item.contract_file}.yaml"
        title = _title_for(yaml_src, name) if yaml_src.is_file() else name
        files.append(
            File.generated(
                config,
                f"{page_subpath}/{name}.md",
                content=stub_template.format(
                    title=title, macro=macro_name, name=name
                ),
                inclusion=stub_inclusion,
            )
        )
        if download_subpath is not None and yaml_src.is_file():
            files.append(
                File.generated(
                    config,
                    src_uri=f"downloads/{download_subpath}/{name}.yaml",
                    abs_src_path=str(yaml_src),
                    inclusion=InclusionLevel.NOT_IN_NAV,
                )
            )
    return files
