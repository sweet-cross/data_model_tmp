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


def render_contract_header(name: str, meta: dict) -> str:
    """Render the Contract Name / Contract Type / Description block.

    Args:
        name: the registry key (used as a fallback when the yaml has no
            ``name`` field of its own).
        meta: parsed contract yaml.

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
        f'<tbody>{"".join(rows)}</tbody>'
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
        '<p class="contract-primary-key">'
        f"<strong>Primary key:</strong> {keys_html}</p>"
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
        target = (
            target_fields[0]
            if isinstance(target_fields, list)
            else target_fields
        )
        out[str(field)] = {
            "resource": str(resource),
            "target": str(target or ""),
        }
    return out


def dimension_page_url(
    resource: str, dim_registry: dict, depth: int
) -> str | None:
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
    return "../" * depth + f"dimensions/{resource}/"


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
            tooltip = f'Foreign key → {fk["resource"]}'
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
        f'<tbody>{"".join(rows)}</tbody>'
        "</table>"
        "</div>"
    )
