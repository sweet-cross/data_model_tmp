"""Tests for .github/scripts/compute_version_bump.py."""

import pytest

from compute_version_bump import (
    apply_bump,
    classify_diff,
    fmt_version,
    parse_version,
    read_version,
)


# ---------------------------------------------------------------------------
# Helpers to build structured diffs in the shape compute_diff produces.
# ---------------------------------------------------------------------------


def _diff(**sheets) -> dict:
    return {"sheets": sheets, "has_errors": False}


def _modified(
    *,
    columns_added=None,
    columns_removed=None,
    row_changes=None,
    mode="id",
) -> dict:
    return {
        "event": "modified",
        "mode": mode,
        "headers": ["id", "label"],
        "columns_added": columns_added or [],
        "columns_removed": columns_removed or [],
        "row_changes": row_changes or [],
    }


def _row_changed(key, changed_columns, *, id_changed=False) -> dict:
    return {
        "type": "changed",
        "key": key,
        "old_row": ["?", "?"],
        "new_row": ["?", "?"],
        "changed_columns": list(changed_columns),
        "id_changed": id_changed,
    }


# ---------------------------------------------------------------------------
# classify_diff — one test per rule from the module docstring rule table.
# ---------------------------------------------------------------------------


def test_classify_empty_diff():
    level, summary = classify_diff(_diff())
    assert level == "none"
    assert summary == []


def test_classify_sheet_added():
    level, summary = classify_diff(_diff(dim_new={"event": "added"}))
    assert level == "minor"
    assert any("[MINOR]" in line and "dim_new" in line for line in summary)


def test_classify_sheet_removed():
    level, summary = classify_diff(_diff(dim_gone={"event": "removed"}))
    assert level == "major"
    assert any("[MAJOR]" in line and "dim_gone" in line for line in summary)


def test_classify_column_added():
    level, _ = classify_diff(_diff(s=_modified(columns_added=["new_col"])))
    assert level == "minor"


def test_classify_column_removed():
    level, _ = classify_diff(_diff(s=_modified(columns_removed=["old_col"])))
    assert level == "major"


def test_classify_row_added():
    level, _ = classify_diff(
        _diff(s=_modified(row_changes=[{"type": "added", "key": "B01", "row": []}]))
    )
    assert level == "minor"


def test_classify_row_deleted():
    level, _ = classify_diff(
        _diff(s=_modified(row_changes=[{"type": "deleted", "key": "B01", "row": []}]))
    )
    assert level == "major"


def test_classify_row_changed_label_only_is_patch():
    level, _ = classify_diff(
        _diff(s=_modified(row_changes=[_row_changed("B01", ["label"])]))
    )
    assert level == "patch"


def test_classify_row_changed_description_only_is_patch():
    level, _ = classify_diff(
        _diff(s=_modified(row_changes=[_row_changed("B01", ["description"])]))
    )
    assert level == "patch"


def test_classify_row_changed_label_and_description_is_patch():
    level, _ = classify_diff(
        _diff(s=_modified(row_changes=[_row_changed("B01", ["label", "description"])]))
    )
    assert level == "patch"


def test_classify_row_changed_parent_id_is_minor():
    level, _ = classify_diff(
        _diff(s=_modified(row_changes=[_row_changed("B01", ["parent_id"])]))
    )
    assert level == "minor"


def test_classify_row_changed_level_is_minor():
    level, _ = classify_diff(
        _diff(s=_modified(row_changes=[_row_changed("B01", ["level"])]))
    )
    assert level == "minor"


def test_classify_row_changed_mixed_label_and_parent_id_is_minor():
    # Mixed → not a subset of PATCH_COLUMNS → MINOR.
    level, _ = classify_diff(
        _diff(s=_modified(row_changes=[_row_changed("B01", ["label", "parent_id"])]))
    )
    assert level == "minor"


def test_classify_id_changed_overrides_columns_to_major():
    # Even if changed_columns would otherwise classify as PATCH, id_changed=True
    # forces MAJOR.
    level, summary = classify_diff(
        _diff(
            s=_modified(
                row_changes=[_row_changed("B01", ["label"], id_changed=True)],
            )
        )
    )
    assert level == "major"
    assert any("primary-key change" in line for line in summary)


