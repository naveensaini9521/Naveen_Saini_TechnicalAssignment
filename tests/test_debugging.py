"""
Debugging exercise tests (Part 11).

Proves:
  - The assignment's sample input now returns 350 (was 150 in the buggy code).
  - Empty list returns 0.
  - Missing keys raise a clear error.
  - Invalid types raise a clear error.
  - Negative values raise a clear error.
  - Single-item and multi-item cases work.
"""

import pytest

from app.utils.calculations import calculate_total


class TestAssignmentCase:
    def test_assignment_sample_returns_350(self):
        """
        The exact input from the assignment.
        Buggy version returned 150 (last item only).
        Corrected version must return 350.
        """
        items = [
            {"qty": 2, "rate": 100},
            {"qty": 3, "rate": 50},
        ]
        assert calculate_total(items) == 350

    def test_buggy_version_would_return_150(self):
        """Demonstrates the bug explicitly — the last amount, not the sum."""
        items = [
            {"qty": 2, "rate": 100},
            {"qty": 3, "rate": 50},
        ]
        # Reproduce the buggy behaviour inline for the test
        total_buggy = 0
        for item in items:
            amount = item["qty"] * item["rate"]
            total_buggy = amount      # buggy: overwrite
        assert total_buggy == 150
        # The fixed function gives 350
        assert calculate_total(items) == 350


class TestEdgeCases:
    def test_empty_list_returns_zero(self):
        assert calculate_total([]) == 0

    def test_single_item(self):
        assert calculate_total([{"qty": 5, "rate": 100}]) == 500

    def test_many_items(self):
        items = [{"qty": i, "rate": 10} for i in range(1, 6)]
        assert calculate_total(items) == 10 * (1 + 2 + 3 + 4 + 5)


class TestValidation:
    def test_missing_qty_raises(self):
        with pytest.raises(ValueError, match="missing field"):
            calculate_total([{"rate": 100}])

    def test_missing_rate_raises(self):
        with pytest.raises(ValueError, match="missing field"):
            calculate_total([{"qty": 2}])

    def test_non_numeric_qty_raises(self):
        with pytest.raises(ValueError, match="must be numbers"):
            calculate_total([{"qty": "abc", "rate": 100}])

    def test_negative_qty_raises(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            calculate_total([{"qty": -1, "rate": 100}])

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            calculate_total([{"qty": 1, "rate": -100}])