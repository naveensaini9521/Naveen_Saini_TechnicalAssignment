"""
Generic helpers.

Small, dependency-light functions used across services and routes.
No imports from app.models or app.services here — keep this layer clean.
"""

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP


# ------------------------------------------------------------
# Money
# ------------------------------------------------------------
TWO_PLACES = Decimal("0.01")


def money_round(value) -> Decimal:
    """
    Round a money value to 2 decimal places using ROUND_HALF_UP.

    Consistent rounding everywhere (Part 5: "Round monetary amounts
    to two decimal places using a consistent rule").
    """
    if value is None:
        return Decimal("0.00")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# ------------------------------------------------------------
# Dates
# ------------------------------------------------------------
def today() -> date:
    return date.today()


def utcnow() -> datetime:
    """Timezone-aware UTC now (avoids naive-datetime bugs)."""
    return datetime.now(timezone.utc)


def parse_date(value, field_name: str = "date") -> date:
    """
    Parse an ISO date string ('YYYY-MM-DD').

    Raises ValueError with a clear message on bad input.
    """
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {field_name}: expected YYYY-MM-DD, got {value!r}")


# ------------------------------------------------------------
# Order numbers
# ------------------------------------------------------------
def generate_order_number(seq: int) -> str:
    """
    Build an order number: SO-YYYYMMDD-XXXX (seq zero-padded to 4).

    Example: SO-20260115-0001
    Caller passes the next sequence value from the DB (see order_service).
    """
    return f"SO-{date.today().strftime('%Y%m%d')}-{seq:04d}"


# ------------------------------------------------------------
# Pagination
# ------------------------------------------------------------
def paginate_query(query, page: int = 1, per_page: int = 20):
    """
    Wrap a SQLAlchemy query with Flask-SQLAlchemy's paginate helper.

    Returns a Pagination object with .items, .total, .pages, .page, .has_next, .has_prev.
    Clamps page to >= 1 and per_page to 1..100.
    """
    page = max(1, int(page or 1))
    per_page = min(max(1, int(per_page or 20)), 100)
    return query.paginate(page=page, per_page=per_page, error_out=False)


# ------------------------------------------------------------
# Safe string / number parsing
# ------------------------------------------------------------
def to_int(value, field_name: str = "value") -> int:
    """Parse an integer with a clear error message."""
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a whole number, got {value!r}")


def to_decimal(value, field_name: str = "value") -> Decimal:
    """Parse a decimal with a clear error message."""
    try:
        return Decimal(str(value).strip())
    except Exception:
        raise ValueError(f"{field_name} must be a number, got {value!r}")


def blank_to_none(value):
    """Convert empty/whitespace-only strings to None (for nullable fields)."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None