#!/usr/bin/env python3
"""Compute the SemVer bump for the dimension data bundle from a workbook diff.

Diffs the workbook (default ``data/dimensions/dimensions.xlsx``) between a
base ref (typically the previous ``dimensions-v*`` tag) and the working tree,
classifies every change against the bump rules, and prints a JSON record:

    {
      "old_version":       "0.1.0",
      "new_version":       "0.2.0",
      "level":             "major",   # raw classification
      "effective_level":   "minor",   # after pre-1.0 mapping
      "no_op":             false,
      "has_errors":        false,
      "summary":           ["- [MAJOR] `dim_building`: row `B01` deleted", ...],
      "summary_markdown":  "..."      # ready for CHANGELOG entry body
    }

Rule table:

    label / description change           PATCH
    parent_id / level change             MINOR
    new row                              MINOR
    new sheet (new dimension)            MINOR
    new column (flexible dim)            MINOR
    primary-key / id change              MAJOR
    row deleted                          MAJOR
    sheet removed                        MAJOR
    column removed                       MAJOR

Pre-1.0 mapping (active while major == 0): MAJOR → MINOR, MINOR → PATCH,
PATCH → PATCH.  Disable with ``--no-pre-1-0-mapping``.

Idempotency: when the diff produces ``level == "none"`` the script reports
``no_op: true`` and ``new_version == old_version`` — the caller should skip
the commit/tag step in that case.
"""

import argparse
import json
import sys
from pathlib import Path

# Allow sibling import when run as a script.
sys.path.insert(0, str(Path(__file__).parent))

from excel_diff import (  # noqa: E402  (sys.path tweak above)
    compute_diff,
    extract_workbook,
    get_workbook_at_ref,
)

# Columns whose change-on-its-own is purely semantic (PATCH).  A row whose
# *only* changed columns are within this set bumps PATCH; anything else
# (parent_id, level, schema-defined columns of flexible dimensions) bumps
# MINOR.
PATCH_COLUMNS: frozenset[str] = frozenset({"label", "description"})

LEVEL_RANK = {"none": 0, "patch": 1, "minor": 2, "major": 3}


def classify_diff(diff: dict) -> tuple[str, list[str]]:
    """Classify a structured workbook diff into a SemVer bump level.

    Walks every sheet diff produced by :func:`excel_diff.compute_diff` and
    runs each change through the rule table from the module docstring. The
    final level is the *highest* level any individual change triggered
    (ranked via :data:`LEVEL_RANK`); each change also adds one bullet line
    to the summary.

    Per-row changes (``ctype == "changed"``) are evaluated in this order:

    1. ``id_changed`` set → MAJOR (primary-key change).
    2. ``changed_columns`` is a non-empty subset of :data:`PATCH_COLUMNS`
       (``label`` / ``description``) → PATCH.
    3. Otherwise → MINOR (the "structural change" branch). An empty
       ``changed_columns`` list (cells differ but no header overlap)
       collapses into the MINOR branch with detail "columns differ".

    Sheets with ``event == "error"`` (e.g. duplicate IDs) contribute
    nothing to either the level or the summary — the workflow surfaces
    those separately and fails the job.

    Args:
        diff: structured diff in the shape produced by
            :func:`excel_diff.compute_diff`.

    Returns:
        ``(level, summary)`` where ``level`` is one of ``"none"``,
        ``"patch"``, ``"minor"``, ``"major"``, and ``summary`` is a list
        of Markdown bullets like ``"- [MAJOR] `dim_building`: row `B01`
        deleted"``.
    """
    level = "none"
    summary: list[str] = []

    def bump(new_level: str, msg: str) -> None:
        nonlocal level
        if LEVEL_RANK[new_level] > LEVEL_RANK[level]:
            level = new_level
        summary.append(f"- [{new_level.upper()}] {msg}")

    for sheet, sd in diff["sheets"].items():
        event = sd.get("event")
        if event == "added":
            bump("minor", f"`{sheet}`: new dimension added")
            continue
        if event == "removed":
            bump("major", f"`{sheet}`: dimension removed")
            continue
        if event in ("unchanged", "error"):
            continue

        for col in sd.get("columns_removed", []):
            bump("major", f"`{sheet}`: column `{col}` removed")
        for col in sd.get("columns_added", []):
            bump("minor", f"`{sheet}`: column `{col}` added")

        for ch in sd.get("row_changes", []):
            ctype = ch["type"]
            key = ch["key"]
            if ctype == "deleted":
                bump("major", f"`{sheet}`: row `{key}` deleted")
            elif ctype == "added":
                bump("minor", f"`{sheet}`: row `{key}` added")
            elif ctype == "changed":
                if ch.get("id_changed"):
                    bump("major", f"`{sheet}`: row `{key}` primary-key change")
                    continue
                cols = ch.get("changed_columns") or []
                if cols and set(cols).issubset(PATCH_COLUMNS):
                    bump(
                        "patch",
                        f"`{sheet}`: row `{key}` semantic change ({', '.join(cols)})",
                    )
                else:
                    detail = ", ".join(cols) if cols else "columns differ"
                    bump("minor", f"`{sheet}`: row `{key}` structural change ({detail})")

    return level, summary


