# .github/scripts/excel_diff.py
"""
Compare Excel files between base and head branch of a PR.
Outputs a Markdown diff report with row-level changes, matched by ID column.

Usage:
    python excel_diff.py --files "path/to/file.xlsx" --base-ref main --output diff.md
"""

import argparse
import os
import subprocess
import sys
import tempfile

from openpyxl import load_workbook


def extract_workbook(path: str) -> dict[str, list[list[str]]]:
    """Extract all sheets into a dict of {sheet_name: [[cell_values]]}."""
    wb = load_workbook(path, data_only=True)
    data = {}
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = []
        for row in ws.iter_rows():
            rows.append([str(c.value) if c.value is not None else "" for c in row])
        data[sheet_name] = rows
    return data


def get_base_version(filepath: str, base_ref: str) -> dict[str, list[list[str]]]:
    """Extract the base branch version of a file via git show."""
    try:
        result = subprocess.run(
            ["git", "show", f"origin/{base_ref}:{filepath}"],
            capture_output=True,
        )
        if result.returncode != 0:
            return {}

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.write(result.stdout)
        tmp.close()
        data = extract_workbook(tmp.name)
        os.unlink(tmp.name)
        return data
    except Exception:
        return {}


def find_id_column(headers: list[str]) -> int | None:
    """Find the index of the 'id' column (case-insensitive)."""
    for i, h in enumerate(headers):
        if h.strip().lower() == "id":
            return i
    return None


def find_duplicates(rows: list[list[str]], id_col: int) -> list[str]:
    """Return list of duplicate ID values."""
    seen = {}
    duplicates = []
    for row in rows:
        if id_col < len(row):
            val = row[id_col]
            if val in seen:
                if val not in duplicates:
                    duplicates.append(val)
            else:
                seen[val] = True
    return duplicates


def build_row_index(rows: list[list[str]], id_col: int) -> dict[str, list[str]]:
    """Build a dict mapping ID value -> row data. Last occurrence wins."""
    index = {}
    for row in rows:
        if id_col < len(row):
            index[row[id_col]] = row
    return index


def highlight_changed_cells(
    headers: list[str], old_row: list[str], new_row: list[str]
) -> tuple[str, str]:
    """Format old and new rows, bolding cells that changed."""
    max_cols = len(headers)
    old_padded = old_row + [""] * (max_cols - len(old_row))
    new_padded = new_row + [""] * (max_cols - len(new_row))

    old_cells = []
    new_cells = []
    for i in range(max_cols):
        old_val = old_padded[i].replace("|", "\\|")
        new_val = new_padded[i].replace("|", "\\|")
        if old_val != new_val:
            old_cells.append(f"**{old_val}**")
            new_cells.append(f"**{new_val}**")
        else:
            old_cells.append(old_val)
            new_cells.append(new_val)

    return (
        "| " + " | ".join(old_cells) + " |",
        "| " + " | ".join(new_cells) + " |",
    )


def format_row(headers: list[str], row: list[str]) -> str:
    """Format a single data row as a Markdown table row."""
    padded = row + [""] * (len(headers) - len(row))
    return (
        "| " + " | ".join(v.replace("|", "\\|") for v in padded[: len(headers)]) + " |"
    )


def diff_sheet_by_id(
    sheet: str,
    old_rows: list[list[str]],
    new_rows: list[list[str]],
    headers: list[str],
    id_col: int,
) -> list[str]:
    """Diff a single sheet using ID-based matching. Returns markdown lines."""
    lines = []

    old_data = old_rows[1:]  # skip header
    new_data = new_rows[1:]  # skip header

    # Check for duplicate IDs
    old_dupes = find_duplicates(old_data, id_col)
    new_dupes = find_duplicates(new_data, id_col)

    if old_dupes or new_dupes:
        lines.append(f"### ❌ Sheet: `{sheet}` — Duplicate IDs detected")
        lines.append("")
        if old_dupes:
            lines.append(f"Base branch duplicates: `{'`, `'.join(old_dupes)}`")
        if new_dupes:
            lines.append(f"PR branch duplicates: `{'`, `'.join(new_dupes)}`")
        lines.append("")
        lines.append("Resolve duplicate IDs before meaningful diff is possible.")
        lines.append("")
        return lines

    old_index = build_row_index(old_data, id_col)
    new_index = build_row_index(new_data, id_col)

    all_ids_old = list(old_index.keys())
    all_ids_new = list(new_index.keys())

    # Preserve order: new rows order, then deleted ones
    seen = set()
    ordered_ids = []
    for id_val in all_ids_new:
        ordered_ids.append(id_val)
        seen.add(id_val)
    for id_val in all_ids_old:
        if id_val not in seen:
            ordered_ids.append(id_val)

    header_line = "| " + " | ".join(h.replace("|", "\\|") for h in headers) + " |"
    sep_line = "| " + " | ".join("---" for _ in headers) + " |"

    changes = []

    for id_val in ordered_ids:
        in_old = id_val in old_index
        in_new = id_val in new_index

        if in_old and not in_new:
            # Deleted
            changes.append(("deleted", id_val, old_index[id_val]))

        elif not in_old and in_new:
            # Added
            changes.append(("added", id_val, new_index[id_val]))

        elif in_old and in_new:
            old_row = old_index[id_val]
            new_row = new_index[id_val]
            if old_row != new_row:
                # Check if ID column itself changed (shouldn't happen in
                # same-key match, but catches cases where another column
                # was the original ID and got remapped)
                id_changed = old_row[id_col] != new_row[id_col]
                changes.append(("changed", id_val, old_row, new_row, id_changed))

    if not changes:
        return []  # no changes, report nothing

    lines.append(f"### 📝 Sheet: `{sheet}` — {len(changes)} row(s) affected")
    lines.append("")

    for change in changes:
        if change[0] == "added":
            _, id_val, new_row = change
            lines.append(f"**Row `{id_val}` — Added**")
            lines.append("")
            lines.append(header_line)
            lines.append(sep_line)
            lines.append(format_row(headers, new_row))
            lines.append("")

        elif change[0] == "deleted":
            _, id_val, old_row = change
            lines.append(f"**⚠️ Row `{id_val}` — Deleted**")
            lines.append("")
            lines.append(header_line)
            lines.append(sep_line)
            lines.append(format_row(headers, old_row))
            lines.append("")

        elif change[0] == "changed":
            _, id_val, old_row, new_row, id_changed = change
            if id_changed:
                label = f"**⚠️ Row `{id_val}` — Key change**"
            else:
                label = f"**Row `{id_val}` — Changed** (changed cells in bold)"
            old_line, new_line = highlight_changed_cells(headers, old_row, new_row)
            lines.append(label)
            lines.append("")
            lines.append(header_line)
            lines.append(sep_line)
            lines.append(old_line)
            lines.append(new_line)
            lines.append("")

    return lines


