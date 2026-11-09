"""
Field validation helpers.

Used by services (customer/product/order) and CSV import.
Each validator returns (cleaned_value, error_message_or_None):

    value, err = validate_email("foo@bar.com")
    if err:
        raise ValidationError(err)

Keeps all field rules in ONE place (Part 13: no duplicated validation).
"""

import re
from decimal import Decimal

from app.utils.helpers import blank_to_none


class ValidationError(ValueError):
    """Raised when a field fails validation. Routes convert to 400."""


# ------------------------------------------------------------
# Patterns
# ------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOBILE_RE = re.compile(r"^\+?[0-9]{7,15}$")   # digits only, optional leading +
CODE_RE   = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_]{1,49}$")   # 2..50 chars

VALID_STATUSES = {"active", "inactive"}


# ------------------------------------------------------------
# Generic helpers
# ------------------------------------------------------------
def validate_required(value, field_name: str):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, f"{field_name} is required."
    return (value.strip() if isinstance(value, str) else value), None


def validate_length(value, field_name: str, min_len: int = 0, max_len: int = 255):
    s = "" if value is None else str(value)
    if len(s) < min_len:
        return None, f"{field_name} must be at least {min_len} characters."
    if len(s) > max_len:
        return None, f"{field_name} must be at most {max_len} characters."
    return s, None


def validate_int(value, field_name: str, min_value=None, max_value=None):
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return None, f"{field_name} must be a whole number."
    if min_value is not None and n < min_value:
        return None, f"{field_name} must be ≥ {min_value}."
    if max_value is not None and n > max_value:
        return None, f"{field_name} must be ≤ {max_value}."
    return n, None


def validate_decimal(value, field_name: str, min_value=None, max_value=None, places: int = 2):
    try:
        d = Decimal(str(value).strip())
    except Exception:
        return None, f"{field_name} must be a number."
    if min_value is not None and d < Decimal(str(min_value)):
        return None, f"{field_name} must be ≥ {min_value}."
    if max_value is not None and d > Decimal(str(max_value)):
        return None, f"{field_name} must be ≤ {max_value}."
    # Check decimal places
    if -d.as_tuple().exponent > places:
        return None, f"{field_name} must have at most {places} decimal places."
    return d, None


# ------------------------------------------------------------
# Domain fields
# ------------------------------------------------------------
def validate_email(value, required: bool = False):
    v = blank_to_none(value)
    if v is None:
        return (None, "Email is required.") if required else (None, None)
    v = v.lower()
    if not EMAIL_RE.match(v):
        return None, "Invalid email address."
    return v, None


def validate_mobile(value, required: bool = False):
    v = blank_to_none(value)
    if v is None:
        return (None, "Mobile is required.") if required else (None, None)
    v = v.replace(" ", "").replace("-", "")
    if not MOBILE_RE.match(v):
        return None, "Invalid mobile number (7–15 digits, optional +)."
    return v, None


def validate_product_code(value):
    v, err = validate_required(value, "Product code")
    if err:
        return None, err
    if not CODE_RE.match(v):
        return None, "Product code must be 2–50 chars, letters/digits/-/_."
    return v.upper(), None


def validate_status(value, default_active: bool = True):
    """Accepts 'Active'/'Inactive' (any case) → returns True/False."""
    if value is None or str(value).strip() == "":
        return default_active, None
    s = str(value).strip().lower()
    if s not in VALID_STATUSES:
        return None, "Status must be 'Active' or 'Inactive'."
    return s == "active", None


def validate_discount(value):
    """Percent 0..20, returns Decimal."""
    if value is None or str(value).strip() == "":
        return Decimal("0"), None
    d, err = validate_decimal(value, "Discount %", min_value=0, max_value=20)
    if err:
        return None, err
    return d, None


# ------------------------------------------------------------
# Aggregate: collect all field errors at once
# ------------------------------------------------------------
def collect_errors(fields_dict: dict) -> list[str]:
    """
    Given {"field": (value, error_or_None), ...}, return list of error strings.

    Usage:
        checks = {
            "name":   validate_required(name, "Name"),
            "email":  validate_email(email),
            "mobile": validate_mobile(mobile),
        }
        errors = collect_errors(checks)
        if errors:
            raise ValidationError(" ".join(errors))
    """
    return [err for (_val, err) in fields_dict.values() if err]