def parse_version(s: str) -> tuple[int, int, int]:
    """Parse a ``"MAJOR.MINOR.PATCH"`` string into a 3-tuple of ints.

    Surrounding whitespace is tolerated. Raises :class:`ValueError` if the
    string does not have exactly three dot-separated components or any
    component is not an integer.
    """
    parts = s.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version string: {s!r}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def fmt_version(v: tuple[int, int, int]) -> str:
    """Format a ``(major, minor, patch)`` tuple as ``"MAJOR.MINOR.PATCH"``."""
    return f"{v[0]}.{v[1]}.{v[2]}"


def apply_bump(
    version: tuple[int, int, int], level: str, pre_1_0_mapping: bool
) -> tuple[tuple[int, int, int], str]:
    """Apply a classified bump to a SemVer triple.

    Args:
        version: current ``(major, minor, patch)``.
        level: raw classification from :func:`classify_diff` —
            ``"none"`` / ``"patch"`` / ``"minor"`` / ``"major"``.
        pre_1_0_mapping: when ``True`` *and* ``major == 0``, downgrade
            MAJOR → MINOR and MINOR → PATCH before applying. This keeps
            the bundle in 0.x while the schema is unstable. PATCH and
            ``"none"`` are unaffected. Above 0.x the flag has no effect.

    Returns:
        ``(new_version, effective_level)`` where ``effective_level`` is
        the level that actually drove the bump (post-mapping). Reporting
        both lets the PR comment surface "MAJOR, downgraded to MINOR".
    """
    major, minor, patch = version
    eff = level
    if pre_1_0_mapping and major == 0:
        if eff == "major":
            eff = "minor"
        elif eff == "minor":
            eff = "patch"
    if eff == "major":
        return (major + 1, 0, 0), eff
    if eff == "minor":
        return (major, minor + 1, 0), eff
    if eff == "patch":
        return (major, minor, patch + 1), eff
    return (major, minor, patch), eff


def read_version(path: Path) -> str:
    """Read a VERSION file, returning ``"0.0.0"`` when absent or blank.

    A missing, empty, or whitespace-only file is treated as the seed
    ``"0.0.0"`` so a fresh checkout without the file still bumps cleanly.
    """
    if not path.exists():
        return "0.0.0"
    return path.read_text().strip() or "0.0.0"


def main() -> None:
    """CLI entry: diff the workbook against ``--base-ref`` (or
    ``--base-workbook``), classify the changes, and emit a JSON record
    describing the bump. See the module docstring for the JSON shape and
    rule table.
    """
    parser = argparse.ArgumentParser(
        description="Compute SemVer bump for the dimension data bundle."
    )
    parser.add_argument(
        "--workbook",
        default="data/dimensions/dimensions.xlsx",
        help="Path to the head workbook (default: data/dimensions/dimensions.xlsx)",
    )
    parser.add_argument(
        "--version-file",
        default="data/dimensions/VERSION",
        help="Path to VERSION file (default: data/dimensions/VERSION)",
    )
    parser.add_argument(
        "--base-ref",
        help="Git ref (tag/branch/sha) to diff against. Mutually exclusive with --base-workbook.",
    )
    parser.add_argument(
        "--base-workbook",
        help="Local path to a base xlsx to diff against, instead of --base-ref.",
    )
    parser.add_argument(
        "--no-pre-1-0-mapping",
        dest="pre_1_0_mapping",
        action="store_false",
        help="Disable the 0.x downgrade mapping (treat MAJOR as literal).",
    )
    parser.add_argument(
        "--out",
        help="Write JSON output to this path instead of stdout.",
    )
    args = parser.parse_args()

    if args.base_ref and args.base_workbook:
        parser.error("--base-ref and --base-workbook are mutually exclusive")

    if args.base_ref:
        old_data = get_workbook_at_ref(args.workbook, args.base_ref)
    elif args.base_workbook:
        old_path = Path(args.base_workbook)
        old_data = extract_workbook(str(old_path)) if old_path.exists() else {}
    else:
        old_data = {}

    new_data = extract_workbook(args.workbook)
    diff = compute_diff(old_data, new_data)

    level, summary = classify_diff(diff)
    old_v_str = read_version(Path(args.version_file))
    old_v = parse_version(old_v_str)
    new_v, effective = apply_bump(old_v, level, args.pre_1_0_mapping)
    new_v_str = fmt_version(new_v)

    no_op = level == "none" or new_v == old_v
    summary_markdown = "\n".join(summary) if summary else "(no data changes)"

    result = {
        "old_version": old_v_str,
        "new_version": new_v_str,
        "level": level,
        "effective_level": effective,
        "no_op": no_op,
        "has_errors": diff.get("has_errors", False),
        "summary": summary,
        "summary_markdown": summary_markdown,
    }

    payload = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(payload)
    print(payload)


if __name__ == "__main__":
    main()
