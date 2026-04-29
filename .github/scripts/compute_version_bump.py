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
    """Walk the structured diff and return (level, summary_lines)."""
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
    parts = s.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version string: {s!r}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def fmt_version(v: tuple[int, int, int]) -> str:
    return f"{v[0]}.{v[1]}.{v[2]}"


def apply_bump(
    version: tuple[int, int, int], level: str, pre_1_0_mapping: bool
) -> tuple[tuple[int, int, int], str]:
    """Return (new_version, effective_level) given the raw classification."""
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
    if not path.exists():
        return "0.0.0"
    return path.read_text().strip() or "0.0.0"


def main() -> None:
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
