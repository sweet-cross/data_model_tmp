"""Shared rendering helpers for contract pages (dimensions, assumptions, results).

Every helper speaks to the light metadata surface shared by every contract in
this repo (`name`, `title`, `description`, `contract_type`) and/or the
Frictionless Table Schema block (`tableschema.fields`, `tableschema.primaryKey`,
`tableschema.foreignKeys`). Dimension, assumption, and future result macros
compose these primitives so the visual language and markup stay consistent
across contract types.
"""

import html
import math
from functools import lru_cache
from pathlib import Path

import yaml

# Foreign keys whose reference resource matches this are dropped entirely:
# the scenario tuple is always present on scenario-aware contracts and adding
# a marker next to three field names (group/name/variant) is noisy without
# being useful.
SCENARIO_FK_RESOURCE = "dim_scenario"


# ---------------------------------------------------------------------------
# Value cleaning + YAML loading
# ---------------------------------------------------------------------------


def clean(value) -> str:
    """Normalise a yaml-parsed scalar to a safe printable string.

    Args:
        value: any scalar coming out of yaml.safe_load / pandas (str, int,
            float, None, NaN, etc.).

    Returns:
        The stripped string representation, or '' when the value is missing
        (None, float NaN, or the literal token 'nan' case-insensitively).
        Callers use the empty string as the "not set" signal.
    """
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


