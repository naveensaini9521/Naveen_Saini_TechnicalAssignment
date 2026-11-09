"""
Tests for order calculations (Part 5 / Part 12).

Covers:
  - Assignment's worked example (4500 → 450 → 4050)
  - Zero / negative quantity rejected
  - Discount outside 0–20 rejected
  - Empty item list rejected
  - Decimal precision (ROUND_HALF_UP)
"""

import pytest
from decimal import Decimal

from app.utils.calculations import (
    compute_totals, compute_line_amount, validate_discount, CalculationError,
)


class TestWorkedExample:
    """The exact example from the assignment (page 8)."""

    def test_keyboard_and_mouse_10_percent(self):
        items = [
            {"quantity": 2, "rate": "1500.00"},
            {"quantity": 3, "rate": "500.00"},
        ]
        r = compute_totals(items, "10")
        assert r["subtotal"]        == Decimal("4500.00")
        assert r["discount_amount"] == Decimal("450.00")
        assert r["grand_total"]     == Decimal("4050.00")

    def test_line_amounts_recorded(self):
        items = [
            {"quantity": 2, "rate": "1500.00"},
            {"quantity": 3, "rate": "500.00"},
        ]
        r = compute_totals(items, "10")
        assert r["lines"][0]["amount"] == Decimal("3000.00")
        assert r["lines"][1]["amount"] == Decimal("1500.00")


class TestQuantity:
    def test_zero_quantity_rejected(self):
        with pytest.raises(CalculationError):
            compute_totals([{"quantity": 0, "rate": "100"}], 0)

    def test_negative_quantity_rejected(self):
        with pytest.raises(CalculationError):
            compute_totals([{"quantity": -1, "rate": "100"}], 0)

    def test_zero_quantity_rejected_at_line_level(self):
        with pytest.raises(CalculationError):
            compute_line_amount(0, "100")


class TestDiscount:
    def test_zero_discount_allowed(self):
        r = compute_totals([{"quantity": 1, "rate": "100"}], "0")
        assert r["discount_amount"] == Decimal("0.00")
        assert r["grand_total"]     == Decimal("100.00")

    def test_twenty_percent_allowed(self):
        r = compute_totals([{"quantity": 1, "rate": "100"}], "20")
        assert r["discount_amount"] == Decimal("20.00")
        assert r["grand_total"]     == Decimal("80.00")

    def test_above_twenty_rejected(self):
        with pytest.raises(CalculationError):
            compute_totals([{"quantity": 1, "rate": "100"}], "20.01")

    def test_negative_discount_rejected(self):
        with pytest.raises(CalculationError):
            validate_discount("-1")


class TestEmptyItems:
    def test_empty_list_rejected(self):
        with pytest.raises(CalculationError):
            compute_totals([], 0)


class TestRounding:
    def test_round_half_up(self):
        # 1 * 0.125 = 0.125 → 0.13 (ROUND_HALF_UP)
        r = compute_totals([{"quantity": 1, "rate": "0.125"}], 0)
        assert r["subtotal"] == Decimal("0.13")

    def test_decimal_not_float(self):
        r = compute_totals([{"quantity": 1, "rate": "99.99"}], "10")
        assert isinstance(r["subtotal"], Decimal)
        assert r["subtotal"] == Decimal("99.99")