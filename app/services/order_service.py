"""
Order service — Draft, Confirm, Cancel.

Parts 5 & 6: backend-calculated totals, transactional stock updates,
idempotency, concurrency safety.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.extensions import db
from app.models import (
    SalesOrder, SalesOrderItem, Product, Customer, StockMovement,
)
from app.utils.calculations import compute_totals, CalculationError
from app.utils.helpers import generate_order_number, parse_date
from app.utils.validators import ValidationError, validate_discount


class OrderError(Exception):
    """Business-rule violation on an order (state machine, stock, etc.)."""


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _next_order_sequence() -> int:
    today_prefix = f"SO-{date.today().strftime('%Y%m%d')}-"
    count = db.session.query(SalesOrder).filter(
        SalesOrder.order_number.like(f"{today_prefix}%")
    ).count()
    return count + 1


def _get_order(order_id: int) -> SalesOrder:
    order = db.session.get(SalesOrder, int(order_id))
    if order is None:
        raise LookupError("Order not found.")
    return order


def _load_and_validate_items(items_payload: list) -> list[dict]:
    if not items_payload:
        raise ValidationError("Order must contain at least one item.")
    seen = set()
    result = []
    for idx, item in enumerate(items_payload, start=1):
        try:
            pid = int(item["product_id"])
            qty = int(item["quantity"])
        except (KeyError, TypeError, ValueError):
            raise ValidationError(f"Line {idx}: product_id and quantity are required.")
        if pid in seen:
            raise ValidationError(f"Duplicate product in order (product_id={pid}).")
        seen.add(pid)

        product = db.session.get(Product, pid)
        if product is None:
            raise ValidationError(f"Line {idx}: product not found.")
        if not product.is_active:
            raise ValidationError(f"Line {idx}: product '{product.name}' is inactive.")

        result.append({"product": product, "quantity": qty})
    return result


# ------------------------------------------------------------
# Create Draft
# ------------------------------------------------------------
def create_order(payload: dict, user) -> SalesOrder:
    customer_id = payload.get("customer_id")
    if not customer_id:
        raise ValidationError("Customer is required.")
    customer = db.session.get(Customer, int(customer_id))
    if customer is None:
        raise ValidationError("Customer not found.")
    if not customer.is_active:
        raise ValidationError("Cannot order for an inactive customer.")

    items = _load_and_validate_items(payload.get("items") or [])

    discount = validate_discount(payload.get("discount_percentage", 0))[0]
    try:
        totals = compute_totals(
            [{"quantity": it["quantity"], "rate": it["product"].price} for it in items],
            discount,
        )
    except CalculationError as e:
        raise ValidationError(str(e))

    order = SalesOrder(
        order_number=generate_order_number(_next_order_sequence()),
        customer_id=customer.id,
        order_date=parse_date(payload.get("order_date", date.today().isoformat())),
        status="Draft",
        discount_percentage=discount,
        subtotal=totals["subtotal"],
        discount_amount=totals["discount_amount"],
        grand_total=totals["grand_total"],
        created_by=user.id,
    )
    db.session.add(order)
    db.session.flush()

    for line, item in zip(totals["lines"], items):
        db.session.add(SalesOrderItem(
            sales_order_id=order.id,
            product_id=item["product"].id,
            quantity=line["quantity"],
            rate=line["rate"],
            amount=line["amount"],
        ))
    db.session.commit()
    return order


# ------------------------------------------------------------
# Update Draft
# ------------------------------------------------------------
def update_order(order_id: int, payload: dict, user) -> SalesOrder:
    order = _get_order(order_id)
    if order.status != "Draft":
        raise OrderError("Only Draft orders can be edited.")

    if payload.get("items") is not None:
        items = _load_and_validate_items(payload["items"])
        discount = validate_discount(payload.get("discount_percentage", order.discount_percentage))[0]
        try:
            totals = compute_totals(
                [{"quantity": it["quantity"], "rate": it["product"].price} for it in items],
                discount,
            )
        except CalculationError as e:
            raise ValidationError(str(e))

        SalesOrderItem.query.filter_by(sales_order_id=order.id).delete()
        for line, item in zip(totals["lines"], items):
            db.session.add(SalesOrderItem(
                sales_order_id=order.id,
                product_id=item["product"].id,
                quantity=line["quantity"],
                rate=line["rate"],
                amount=line["amount"],
            ))
        order.discount_percentage = discount
        order.subtotal        = totals["subtotal"]
        order.discount_amount = totals["discount_amount"]
        order.grand_total     = totals["grand_total"]
    elif payload.get("discount_percentage") is not None:
        discount = validate_discount(payload["discount_percentage"])[0]
        totals = compute_totals(
            [{"quantity": it.quantity, "rate": it.rate} for it in order.items],
            discount,
        )
        order.discount_percentage = discount
        order.subtotal        = totals["subtotal"]
        order.discount_amount = totals["discount_amount"]
        order.grand_total     = totals["grand_total"]

    db.session.commit()
    return order


# ------------------------------------------------------------
# Confirm (transactional + row-locked)
# ------------------------------------------------------------
def confirm_order(order_id: int, user) -> SalesOrder:
    # Idempotency: if already Confirmed, return as-is (no double deduction)
    order = _get_order(order_id)
    if order.status == "Confirmed":
        return order
    if order.status != "Draft":
        raise OrderError(f"Cannot confirm a {order.status} order.")
    if not order.items:
        raise ValidationError("Cannot confirm an order with no items.")

    product_ids = sorted({it.product_id for it in order.items})

    try:
        # Row-lock all relevant products to serialize concurrent confirms
        locked = {
            p.id: p
            for p in db.session.query(Product)
                .filter(Product.id.in_(product_ids))
                .with_for_update()
                .all()
        }

        # Stock check for every line BEFORE any mutation
        for item in order.items:
            product = locked.get(item.product_id)
            if product is None:
                raise OrderError(f"Product id={item.product_id} no longer exists.")
            if product.stock_quantity < item.quantity:
                raise OrderError(
                    f"Insufficient stock for '{product.name}': "
                    f"need {item.quantity}, have {product.stock_quantity}."
                )

        # Apply deductions + movement records
        for item in order.items:
            product = locked[item.product_id]
            product.stock_quantity -= item.quantity
            db.session.add(StockMovement(
                product_id=product.id,
                movement_type="Order Confirm",
                quantity_change=-item.quantity,
                related_order_id=order.id,
                reason=f"Order {order.order_number} confirmed",
                created_by=user.id,
            ))

        order.status = "Confirmed"
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return order


# ------------------------------------------------------------
# Cancel
# ------------------------------------------------------------
def cancel_order(order_id: int, user) -> SalesOrder:
    order = _get_order(order_id)

    # Idempotency: cancelling an already-cancelled order is a no-op
    if order.status == "Cancelled":
        return order
    if order.status not in ("Draft", "Confirmed"):
        raise OrderError(f"Cannot cancel a {order.status} order.")

    was_confirmed = order.status == "Confirmed"

    try:
        if was_confirmed:
            product_ids = sorted({it.product_id for it in order.items})
            locked = {
                p.id: p
                for p in db.session.query(Product)
                    .filter(Product.id.in_(product_ids))
                    .with_for_update()
                    .all()
            }
            for item in order.items:
                product = locked[item.product_id]
                product.stock_quantity += item.quantity
                db.session.add(StockMovement(
                    product_id=product.id,
                    movement_type="Order Cancel",
                    quantity_change=+item.quantity,
                    related_order_id=order.id,
                    reason=f"Order {order.order_number} cancelled",
                    created_by=user.id,
                ))

        order.status = "Cancelled"
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return order