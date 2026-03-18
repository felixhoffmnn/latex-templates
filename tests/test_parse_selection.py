"""Tests for invoice_cli/invoice.py: _parse_selection."""

import pytest

from invoice_toolkit.cli.invoice import _parse_selection


@pytest.mark.parametrize(
    ("selection", "max_index", "expected"),
    [
        pytest.param("0", 5, [0], id="single_index"),
        pytest.param("0,2,4", 5, [0, 2, 4], id="multiple_indices"),
        pytest.param("1-3", 5, [1, 2, 3], id="range"),
        pytest.param("0,2-4,6", 6, [0, 2, 3, 4, 6], id="mixed_indices_and_ranges"),
        pytest.param("1,1,2", 5, [1, 2], id="duplicates_deduplicated"),
        pytest.param("0,99", 5, [0], id="out_of_bounds_filtered"),
        pytest.param("abc,xyz", 5, None, id="all_invalid_returns_none"),
        pytest.param("", 5, None, id="empty_string_returns_none"),
        pytest.param(" 1 , 2 - 4 ", 5, [1, 2, 3, 4], id="whitespace_handling"),
        pytest.param("-1,0,1", 5, [0, 1], id="negative_indices_filtered"),
        pytest.param("10", 5, None, id="single_out_of_bounds_returns_none"),
        pytest.param("4-8", 5, [4, 5], id="range_partially_out_of_bounds"),
        pytest.param("3,1,2", 5, [3, 1, 2], id="preserves_input_order"),
        pytest.param("2,1-3", 5, [2, 1, 3], id="range_with_duplicate_overlap"),
    ],
)
def test_parse_selection(selection, max_index, expected):
    assert _parse_selection(selection, max_index=max_index) == expected