def diff_sheet_positional(
    sheet: str,
    old_rows: list[list[str]],
    new_rows: list[list[str]],
    headers: list[str],
) -> list[str]:
    """Fallback: positional diff when no ID column exists."""
    lines = []
    header_line = "| " + " | ".join(h.replace("|", "\\|") for h in headers) + " |"
    sep_line = "| " + " | ".join("---" for _ in headers) + " |"

    changes = []
    max_rows = max(len(old_rows), len(new_rows))

    for r in range(1, max_rows):
        old_row = old_rows[r] if r < len(old_rows) else None
        new_row = new_rows[r] if r < len(new_rows) else None

        if old_row is None and new_row is not None:
            changes.append(("added", r, new_row))
        elif old_row is not None and new_row is None:
            changes.append(("deleted", r, old_row))
        elif old_row != new_row:
            changes.append(("changed", r, old_row, new_row))

    if not changes:
        return []

    lines.append(
        f"### 📝 Sheet: `{sheet}` — {len(changes)} row(s) affected (no ID column, positional diff)"
    )
    lines.append("")

    for change in changes:
        if change[0] == "added":
            _, row_num, new_row = change
            lines.append(f"**Row {row_num} — Added**")
            lines.append("")
            lines.append(header_line)
            lines.append(sep_line)
            lines.append(format_row(headers, new_row))
            lines.append("")
        elif change[0] == "deleted":
            _, row_num, old_row = change
            lines.append(f"**⚠️ Row {row_num} — Deleted**")
            lines.append("")
            lines.append(header_line)
            lines.append(sep_line)
            lines.append(format_row(headers, old_row))
            lines.append("")
        elif change[0] == "changed":
            _, row_num, old_row, new_row = change
            old_line, new_line = highlight_changed_cells(headers, old_row, new_row)
            lines.append(f"**Row {row_num} — Changed** (changed cells in bold)")
            lines.append("")
            lines.append(header_line)
            lines.append(sep_line)
            lines.append(old_line)
            lines.append(new_line)
            lines.append("")

    return lines


def diff_workbooks(
    old_data: dict[str, list[list[str]]],
    new_data: dict[str, list[list[str]]],
) -> str:
    """Compare two workbook extracts, return a Markdown diff."""
    lines = []
    all_sheets = sorted(set(list(old_data.keys()) + list(new_data.keys())))

    for sheet in all_sheets:
        if sheet not in old_data:
            lines.append(f"### 🟢 Sheet added: `{sheet}`")
            lines.append("")
            continue
        if sheet not in new_data:
            lines.append(f"### 🔴 Sheet removed: `{sheet}`")
            lines.append("")
            continue

        old_rows = old_data[sheet]
        new_rows = new_data[sheet]

        headers = old_rows[0] if old_rows else new_rows[0] if new_rows else []
        if not headers:
            continue

        id_col = find_id_column(headers)

        if id_col is not None:
            sheet_lines = diff_sheet_by_id(sheet, old_rows, new_rows, headers, id_col)
        else:
            sheet_lines = diff_sheet_positional(sheet, old_rows, new_rows, headers)

        lines.extend(sheet_lines)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Diff Excel files between git branches"
    )
    parser.add_argument(
        "--files", required=True, help="Newline-separated list of xlsx paths"
    )
    parser.add_argument(
        "--base-ref", required=True, help="Base branch name (e.g. main)"
    )
    parser.add_argument("--output", required=True, help="Output markdown file path")
    args = parser.parse_args()

    files = [f.strip() for f in args.files.strip().splitlines() if f.strip()]
    all_output = []

    for filepath in files:
        all_output.append(f"## 📊 `{filepath}`\n")
        try:
            old_data = get_base_version(filepath, args.base_ref)
            new_data = extract_workbook(filepath)
            all_output.append(diff_workbooks(old_data, new_data))
        except Exception as e:
            all_output.append(f"⚠️ Error processing file: {e}\n")

    output = "\n".join(all_output)
    has_errors = "❌" in output

    with open(args.output, "w") as f:
        f.write(output)

    print(f"Generated diff for {len(files)} file(s) -> {args.output}")

    if has_errors:
        print("::error::Validation errors found in Excel file(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
