"""Tests for .github/scripts/excel_diff.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from openpyxl import Workbook

import excel_diff
from excel_diff import (
    _changed_column_names,
    _compute_sheet_diff_id,
    _compute_sheet_diff_positional,
    build_row_index,
    compute_diff,
    diff_workbooks,
    extract_workbook,
    find_duplicates,
    find_id_column,
    format_row,
    get_workbook_at_ref,
    highlight_changed_cells,
    render_markdown,
)


# ---------------------------------------------------------------------------
# find_id_column
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "headers, expected",
    [
        (["id", "label"], 0),
        (["label", "ID"], 1),
        (["label", " Id "], 1),
        (["label", "description"], None),
        ([], None),
    ],
)
def test_find_id_column(headers, expected):
    assert find_id_column(headers) == expected


# ---------------------------------------------------------------------------
# find_duplicates
# ---------------------------------------------------------------------------


def test_find_duplicates_unique():
    rows = [["A", "x"], ["B", "y"], ["C", "z"]]
    assert find_duplicates(rows, id_col=0) == []


def test_find_duplicates_first_seen_order():
    rows = [["A"], ["B"], ["A"], ["C"], ["B"], ["A"]]
    # "A" duplicated first, then "B"; each only listed once.
    assert find_duplicates(rows, id_col=0) == ["A", "B"]


def test_find_duplicates_skips_short_rows():
    # row at index 2 has no value at id_col=1; it must not crash and not count.
    rows = [["x", "A"], ["y", "A"], ["z"]]
    assert find_duplicates(rows, id_col=1) == ["A"]


# ---------------------------------------------------------------------------
# build_row_index
# ---------------------------------------------------------------------------


def test_build_row_index_last_wins_on_duplicate():
    rows = [["A", "first"], ["B", "b"], ["A", "second"]]
    idx = build_row_index(rows, id_col=0)
    assert idx == {"A": ["A", "second"], "B": ["B", "b"]}


def test_build_row_index_skips_short_rows():
    rows = [["x", "A"], ["y"], ["z", "B"]]
    idx = build_row_index(rows, id_col=1)
    assert idx == {"A": ["x", "A"], "B": ["z", "B"]}


# ---------------------------------------------------------------------------
# _changed_column_names
# ---------------------------------------------------------------------------


def test_changed_column_names_identical():
    headers = ["id", "label", "description"]
    row = ["A", "Alpha", "first"]
    assert _changed_column_names(headers, headers, row, row) == []


def test_changed_column_names_one_changed():
    headers = ["id", "label", "description"]
    old = ["A", "Alpha", "first"]
    new = ["A", "Alpha", "second"]
    assert _changed_column_names(headers, headers, old, new) == ["description"]


def test_changed_column_names_only_intersection_compared():
    # "extra" is removed and "added" is added — comparison only spans
    # the intersection {id, label}, and only "label" actually differs there.
    old_headers = ["id", "label", "extra"]
    new_headers = ["id", "label", "added"]
    old = ["A", "Alpha", "x"]
    new = ["A", "Beta", "y"]
    assert _changed_column_names(old_headers, new_headers, old, new) == ["label"]


def test_changed_column_names_tolerates_short_rows():
    headers = ["id", "label", "description"]
    old = ["A", "Alpha"]  # missing description
    new = ["A", "Alpha", "added desc"]
    assert _changed_column_names(headers, headers, old, new) == ["description"]


# ---------------------------------------------------------------------------
# _compute_sheet_diff_id
# ---------------------------------------------------------------------------


def test_sheet_diff_id_identical(make_sheet):
    sheet = make_sheet(["id", "label"], ["A", "Alpha"], ["B", "Beta"])
    assert _compute_sheet_diff_id(sheet, sheet) == {"event": "unchanged"}


def test_sheet_diff_id_row_added(make_sheet):
    old = make_sheet(["id", "label"], ["A", "Alpha"])
    new = make_sheet(["id", "label"], ["A", "Alpha"], ["B", "Beta"])
    sd = _compute_sheet_diff_id(old, new)
    assert sd["event"] == "modified"
    assert sd["mode"] == "id"
    assert sd["row_changes"] == [{"type": "added", "key": "B", "row": ["B", "Beta"]}]


def test_sheet_diff_id_row_deleted(make_sheet):
    old = make_sheet(["id", "label"], ["A", "Alpha"], ["B", "Beta"])
    new = make_sheet(["id", "label"], ["A", "Alpha"])
    sd = _compute_sheet_diff_id(old, new)
    assert sd["row_changes"] == [{"type": "deleted", "key": "B", "row": ["B", "Beta"]}]


def test_sheet_diff_id_row_label_only_change(make_sheet):
    old = make_sheet(["id", "label", "description"], ["A", "Old", "desc"])
    new = make_sheet(["id", "label", "description"], ["A", "New", "desc"])
    sd = _compute_sheet_diff_id(old, new)
    assert len(sd["row_changes"]) == 1
    ch = sd["row_changes"][0]
    assert ch["type"] == "changed"
    assert ch["key"] == "A"
    assert ch["changed_columns"] == ["label"]
    assert ch["id_changed"] is False


def test_sheet_diff_id_row_parent_id_change(make_sheet):
    old = make_sheet(["id", "parent_id", "label"], ["B01", "P1", "Building"])
    new = make_sheet(["id", "parent_id", "label"], ["B01", "P2", "Building"])
    sd = _compute_sheet_diff_id(old, new)
    ch = sd["row_changes"][0]
    assert ch["type"] == "changed"
    assert ch["changed_columns"] == ["parent_id"]
    assert ch["id_changed"] is False


def test_sheet_diff_id_id_renamed_surfaces_as_add_plus_delete(make_sheet):
    # The join is on id, so a renamed id looks like one added + one deleted —
    # NOT a single 'changed' row with id_changed=True.  The 'id_changed' flag
    # only fires for true 'changed' entries (same join key, different values).
    # This is a contract the version-bump rules rely on.
    old = make_sheet(["id", "label"], ["A", "x"])
    new = make_sheet(["id", "label"], ["B", "x"])
    sd = _compute_sheet_diff_id(old, new)
    types = sorted(c["type"] for c in sd["row_changes"])
    keys = sorted(c["key"] for c in sd["row_changes"])
    assert types == ["added", "deleted"]
    assert keys == ["A", "B"]


def test_sheet_diff_id_column_added(make_sheet):
    old = make_sheet(["id", "label"], ["A", "Alpha"])
    new = make_sheet(["id", "label", "extra"], ["A", "Alpha", "x"])
    sd = _compute_sheet_diff_id(old, new)
    assert sd["columns_added"] == ["extra"]
    assert sd["columns_removed"] == []


def test_sheet_diff_id_column_removed(make_sheet):
    old = make_sheet(["id", "label", "extra"], ["A", "Alpha", "x"])
    new = make_sheet(["id", "label"], ["A", "Alpha"])
    sd = _compute_sheet_diff_id(old, new)
    assert sd["columns_added"] == []
    assert sd["columns_removed"] == ["extra"]


def test_sheet_diff_id_duplicate_in_old(make_sheet):
    old = make_sheet(["id", "label"], ["A", "x"], ["A", "y"])
    new = make_sheet(["id", "label"], ["A", "x"])
    sd = _compute_sheet_diff_id(old, new)
    assert sd["event"] == "error"
    assert sd["error_type"] == "duplicate_ids"
    assert sd["old_duplicates"] == ["A"]
    assert sd["new_duplicates"] == []


def test_sheet_diff_id_duplicate_in_new(make_sheet):
    old = make_sheet(["id", "label"], ["A", "x"])
    new = make_sheet(["id", "label"], ["A", "x"], ["A", "y"])
    sd = _compute_sheet_diff_id(old, new)
    assert sd["event"] == "error"
    assert sd["new_duplicates"] == ["A"]


def test_sheet_diff_id_empty_old_treats_all_new_as_added(make_sheet):
    # _compute_sheet_diff_id is normally guarded by compute_diff (which
    # short-circuits an absent sheet to event=added), but the inner function
    # has its own behavior worth pinning so a future refactor can't drift.
    old: list[list[str]] = []
    new = make_sheet(["id", "label"], ["A", "Alpha"], ["B", "Beta"])
    sd = _compute_sheet_diff_id(old, new)
    assert sd["event"] == "modified"
    assert [c["type"] for c in sd["row_changes"]] == ["added", "added"]
    assert sd["columns_added"] == ["id", "label"]


def test_sheet_diff_id_row_change_order_new_first_then_old_only(make_sheet):
    # Order matters: ids in the new sheet appear in new-sheet order first,
    # then ids only in old (deletions) follow.  _render_modified_sheet and the
    # version-bump summary both rely on this ordering.
    old = make_sheet(
        ["id", "label"],
        ["A", "a"],
        ["B", "b"],
    )
    new = make_sheet(
        ["id", "label"],
        ["B", "b2"],  # changed
        ["C", "c"],   # added
    )
    sd = _compute_sheet_diff_id(old, new)
    assert [(c["type"], c["key"]) for c in sd["row_changes"]] == [
        ("changed", "B"),
        ("added", "C"),
        ("deleted", "A"),
    ]


# ---------------------------------------------------------------------------
# _compute_sheet_diff_positional
# ---------------------------------------------------------------------------


def test_sheet_diff_positional_identical(make_sheet):
    sheet = make_sheet(["a", "b"], ["1", "2"], ["3", "4"])
    assert _compute_sheet_diff_positional(sheet, sheet) == {"event": "unchanged"}


def test_sheet_diff_positional_row_added_at_end(make_sheet):
    old = make_sheet(["a", "b"], ["1", "2"])
    new = make_sheet(["a", "b"], ["1", "2"], ["3", "4"])
    sd = _compute_sheet_diff_positional(old, new)
    assert sd["mode"] == "positional"
    assert sd["row_changes"] == [{"type": "added", "key": 2, "row": ["3", "4"]}]


def test_sheet_diff_positional_row_deleted_at_end(make_sheet):
    old = make_sheet(["a", "b"], ["1", "2"], ["3", "4"])
    new = make_sheet(["a", "b"], ["1", "2"])
    sd = _compute_sheet_diff_positional(old, new)
    assert sd["row_changes"] == [{"type": "deleted", "key": 2, "row": ["3", "4"]}]


def test_sheet_diff_positional_row_changed_mid_sheet(make_sheet):
    old = make_sheet(["a", "b"], ["1", "2"], ["3", "4"], ["5", "6"])
    new = make_sheet(["a", "b"], ["1", "2"], ["3", "X"], ["5", "6"])
    sd = _compute_sheet_diff_positional(old, new)
    assert len(sd["row_changes"]) == 1
    ch = sd["row_changes"][0]
    assert ch["type"] == "changed"
    assert ch["key"] == 2
    assert ch["id_changed"] is False
    assert ch["changed_columns"] == ["b"]


# ---------------------------------------------------------------------------
# compute_diff (sheet-level orchestration)
# ---------------------------------------------------------------------------


def test_compute_diff_sheet_added(make_sheet):
    new = {"new_sheet": make_sheet(["id"], ["A"])}
    diff = compute_diff({}, new)
    assert diff["sheets"]["new_sheet"] == {"event": "added"}
    assert diff["has_errors"] is False


def test_compute_diff_sheet_removed(make_sheet):
    old = {"gone": make_sheet(["id"], ["A"])}
    diff = compute_diff(old, {})
    assert diff["sheets"]["gone"] == {"event": "removed"}
    assert diff["has_errors"] is False


def test_compute_diff_both_sides_empty_sheet():
    diff = compute_diff({"empty": []}, {"empty": []})
    assert diff["sheets"]["empty"] == {"event": "unchanged"}


def test_compute_diff_mixed_with_errors(make_sheet):
    old = {
        "stable": make_sheet(["id", "label"], ["A", "x"]),
        "broken": make_sheet(["id", "label"], ["A", "x"], ["A", "y"]),
        "to_modify": make_sheet(["id", "label"], ["A", "old"]),
    }
    new = {
        "stable": make_sheet(["id", "label"], ["A", "x"]),
        "broken": make_sheet(["id", "label"], ["A", "x"], ["A", "y"]),
        "to_modify": make_sheet(["id", "label"], ["A", "new"]),
        "added_sheet": make_sheet(["id"], ["Z"]),
    }
    diff = compute_diff(old, new)
    assert diff["has_errors"] is True
    assert diff["sheets"]["stable"]["event"] == "unchanged"
    assert diff["sheets"]["broken"]["event"] == "error"
    assert diff["sheets"]["to_modify"]["event"] == "modified"
    assert diff["sheets"]["added_sheet"]["event"] == "added"


def test_compute_diff_no_id_column_takes_positional_path(make_sheet):
    old = {"flat": make_sheet(["a", "b"], ["1", "2"])}
    new = {"flat": make_sheet(["a", "b"], ["1", "X"])}
    diff = compute_diff(old, new)
    sd = diff["sheets"]["flat"]
    assert sd["event"] == "modified"
    assert sd["mode"] == "positional"


# ---------------------------------------------------------------------------
# format_row / highlight_changed_cells
# ---------------------------------------------------------------------------


def test_format_row_pads_to_header_length():
    headers = ["a", "b", "c"]
    assert format_row(headers, ["1", "2"]) == "| 1 | 2 |  |"


def test_format_row_escapes_pipes():
    headers = ["a"]
    assert format_row(headers, ["x|y"]) == "| x\\|y |"


def test_highlight_changed_cells_bolds_only_diff():
    headers = ["a", "b", "c"]
    old = ["1", "2", "3"]
    new = ["1", "X", "3"]
    old_line, new_line = highlight_changed_cells(headers, old, new)
    assert old_line == "| 1 | **2** | 3 |"
    assert new_line == "| 1 | **X** | 3 |"


def test_highlight_changed_cells_pads_short_row():
    headers = ["a", "b"]
    old = ["1"]      # padded to ["1", ""]
    new = ["1", "Y"]
    old_line, new_line = highlight_changed_cells(headers, old, new)
    assert old_line == "| 1 | **** |"
    assert new_line == "| 1 | **Y** |"


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------


def test_render_markdown_covers_each_event(make_sheet):
    diff = {
        "sheets": {
            "added_sheet": {"event": "added"},
            "removed_sheet": {"event": "removed"},
            "untouched": {"event": "unchanged"},
            "dup": {
                "event": "error",
                "error_type": "duplicate_ids",
                "old_duplicates": ["A"],
                "new_duplicates": [],
            },
            "mod": {
                "event": "modified",
                "mode": "id",
                "headers": ["id", "label"],
                "columns_added": [],
                "columns_removed": [],
                "row_changes": [
                    {"type": "added", "key": "X", "row": ["X", "Xenon"]},
                ],
            },
        },
        "has_errors": True,
    }
    out = render_markdown(diff)
    assert "### 🟢 Sheet added: `added_sheet`" in out
    assert "### 🔴 Sheet removed: `removed_sheet`" in out
    assert "### ❌ Sheet: `dup` — Duplicate IDs detected" in out
    assert "Base branch duplicates: `A`" in out
    assert "### 📝 Sheet: `mod`" in out
    # 'unchanged' must not produce a header line
    assert "untouched" not in out


def test_diff_workbooks_matches_render_of_compute(make_sheet):
    old = {"s": make_sheet(["id", "label"], ["A", "x"])}
    new = {"s": make_sheet(["id", "label"], ["A", "y"])}
    assert diff_workbooks(old, new) == render_markdown(compute_diff(old, new))


# ---------------------------------------------------------------------------
# extract_workbook (real xlsx I/O)
# ---------------------------------------------------------------------------


def _build_xlsx(path: Path) -> None:
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "dim_demo"
    ws1.append(["id", "label", "count"])
    ws1.append(["A", "Alpha", 1])
    ws1.append(["B", None, 2.5])  # blank label, float count

    ws2 = wb.create_sheet("dim_other")
    ws2.append(["id", "label"])
    ws2.append(["X", "Xenon"])

    wb.save(path)


def test_extract_workbook_round_trip(tmp_path):
    path = tmp_path / "wb.xlsx"
    _build_xlsx(path)

    data = extract_workbook(str(path))

    assert set(data.keys()) == {"dim_demo", "dim_other"}
    assert data["dim_demo"] == [
        ["id", "label", "count"],
        ["A", "Alpha", "1"],
        ["B", "", "2.5"],
    ]
    assert data["dim_other"] == [
        ["id", "label"],
        ["X", "Xenon"],
    ]


# ---------------------------------------------------------------------------
# get_workbook_at_ref (subprocess mocked)
# ---------------------------------------------------------------------------


def test_get_workbook_at_ref_happy_path(tmp_path, monkeypatch):
    src = tmp_path / "src.xlsx"
    _build_xlsx(src)
    payload = src.read_bytes()

    expected = extract_workbook(str(src))

    def fake_run(cmd, capture_output):
        assert cmd[:2] == ["git", "show"]
        assert cmd[2] == "origin/main:data/dimensions/dimensions.xlsx"
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=payload, stderr=b"")

    monkeypatch.setattr(excel_diff.subprocess, "run", fake_run)

    got = get_workbook_at_ref("data/dimensions/dimensions.xlsx", "origin/main")
    assert got == expected


def test_get_workbook_at_ref_returns_empty_on_git_failure(monkeypatch):
    def fake_run(cmd, capture_output):
        return subprocess.CompletedProcess(
            cmd, returncode=128, stdout=b"", stderr=b"fatal: not in a git repo"
        )

    monkeypatch.setattr(excel_diff.subprocess, "run", fake_run)
    assert get_workbook_at_ref("any/path.xlsx", "origin/missing") == {}


def test_get_workbook_at_ref_swallows_exceptions(monkeypatch):
    def fake_run(cmd, capture_output):
        raise OSError("git binary missing")

    monkeypatch.setattr(excel_diff.subprocess, "run", fake_run)
    assert get_workbook_at_ref("any/path.xlsx", "origin/missing") == {}
