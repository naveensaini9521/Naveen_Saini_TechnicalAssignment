# Debugging Exercise (Part 11)

## Original Faulty Code

```python
def calculate_total(items):
    total = 0
    for item in items:
        amount = item["qty"] * item["rate"]
        total = amount              # ← BUG
    return total
```

## Cause of the Incorrect Result

The line `total = amount` overwrites the running total on every iteration instead of adding to it. Only the last item's amount survives.

For the assignment's input:

```python
items = [
    {"qty": 2, "rate": 100},
    {"qty": 3, "rate": 50},
]
```

Trace:

| Iteration | `amount`      | `total` after line                 |
| --------- | ------------- | ---------------------------------- |
| 1         | 2 × 100 = 200 | 200                                |
| 2         | 3 × 50 = 150  | **150** ← previous value discarded |

Return: **150** ❌ (expected **350**)

The correction is to use the accumulation operator `+=` instead of the assignment operator `=`.

## Corrected Function

```python
def calculate_total(items):
    if not items:
        return 0
    total = 0
    for idx, item in enumerate(items, start=1):
        try:
            qty  = item["qty"]
            rate = item["rate"]
        except (KeyError, TypeError):
            raise ValueError(f"Item {idx}: missing qty or rate.")
        if not isinstance(qty, (int, float)) or not isinstance(rate, (int, float)):
            raise ValueError(f"Item {idx}: qty and rate must be numbers.")
        if qty < 0 or rate < 0:
            raise ValueError(f"Item {idx}: qty and rate cannot be negative.")
        total += qty * rate            # ✅ FIX: accumulate
    return total
```

The single-character fix: `total += qty * rate` (was `total = amount`).

## Behaviour Summary

| Scenario           | Input                                                   | Behaviour                                                       |
| ------------------ | ------------------------------------------------------- | --------------------------------------------------------------- |
| Assignment example | `[{"qty": 2, "rate": 100}, {"qty": 3, "rate": 50}]`     | Returns `350`                                                   |
| Empty list         | `[]`                                                    | Returns `0`                                                     |
| Single item        | `[{"qty": 5, "rate": 100}]`                             | Returns `500`                                                   |
| Many items         | `[{"qty": 1, "rate": 10}, ..., {"qty": 5, "rate": 10}]` | Returns `150`                                                   |
| Missing qty        | `[{"rate": 100}]`                                       | Raises `ValueError("Item 1: missing qty or rate.")`             |
| Missing rate       | `[{"qty": 2}]`                                          | Raises `ValueError("Item 1: missing qty or rate.")`             |
| Non-numeric values | `[{"qty": "abc", "rate": 100}]`                         | Raises `ValueError("Item 1: qty and rate must be numbers.")`    |
| Negative quantity  | `[{"qty": -1, "rate": 100}]`                            | Raises `ValueError("Item 1: qty and rate cannot be negative.")` |
| Negative rate      | `[{"qty": 1, "rate": -100}]`                            | Raises `ValueError("Item 1: qty and rate cannot be negative.")` |

## Test Evidence

The corrected function lives in `app/utils/calculations.py` alongside the rest of the order math.

Tests live in `tests/test_debugging.py` and are grouped into three classes:

### `TestAssignmentCase` — proves the fix

- `test_assignment_sample_returns_350` — the exact input from the assignment returns `350` ✅
- `test_buggy_version_would_return_150` — reproduces the buggy behaviour inline to show why the original returned the wrong value, and asserts that the fixed function returns `350` on the same input

### `TestEdgeCases` — edge behaviour

- `test_empty_list_returns_zero` — `[]` → `0`
- `test_single_item` — one item returns the item's qty × rate
- `test_many_items` — 5 items return the correct cumulative sum

### `TestValidation` — invalid inputs raise clear errors

- `test_missing_qty_raises` — missing qty → `ValueError`
- `test_missing_rate_raises` — missing rate → `ValueError`
- `test_non_numeric_qty_raises` — string qty → `ValueError`
- `test_negative_qty_raises` — negative qty → `ValueError`
- `test_negative_rate_raises` — negative rate → `ValueError`

## How to Run the Tests

```bash
pytest tests/test_debugging.py -v
```

Expected output:

```text
tests/test_debugging.py::TestAssignmentCase::test_assignment_sample_returns_350 PASSED
tests/test_debugging.py::TestAssignmentCase::test_buggy_version_would_return_150 PASSED
tests/test_debugging.py::TestEdgeCases::test_empty_list_returns_zero PASSED
tests/test_debugging.py::TestEdgeCases::test_single_item PASSED
tests/test_debugging.py::TestEdgeCases::test_many_items PASSED
tests/test_debugging.py::TestValidation::test_missing_qty_raises PASSED
tests/test_debugging.py::TestValidation::test_missing_rate_raises PASSED
tests/test_debugging.py::TestValidation::test_non_numeric_qty_raises PASSED
tests/test_debugging.py::TestValidation::test_negative_qty_raises PASSED
tests/test_debugging.py::TestValidation::test_negative_rate_raises PASSED

10 passed in X.XXs
```
