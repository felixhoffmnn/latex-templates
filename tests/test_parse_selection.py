"""Tests for invoice_cli/invoice.py: _parse_selection."""

from invoice_toolkit.cli.invoice import _parse_selection


class TestParseSelection:
    def test_single_index(self):
        assert _parse_selection("0", max_index=5) == [0]

    def test_multiple_indices(self):
        assert _parse_selection("0,2,4", max_index=5) == [0, 2, 4]

    def test_range(self):
        assert _parse_selection("1-3", max_index=5) == [1, 2, 3]

    def test_mixed_indices_and_ranges(self):
        assert _parse_selection("0,2-4,6", max_index=6) == [0, 2, 3, 4, 6]

    def test_duplicates_deduplicated(self):
        assert _parse_selection("1,1,2", max_index=5) == [1, 2]

    def test_out_of_bounds_filtered(self):
        assert _parse_selection("0,99", max_index=5) == [0]

    def test_all_invalid_returns_none(self):
        assert _parse_selection("abc,xyz", max_index=5) is None

    def test_empty_string_returns_none(self):
        assert _parse_selection("", max_index=5) is None

    def test_whitespace_handling(self):
        assert _parse_selection(" 1 , 2 - 4 ", max_index=5) == [1, 2, 3, 4]

    def test_negative_indices_filtered(self):
        assert _parse_selection("-1,0,1", max_index=5) == [0, 1]

    def test_single_out_of_bounds_returns_none(self):
        assert _parse_selection("10", max_index=5) is None

    def test_range_partially_out_of_bounds(self):
        assert _parse_selection("4-8", max_index=5) == [4, 5]

    def test_preserves_input_order(self):
        assert _parse_selection("3,1,2", max_index=5) == [3, 1, 2]

    def test_range_with_duplicate_overlap(self):
        assert _parse_selection("2,1-3", max_index=5) == [2, 1, 3]
