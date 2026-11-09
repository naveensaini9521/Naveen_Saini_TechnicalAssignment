"""
Order calculation rules.

This module is the ONLY place in the codebase that computes
order money values (Part 5 / Part 13: "avoid duplicated calculation logic").

Rules (from the assignment):

    Item Amount      = Quantity × Rate
    Subtotal         = Sum of Item Amounts
    Discount Amount  = Subtotal × Discount Percentage / 100
    Grand Total      = Subtotal − Discount Amount

All values are Decimal, rounded to 2 decimals with ROUND_HALF_UP.
"""

from decimal import Decimal
from app.utils.helpers import money_round


class CalculationError(ValueError):
    """Raised when inputs violate calculation rules (used to produce 400s)."""


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
MIN_DISCOUNT = Decimal("0")
MAX_DISCOUNT = Decimal("20")
MIN_QTY = 1


# ------------------------------------------------------------
# Line-level
# ------------------------------------------------------------
def compute_line_amount(quantity, rate) -> Decimal:
    """
    Item amount = quantity × rate, rounded to 2 decimals.

    Rejects zero / negative quantity (Part 12 test case).
    """
    qty = int(quantity)
    rate_d = Decimal(str(rate))

    if qty < MIN_QTY:
        raise CalculationError(f"Quantity must be at least {MIN_QTY}, got {qty}.")
    if rate_d < 0:
        raise CalculationError(f"Rate cannot be negative, got {rate_d}.")

    return money_round(Decimal(qty) * rate_d)


# ------------------------------------------------------------
# Order-level
# ------------------------------------------------------------
def validate_discount(percent) -> Decimal:
    """Ensure discount is between 0 and 20 inclusive (Part 5)."""
    pct = Decimal(str(percent))
    if pct < MIN_DISCOUNT or pct > MAX_DISCOUNT:
        raise CalculationError(
            f"Discount percentage must be between {MIN_DISCOUNT} and {MAX_DISCOUNT}, got {pct}."
        )
    return pct


def compute_totals(items, discount_percentage) -> dict:
    """
    Compute subtotal, discount_amount, grand_total for an order.

    `items` is a list of dicts, each with at least 'quantity' and 'rate'.
    Returns a dict with Decimal values:

        {
            "subtotal":        Decimal("4500.00"),
            "discount_amount": Decimal("450.00"),
            "grand_total":     Decimal("4050.00"),
            "lines":           [{"quantity": 2, "rate": 1500.00, "amount": 3000.00}, ...],
        }

    The `lines` field lets services persist `amount` per item without
    recomputing it themselves.
    """
    if not items:
        raise CalculationError("Order must contain at least one item.")

    discount_pct = validate_discount(discount_percentage)

    lines = []
    subtotal = Decimal("0")

    for idx, item in enumerate(items, start=1):
        try:
            qty = int(item["quantity"])
            rate = Decimal(str(item["rate"]))
        except KeyError as e:
            raise CalculationError(f"Line {idx}: missing field {e.args[0]!r}.")
        except (TypeError, ValueError):
            raise CalculationError(f"Line {idx}: quantity and rate must be numbers.")

        amount = compute_line_amount(qty, rate)
        subtotal += amount

        lines.append({"quantity": qty, "rate": rate, "amount": amount})

    subtotal = money_round(subtotal)
    discount_amount = money_round(subtotal * discount_pct / Decimal("100"))
    grand_total = money_round(subtotal - discount_amount)

    # Final safety: grand total must never be negative
    if grand_total < 0:
        raise CalculationError("Grand total cannot be negative.")

    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "grand_total": grand_total,
        "lines": lines,
    }
    
# ------------------------------------------------------------
# Debugging exercise (Part 11)
# ------------------------------------------------------------
def calculate_total(items) -> float:
    """
    Calculate the total amount of all items.

    Fixed from the assignment's faulty version:
        amount = item["qty"] * item["rate"]
        total = amount              # ← BUG: overwrites instead of adds
    Fixed:
        total += amount

    Validates inputs — raises ValueError on missing/invalid data.
    Returns 0 for an empty list.
    """
    if not items:
        return 0

    total = 0
    for idx, item in enumerate(items, start=1):
        try:
            qty = item["qty"]
            rate = item["rate"]
        except (KeyError, TypeError) as e:
            raise ValueError(f"Item {idx}: missing field {e}.")
        if not isinstance(qty, (int, float)) or not isinstance(rate, (int, float)):
            raise ValueError(f"Item {idx}: qty and rate must be numbers.")
        if qty < 0 or rate < 0:
            raise ValueError(f"Item {idx}: qty and rate cannot be negative.")
        total += qty * rate
    return total