@lru_cache(maxsize=None)
def load_contract(yaml_path: str) -> dict:
    """Read and parse a contract YAML file, cached for the build.

    Args:
        yaml_path: absolute filesystem path to the YAML. Passed as ``str`` so
            the result is memoisable with ``lru_cache``.

    Returns:
        The parsed mapping; an empty dict when the file is empty. Cached so
        every mkdocs lifecycle step (nav build, stub generation, macro render)
        that opens the same contract pays the I/O cost exactly once.
    """
    with Path(yaml_path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def contract_type_label(meta: dict) -> str:
    """Return the contract_type from contract metadata, defaulting to 'General'.

    Args:
        meta: parsed contract yaml.

    Returns:
        The human-readable contract-type label. Falls back to 'General' when
        the ``contract_type`` field is missing or empty, so every contract
        page shows a consistent row.
    """
    return clean(meta.get("contract_type")) or "General"


# ---------------------------------------------------------------------------
# Header / metadata block
# ---------------------------------------------------------------------------


def render_contract_header(
    name: str, meta: dict, *, version: str | None = None
) -> str:
    """Render the Contract Name / Contract Type / Description block.

    Args:
        name: the registry key (used as a fallback when the yaml has no
            ``name`` field of its own).
        meta: parsed contract yaml.
        version: optional bundle version string to display as an extra row.
            Pass ``None`` (default) to omit. Used by dimension pages to show
            the dimension data bundle version.

    Returns:
        HTML string containing a ``<dl class="contract-meta">``. The
        description row is omitted when the contract has no description, so
        the block never shows an empty value.
    """
    contract_name = clean(meta.get("name")) or name
    ctype = contract_type_label(meta)
    desc = clean(meta.get("description"))
    rows = [
        ("Contract Name", f"<code>{html.escape(contract_name)}</code>"),
        ("Contract Type", html.escape(ctype)),
    ]
    if version:
        rows.append(("Version", f"<code>{html.escape(version)}</code>"))
    if desc:
        rows.append(("Description", html.escape(desc)))
    body = "".join(f"<dt>{label}</dt><dd>{value}</dd>" for label, value in rows)
    return f'<dl class="contract-meta">{body}</dl>'


# ---------------------------------------------------------------------------
# Downloads bar
# ---------------------------------------------------------------------------


def render_downloads(buttons: list[tuple[str, str]]) -> str:
    """Render the pill-button row used at the top of every contract page.

    Args:
        buttons: ordered list of (href, label) tuples.

    Returns:
        An HTML ``<div class="contract-downloads">`` with one anchor per
        button, or the empty string when ``buttons`` is empty so callers can
        always interpolate the result unconditionally.
    """
    if not buttons:
        return ""
    inner = "".join(
        f'<a class="contract-download-btn" href="{html.escape(href)}" download>'
        f"{html.escape(label)}</a>"
        for href, label in buttons
    )
    return f'<div class="contract-downloads">{inner}</div>'


# ---------------------------------------------------------------------------
# Overview index table
# ---------------------------------------------------------------------------


def render_contract_index(entries: list[tuple[str, str, str, str | None]]) -> str:
    """Render a sortable Name / Title / Description overview table.

    Args:
        entries: list of ``(name, title, description, href)`` tuples. When
            ``href`` is ``None`` the row is rendered as plain text (no link,
            no hover overlay) — use for registry items that do not get a
            per-contract page.

    Returns:
        HTML string containing a ``<table class="contract-index-table sortable">``
        consumed by the vendored tablesort.js. Falls back to a plain
        ``<p>`` when ``entries`` is empty so pages never render a blank table.
    """
    if not entries:
        return "<p><em>No contracts registered.</em></p>"
    rows = []
    for name, title, desc, href in entries:
        name_html = html.escape(name)
        if href is None:
            name_cell = f"<code>{name_html}</code>"
            row_class = "contract-index-row contract-index-row-static"
        else:
            name_cell = f'<a href="{html.escape(href)}"><code>{name_html}</code></a>'
            row_class = "contract-index-row"
        rows.append(
            f'<tr class="{row_class}">'
            f'<td class="contract-index-name">{name_cell}</td>'
            f"<td>{html.escape(title)}</td>"
            f"<td>{html.escape(desc)}</td>"
            "</tr>"
        )
    return (
        '<div class="contract-index" markdown="0">'
        '<table class="contract-index-table sortable">'
        "<thead><tr><th>Name</th><th>Title</th><th>Description</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Primary key line
# ---------------------------------------------------------------------------


def render_primary_key(table_schema: dict) -> str:
    """Render the primary-key statement for a contract, or '' when absent.

    Args:
        table_schema: parsed ``tableschema`` block from a contract.

    Returns:
        An HTML ``<p class="contract-primary-key">`` listing each key field as
        a ``<code>`` element, or the empty string when ``primaryKey`` is
        missing / empty.
    """
    pk = table_schema.get("primaryKey") or []
    if isinstance(pk, str):
        pk = [pk]
    if not pk:
        return ""
    keys_html = ", ".join(f"<code>{html.escape(str(k))}</code>" for k in pk)
    return (
        f'<p class="contract-primary-key"><strong>Primary key:</strong> {keys_html}</p>'
    )


# ---------------------------------------------------------------------------
# Foreign keys + dimension linking
# ---------------------------------------------------------------------------


def foreign_key_index(table_schema: dict) -> dict[str, dict]:
    """Build a field-name → reference lookup for **single-field** foreign keys.

    Composite foreign keys (``fields`` is a list with more than one entry)
    are dropped because attaching a marker to a single field name is
    misleading when the constraint spans several. FKs pointing at
    ``dim_scenario`` are also dropped — they are always the
    (scenario_group, scenario_name, scenario_variant) composite tuple and are
    handled implicitly by the scenario registry elsewhere.

    Args:
        table_schema: parsed ``tableschema`` block from a contract.

    Returns:
        Mapping ``field_name → {'resource': str, 'target': str}`` for every
        single-field foreign key that should render a marker in the fields
        table. ``target`` is the reference's target field (commonly ``'id'``).
    """
    fks = table_schema.get("foreignKeys") or []
    out: dict[str, dict] = {}
    for fk in fks:
        fields = fk.get("fields")
        ref = fk.get("reference") or {}
        resource = ref.get("resource")
        target_fields = ref.get("fields")
        if isinstance(fields, list):
            if len(fields) != 1:
                continue
            field = fields[0]
        else:
            field = fields
        if not field or not resource or resource == SCENARIO_FK_RESOURCE:
            continue
        target = target_fields[0] if isinstance(target_fields, list) else target_fields
        out[str(field)] = {
            "resource": str(resource),
            "target": str(target or ""),
        }
    return out


def dimension_page_url(resource: str, dim_registry: dict, depth: int) -> str | None:
    """Return the relative URL to a rendered dimension page, or None.

    Args:
        resource: the foreign-key target resource name, e.g. ``'dim_iso_region'``.
        dim_registry: the ``dimension_registry`` dict from ``registry.py``.
        depth: how many directory levels the *calling page* sits below the
            site root (with ``use_directory_urls: true``). An assumption page
            at ``variables/assumptions/<name>/`` is depth 3; a dimension page
            at ``dimensions/<name>/`` is depth 2.

    Returns:
        Relative URL string (e.g. ``'../../dimensions/dim_iso_region/'``), or
        ``None`` when the resource is absent from the registry or is marked
        ``index_only`` — i.e. when no per-dimension page exists to link to.
    """
    entry = dim_registry.get(resource)
    if entry is None or getattr(entry, "index_only", False):
        return None
    # Path segment matches ``_PAGE_SUBPATH`` in docs/hooks/dimensions.py;
    # update both together if the hierarchical-dimension hook moves.
    return "../" * depth + f"dimensions/dimensions/{resource}/"


# ---------------------------------------------------------------------------
# Fields table
# ---------------------------------------------------------------------------


def _format_constraint(key: str, value) -> str:
    """Format one constraint key/value pair as a compact chip label."""
    cleaned = clean(value) or str(value)
    return f"{html.escape(key)}={html.escape(cleaned)}"


def render_fields_table(
    fields: list[dict],
    fk_index: dict[str, dict],
    dim_registry: dict,
    depth: int,
    primary_key: list[str] | None = None,
) -> str:
    """Render the Frictionless fields block as a sortable HTML table.

    Args:
        fields: list of field descriptors from ``tableschema.fields``. Each
            dict may carry ``name``, ``type``, ``title``, ``description``, and
            a ``constraints`` sub-mapping.
        fk_index: mapping produced by :func:`foreign_key_index`. Fields named
            in this mapping get a foreign-key marker next to the name.
        dim_registry: the ``dimension_registry`` dict; used to decide whether
            a foreign-key marker is a clickable link or plain text.
        depth: directory depth of the *calling page* from the site root,
            propagated to :func:`dimension_page_url`.
        primary_key: names of fields that form the contract's primary key.
            Those fields are always marked Required even when the yaml
            ``constraints.required`` flag is missing — primary-key membership
            implies NOT NULL.

    Returns:
        HTML string containing a ``<table class="contract-fields-table sortable">``,
        or the empty string when ``fields`` is empty.
    """
    if not fields:
        return ""
    pk_set = set(primary_key or [])
    rows = []
    for field in fields:
        name = clean(field.get("name"))
        title = clean(field.get("title"))
        ftype = clean(field.get("type"))
        desc = clean(field.get("description"))
        constraints = field.get("constraints") or {}
        required = constraints.get("required") is True or name in pk_set
        other = {k: v for k, v in constraints.items() if k != "required"}

        name_cell = f"<code>{html.escape(name)}</code>"
        fk = fk_index.get(name)
        if fk:
            tooltip = f"Foreign key → {fk['resource']}"
            url = dimension_page_url(fk["resource"], dim_registry, depth)
            if url:
                name_cell += (
                    f' <a class="contract-fk" href="{html.escape(url)}" '
                    f'title="{html.escape(tooltip)}">&#x2197;</a>'
                )
            else:
                name_cell += (
                    f' <span class="contract-fk" '
                    f'title="{html.escape(tooltip)}">&#x2197;</span>'
                )

        req_cell = "\u2713" if required else ""
        constraints_cell = " ".join(
            f'<span class="contract-constraint">{_format_constraint(k, v)}</span>'
            for k, v in other.items()
        )
        ftype_cell = f"<code>{html.escape(ftype)}</code>" if ftype else ""
        rows.append(
            "<tr>"
            f"<td>{name_cell}</td>"
            f"<td>{html.escape(title)}</td>"
            f"<td>{ftype_cell}</td>"
            f'<td class="contract-fields-req">{req_cell}</td>'
            f"<td>{constraints_cell}</td>"
            f"<td>{html.escape(desc)}</td>"
            "</tr>"
        )
    return (
        '<div class="contract-fields" markdown="0">'
        '<h2 class="contract-fields-heading">Data fields</h2>'
        '<table class="contract-fields-table sortable">'
        "<thead><tr>"
        "<th>Name</th><th>Title</th><th>Type</th><th>Required</th>"
        "<th>Constraints</th><th>Description</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Full-page composition (used by yaml-only contract macros)
# ---------------------------------------------------------------------------


def render_contract_page(
    name: str,
    meta: dict,
    downloads: list[tuple[str, str]],
    page_depth: int,
    dim_registry: dict,
    extra_body_html: str = "",
    *,
    version: str | None = None,
) -> str:
    """Render the full HTML block for a single contract page.

    Composes the primitives — downloads, header, primary key, fields table
    — into the ``<div class="contract-page" markdown="0">`` wrapper shared
    by assumption, result, and flexible-dimension pages.

    Args:
        name: the registry key, used as fallback when the yaml has no
            ``name`` field of its own.
        meta: parsed contract yaml (output of :func:`load_contract`).
        downloads: ordered ``(href, label)`` tuples rendered as the pill-
            button row at the top of the page. Pass a single-item list for
            yaml-only contracts.
        page_depth: directory depth of the calling page below the site root
            (with ``use_directory_urls: true``), propagated to
            :func:`render_fields_table` for dimension-link resolution.
        dim_registry: the ``dimension_registry`` dict from ``registry.py``.
        extra_body_html: optional HTML appended after the fields table and
            before the closing ``</div>``. Used by the flexible-dimension
            macro to append a data table; leave empty for yaml-only pages.

    Returns:
        HTML string. The outer div carries ``markdown="0"`` so mkdocs does
        not re-parse the body as markdown.
    """
    schema = meta.get("tableschema") or {}
    fields = schema.get("fields") or []
    fk_index = foreign_key_index(schema)
    pk = schema.get("primaryKey") or []
    if isinstance(pk, str):
        pk = [pk]

    downloads_html = render_downloads(downloads)
    header_html = render_contract_header(name, meta, version=version)
    pk_html = render_primary_key(schema)
    fields_html = render_fields_table(
        fields,
        fk_index,
        dim_registry,
        page_depth,
        primary_key=pk,
    )
    return (
        '<div class="contract-page" markdown="0">'
        f"{header_html}"
        f"{pk_html}"
        f"{fields_html}"
        f"{extra_body_html}"
        f"{downloads_html}"
        "</div>"
    )


def render_data_table(df, fields: list[dict]) -> str:
    """Render a pandas DataFrame as a sortable contract data table.

    Column order follows ``fields`` (the Frictionless field list from the
    contract yaml); any DataFrame column not named in ``fields`` is
    dropped so workbook scratch columns never leak onto the page. Each
    cell is normalised via :func:`clean` and HTML-escaped.

    Args:
        df: the pandas DataFrame holding the sheet rows.
        fields: the ``tableschema.fields`` list from the contract yaml.
            Each entry needs at least a ``name``; ``title`` is used for
            the column header when present, falling back to ``name``.

    Returns:
        HTML block, or the empty string when there are no fields or no
        rows after column filtering.
    """
    if not fields:
        return ""
    columns = [clean(f.get("name")) for f in fields if clean(f.get("name"))]
    present = [c for c in columns if c in df.columns]
    if not present:
        return ""
    titles = {
        clean(f.get("name")): clean(f.get("title")) or clean(f.get("name"))
        for f in fields
    }
    head = "".join(f"<th>{html.escape(titles.get(c, c))}</th>" for c in present)
    body_rows = []
    for _, row in df[present].iterrows():
        cells = "".join(f"<td>{html.escape(clean(row[c]))}</td>" for c in present)
        body_rows.append(f"<tr>{cells}</tr>")
    return (
        '<div class="contract-fields" markdown="0">'
        '<h2 class="contract-fields-heading">Data</h2>'
        '<table class="contract-data-table sortable">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


def workbook_dimension_downloads(
    name: str,
    page_depth: int,
    *,
    include_csv: bool = True,
    version: str | None = None,
) -> list[tuple[str, str]]:
    """Build the standard download-pill set for a workbook-backed dimension page.

    The dimensions workbook is a single artefact shared by hierarchical
    dimensions and flexible dimensions, so every page that renders a row
    from it offers the same button triad: contract yaml → per-contract CSV
    → full workbook. The CSV button is suppressed when ``include_csv`` is
    False (flexible dimensions without ``show_data``).

    Args:
        name: the registry key; used to build the per-contract yaml and CSV
            URLs. Both files must be emitted under
            ``site/downloads/dimensions/``.
        page_depth: directory depth of the calling page below the site
            root (with ``use_directory_urls: true``). A hierarchical
            dimension page at ``dimensions/<name>/`` is depth 2; a flexible
            dimension page at ``dimensions/flexible/<name>/`` is depth 3.
        include_csv: include the per-contract CSV button. Defaults to True.
            Pass False when the registry entry has no inline data to ship.

    Returns:
        An ordered ``[(href, label), ...]`` list ready to pass to
        :func:`render_downloads` or :func:`render_contract_page`.
    """
    prefix = "../" * page_depth
    suffix = f" — v{version}" if version else ""
    downloads = [
        (
            f"{prefix}downloads/dimensions/{name}.yaml",
            "Download contract (yaml)",
        ),
    ]
    if include_csv:
        downloads.append(
            (
                f"{prefix}downloads/dimensions/{name}.csv",
                f"Download CSV{suffix}",
            )
        )
    downloads.append(
        (
            f"{prefix}downloads/dimensions.xlsx",
            f"Download all dimensions (xlsx){suffix}",
        )
    )
    return downloads


def render_contract_overview(registry: dict, yaml_dir: Path) -> str:
    """Render the sortable overview table for a yaml-only contract registry.

    Reads ``title`` and ``description`` from each registered contract's yaml
    and delegates to :func:`render_contract_index` with per-entry href
    ``"<name>/"`` — relative to the overview page that hosts the call.

    Args:
        registry: mapping of registry key → item with a ``contract_file``
            attribute (duck-typed; works with
            :class:`registry.ContractRegistryItem`).
        yaml_dir: directory holding the ``<contract_file>.yaml`` sources.

    Returns:
        HTML table, or a placeholder paragraph when the registry is empty.
    """
    entries: list[tuple[str, str, str, str | None]] = []
    for name, item in registry.items():
        meta = load_contract(str(yaml_dir / f"{item.contract_file}.yaml"))
        title = str(meta.get("title") or name).strip()
        desc = str(meta.get("description") or "").strip()
        entries.append((name, title, desc, f"{name}/"))
    return render_contract_index(entries)