def test_classify_row_changed_empty_columns_is_minor():
    # changed_columns=[] hits the 'columns differ' fallback branch.
    level, summary = classify_diff(
        _diff(s=_modified(row_changes=[_row_changed("B01", [])]))
    )
    assert level == "minor"
    assert any("columns differ" in line for line in summary)


def test_classify_error_sheet_contributes_nothing():
    diff = _diff(
        s={
            "event": "error",
            "error_type": "duplicate_ids",
            "old_duplicates": ["A"],
            "new_duplicates": [],
        }
    )
    level, summary = classify_diff(diff)
    assert level == "none"
    assert summary == []


def test_classify_highest_level_wins_across_sheets():
    diff = _diff(
        s_patch=_modified(row_changes=[_row_changed("A", ["label"])]),
        s_major=_modified(row_changes=[{"type": "deleted", "key": "B", "row": []}]),
    )
    level, summary = classify_diff(diff)
    assert level == "major"
    # Both sheets must contribute summary lines, regardless of overall level.
    assert any("[PATCH]" in line for line in summary)
    assert any("[MAJOR]" in line for line in summary)


# ---------------------------------------------------------------------------
# parse_version / fmt_version
# ---------------------------------------------------------------------------


def test_parse_fmt_round_trip():
    assert fmt_version(parse_version("1.2.3")) == "1.2.3"


def test_parse_version_tolerates_whitespace():
    assert parse_version("  0.1.0\n") == (0, 1, 0)


@pytest.mark.parametrize("bad", ["1.2", "1.2.3.4", "1.x.0", "", "v1.2.3"])
def test_parse_version_rejects_malformed(bad):
    with pytest.raises(ValueError):
        parse_version(bad)


# ---------------------------------------------------------------------------
# apply_bump
# ---------------------------------------------------------------------------


def test_apply_bump_major_no_pre_1_0():
    assert apply_bump((1, 2, 3), "major", pre_1_0_mapping=False) == ((2, 0, 0), "major")


def test_apply_bump_minor_no_pre_1_0():
    assert apply_bump((1, 2, 3), "minor", pre_1_0_mapping=False) == ((1, 3, 0), "minor")


def test_apply_bump_patch_no_pre_1_0():
    assert apply_bump((1, 2, 3), "patch", pre_1_0_mapping=False) == ((1, 2, 4), "patch")


def test_apply_bump_none_is_noop():
    assert apply_bump((1, 2, 3), "none", pre_1_0_mapping=False) == ((1, 2, 3), "none")


def test_apply_bump_pre_1_0_demotes_major_to_minor():
    assert apply_bump((0, 1, 0), "major", pre_1_0_mapping=True) == ((0, 2, 0), "minor")


def test_apply_bump_pre_1_0_demotes_minor_to_patch():
    assert apply_bump((0, 1, 0), "minor", pre_1_0_mapping=True) == ((0, 1, 1), "patch")


def test_apply_bump_pre_1_0_keeps_patch():
    assert apply_bump((0, 1, 0), "patch", pre_1_0_mapping=True) == ((0, 1, 1), "patch")


def test_apply_bump_pre_1_0_disabled_takes_literal_major_to_1_0_0():
    assert apply_bump((0, 1, 0), "major", pre_1_0_mapping=False) == ((1, 0, 0), "major")


def test_apply_bump_pre_1_0_flag_inert_above_major_zero():
    # major >= 1 → mapping does nothing even when the flag is on.
    assert apply_bump((1, 5, 9), "major", pre_1_0_mapping=True) == ((2, 0, 0), "major")
    assert apply_bump((1, 5, 9), "minor", pre_1_0_mapping=True) == ((1, 6, 0), "minor")


# ---------------------------------------------------------------------------
# read_version
# ---------------------------------------------------------------------------


def test_read_version_missing_file(tmp_path):
    assert read_version(tmp_path / "missing") == "0.0.0"


def test_read_version_empty_file(tmp_path):
    p = tmp_path / "VERSION"
    p.write_text("")
    assert read_version(p) == "0.0.0"


def test_read_version_strips_trailing_newline(tmp_path):
    p = tmp_path / "VERSION"
    p.write_text("1.2.3\n")
    assert read_version(p) == "1.2.3"


def test_read_version_whitespace_only_is_zero(tmp_path):
    p = tmp_path / "VERSION"
    p.write_text("   \n\t ")
    assert read_version(p) == "0.0.0"
