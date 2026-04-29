"""Shared fixtures and helpers for the .github/scripts test suite."""

import pytest


def _make_sheet(headers: list[str], *rows: list[str]) -> list[list[str]]:
    return [list(headers), *(list(r) for r in rows)]


@pytest.fixture
def make_sheet():
    return _make_sheet
