"""
Customer service.

Part 4 requirements:
  - Create, view, edit customers
  - Delete only when no order references them
  - Search by name, email, mobile
  - Filter by active/inactive
  - Only Admin may modify (enforced at route layer via @admin_required)
"""

from sqlalchemy import or_

from app.extensions import db
from app.models import Customer, SalesOrder
from app.utils.helpers import paginate_query, blank_to_none
from app.utils.validators import (
    ValidationError, collect_errors,
    validate_required, validate_email, validate_mobile, validate_length,
)


# ------------------------------------------------------------
# Read
# ------------------------------------------------------------
def list_customers(search: str = "", status: str = "all", page: int = 1, per_page: int = 20):
    """
    Return a paginated list of customers.

    search: matches name OR email OR mobile (case-insensitive)
    status: "all" | "active" | "inactive"
    """
    q = db.session.query(Customer)

    if search and search.strip():
        s = f"%{search.strip()}%"
        q = q.filter(or_(
            Customer.name.ilike(s),
            Customer.email.ilike(s),
            Customer.mobile.ilike(s),
        ))

    status_norm = (status or "all").strip().lower()
    if status_norm == "active":
        q = q.filter(Customer.is_active.is_(True))
    elif status_norm == "inactive":
        q = q.filter(Customer.is_active.is_(False))

    q = q.order_by(Customer.name.asc())
    return paginate_query(q, page=page, per_page=per_page)


def get_customer(customer_id: int) -> Customer:
    """Fetch one customer or raise LookupError → route returns 404."""
    c = db.session.get(Customer, int(customer_id))
    if c is None:
        raise LookupError("Customer not found.")
    return c


# ------------------------------------------------------------
# Write — Create
# ------------------------------------------------------------
def create_customer(form_data: dict) -> Customer:
    """
    Create a customer.

    At least one of email/mobile is required (business rule so customers
    are contactable). All fields validated via validators.py.
    """
    checks = {
        "name":   validate_required(form_data.get("name"), "Name"),
        "email":  validate_email(form_data.get("email")),
        "mobile": validate_mobile(form_data.get("mobile")),
        "city":   validate_length(blank_to_none(form_data.get("city")), "City", max_len=100),
    }
    errors = collect_errors(checks)
    if errors:
        raise ValidationError(" ".join(errors))

    name   = checks["name"][0]
    email  = checks["email"][0]
    mobile = checks["mobile"][0]
    city   = checks["city"][0]

    if not email and not mobile:
        raise ValidationError("Provide at least one of: email or mobile.")

    customer = Customer(
        name=name, email=email, mobile=mobile, city=city,
        is_active=True,
    )
    db.session.add(customer)
    db.session.commit()
    return customer


# ------------------------------------------------------------
# Write — Update
# ------------------------------------------------------------
def update_customer(customer_id: int, form_data: dict) -> Customer:
    """Edit any of: name, email, mobile, city, is_active."""
    customer = get_customer(customer_id)

    checks = {
        "name":   validate_required(form_data.get("name", customer.name), "Name"),
        "email":  validate_email(form_data.get("email", customer.email)),
        "mobile": validate_mobile(form_data.get("mobile", customer.mobile)),
        "city":   validate_length(blank_to_none(form_data.get("city", customer.city)),
                                  "City", max_len=100),
    }
    errors = collect_errors(checks)
    if errors:
        raise ValidationError(" ".join(errors))

    email, mobile = checks["email"][0], checks["mobile"][0]
    if not email and not mobile:
        raise ValidationError("Provide at least one of: email or mobile.")

    customer.name   = checks["name"][0]
    customer.email  = email
    customer.mobile = mobile
    customer.city   = checks["city"][0]

    # Allow toggling status via form
    if "is_active" in form_data:
        raw = form_data.get("is_active")
        customer.is_active = raw in (True, "true", "True", "1", 1, "on")

    db.session.commit()
    return customer


# ------------------------------------------------------------
# Write — Delete (safe)
# ------------------------------------------------------------
def delete_customer(customer_id: int) -> None:
    """
    Delete a customer ONLY if no sales order references it.

    Part 3 + Part 4: prevent delete; allow deactivation instead.
    """
    customer = get_customer(customer_id)

    order_exists = db.session.query(
        SalesOrder.query.filter(SalesOrder.customer_id == customer.id).exists()
    ).scalar()

    if order_exists:
        raise ValidationError(
            "Cannot delete this customer: it has sales orders. "
            "Deactivate it instead."
        )

    db.session.delete(customer)
    db.session.commit()


# ------------------------------------------------------------
# Convenience
# ------------------------------------------------------------
def active_customers_for_select():
    """Used by the order-creation form to populate the customer dropdown."""
    return db.session.query(Customer).filter(
        Customer.is_active.is_(True)
    ).order_by(Customer.name.asc()).all()