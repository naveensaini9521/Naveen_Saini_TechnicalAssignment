"""
Report service.

Part 9: 4 UI reports + 5 standalone SQL queries.

UI reports use the ORM (to stay consistent with the rest of the app).
The 5 SQL queries live in sql/required_queries.sql and are also exposed
here as callables for tests / verification.
"""

from decimal import Decimal

from sqlalchemy import text, func, extract

from app.extensions import db
from app.models import (
    Customer, Product, SalesOrder, SalesOrderItem, StockMovement,
)
from app.utils.helpers import parse_date
from app.utils.validators import ValidationError


# ============================================================
# UI REPORT 1 — Customer Sales Summary
# ============================================================
def customer_sales_summary(date_from=None, date_to=None) -> list[dict]:
    """
    Customer, confirmed order count, total sales after discount.

    - Supports date range
    - Includes customers with ZERO confirmed orders (LEFT JOIN)
    - No double-count from multiple items (aggregates at ORDER level)
    """
    d_from = parse_date(date_from, "Date from") if date_from else None
    d_to   = parse_date(date_to,   "Date to")   if date_to   else None

    if d_from and d_to and d_from > d_to:
        raise ValidationError("Date from must be before Date to.")

    subq = db.session.query(
        SalesOrder.customer_id.label("cid"),
        func.count(SalesOrder.id).label("order_count"),
        func.coalesce(func.sum(SalesOrder.grand_total), 0).label("total_sales"),
    ).filter(SalesOrder.status == "Confirmed")

    if d_from:
        subq = subq.filter(SalesOrder.order_date >= d_from)
    if d_to:
        subq = subq.filter(SalesOrder.order_date <= d_to)

    subq = subq.group_by(SalesOrder.customer_id).subquery()

    rows = db.session.query(
        Customer.id, Customer.name,
        func.coalesce(subq.c.order_count, 0),
        func.coalesce(subq.c.total_sales, Decimal("0.00")),
    ).outerjoin(subq, subq.c.cid == Customer.id).order_by(Customer.name.asc()).all()

    return [
        {
            "customer_id": r[0],
            "customer_name": r[1],
            "order_count": int(r[2]),
            "total_sales": Decimal(str(r[3])),
        }
        for r in rows
    ]


# ============================================================
# UI REPORT 2 — Product Sales Summary
# ============================================================
def product_sales_summary(date_from=None, date_to=None) -> list[dict]:
    """
    Product, quantity sold, gross item value before order discount.

    Only Confirmed orders. Gross = SUM(quantity * rate) — NOT the
    discounted order total (Part 9 explicitly asks for "before order discount").
    """
    d_from = parse_date(date_from, "Date from") if date_from else None
    d_to   = parse_date(date_to,   "Date to")   if date_to   else None
    if d_from and d_to and d_from > d_to:
        raise ValidationError("Date from must be before Date to.")

    q = db.session.query(
        Product.id, Product.product_code, Product.name,
        func.coalesce(func.sum(SalesOrderItem.quantity), 0).label("qty_sold"),
        func.coalesce(func.sum(SalesOrderItem.amount), 0).label("gross_value"),
    ).join(SalesOrderItem, SalesOrderItem.product_id == Product.id
    ).join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id
    ).filter(SalesOrder.status == "Confirmed")

    if d_from: q = q.filter(SalesOrder.order_date >= d_from)
    if d_to:   q = q.filter(SalesOrder.order_date <= d_to)

    q = q.group_by(Product.id, Product.product_code, Product.name).order_by(Product.name.asc())

    return [
        {
            "product_id": r[0],
            "product_code": r[1],
            "product_name": r[2],
            "qty_sold": int(r[3]),
            "gross_value": Decimal(str(r[4])),
        }
        for r in q.all()
    ]


# ============================================================
# UI REPORT 3 — Low Stock Report
# ============================================================
def low_stock_report(threshold) -> list[dict]:
    if threshold is None or str(threshold).strip() == "":
        raise ValidationError("Threshold is required.")

    try:
        t = int(str(threshold).strip())
    except (TypeError, ValueError):
        raise ValidationError("Threshold must be a whole number.")
    if t < 0:
        raise ValidationError("Threshold must be ≥ 0.")

    rows = db.session.query(Product).filter(
        Product.stock_quantity < t,
        Product.is_active.is_(True),
    ).order_by(Product.stock_quantity.asc()).all()

    return [
        {
            "product_id": p.id,
            "product_code": p.product_code,
            "product_name": p.name,
            "stock_quantity": p.stock_quantity,
        }
        for p in rows
    ]


# ============================================================
# UI REPORT 4 — Stock Movement History
# ============================================================
def stock_movement_history(product_id=None, date_from=None, date_to=None) -> list[dict]:
    q = db.session.query(StockMovement).order_by(StockMovement.created_at.desc())

    if product_id not in (None, "", "None"):
        try:
            pid = int(str(product_id).strip())
        except (TypeError, ValueError):
            raise ValidationError("Product filter must be a numeric ID.")
        q = q.filter(StockMovement.product_id == pid)

    if date_from:
        q = q.filter(StockMovement.created_at >= parse_date(date_from))
    if date_to:
        q = q.filter(StockMovement.created_at <= parse_date(date_to))

    return [
        {
            "movement_id": m.id,
            "product_code": m.product.product_code if m.product else None,
            "product_name": m.product.name if m.product else None,
            "movement_type": m.movement_type,
            "quantity_change": m.quantity_change,
            "order_number": m.order.order_number if m.order else None,
            "reason": m.reason,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in q.all()
    ]


# ============================================================
# 5 STANDALONE SQL QUERIES (Part 9)
# ============================================================

SQL_TOP_3_CUSTOMERS = """
SELECT c.id, c.name,
       SUM(o.grand_total) AS total_confirmed_sales
FROM customers c
JOIN sales_orders o ON o.customer_id = c.id AND o.status = 'Confirmed'
GROUP BY c.id, c.name
ORDER BY total_confirmed_sales DESC
LIMIT 3;
"""

SQL_TOP_3_PRODUCTS = """
SELECT p.id, p.product_code, p.name,
       SUM(oi.quantity) AS total_qty_sold
FROM products p
JOIN sales_order_items oi ON oi.product_id = p.id
JOIN sales_orders o       ON o.id = oi.sales_order_id AND o.status = 'Confirmed'
GROUP BY p.id, p.product_code, p.name
ORDER BY total_qty_sold DESC
LIMIT 3;
"""

SQL_CUSTOMERS_WITH_NO_ORDERS = """
SELECT c.id, c.name, c.email, c.mobile
FROM customers c
LEFT JOIN sales_orders o ON o.customer_id = c.id
WHERE o.id IS NULL;
"""

SQL_MONTHLY_SALES = """
SELECT YEAR(o.order_date)  AS year,
       MONTH(o.order_date) AS month,
       SUM(o.grand_total)  AS total_sales,
       COUNT(*)            AS order_count
FROM sales_orders o
WHERE o.status = 'Confirmed'
GROUP BY YEAR(o.order_date), MONTH(o.order_date)
ORDER BY year DESC, month DESC;
"""

SQL_PRODUCTS_BELOW_THRESHOLD = """
SELECT id, product_code, name, stock_quantity
FROM products
WHERE stock_quantity < :threshold
  AND is_active = 1
ORDER BY stock_quantity ASC;
"""


def run_top_3_customers() -> list[dict]:
    return [dict(r._mapping) for r in db.session.execute(text(SQL_TOP_3_CUSTOMERS))]


def run_top_3_products() -> list[dict]:
    return [dict(r._mapping) for r in db.session.execute(text(SQL_TOP_3_PRODUCTS))]


def run_customers_with_no_orders() -> list[dict]:
    return [dict(r._mapping) for r in db.session.execute(text(SQL_CUSTOMERS_WITH_NO_ORDERS))]


def run_monthly_sales() -> list[dict]:
    """Portable: uses SQLAlchemy extract() so it works on MySQL and SQLite."""
    rows = (
        db.session.query(
            extract("year",  SalesOrder.order_date).label("year"),
            extract("month", SalesOrder.order_date).label("month"),
            func.sum(SalesOrder.grand_total).label("total_sales"),
            func.count(SalesOrder.id).label("order_count"),
        )
        .filter(SalesOrder.status == "Confirmed")
        .group_by("year", "month")
        .order_by(text("year DESC"), text("month DESC"))
        .all()
    )
    return [
        {
            "year":        int(r.year),
            "month":       int(r.month),
            "total_sales": r.total_sales,
            "order_count": r.order_count,
        }
        for r in rows
    ]


def run_products_below_threshold(threshold: int) -> list[dict]:
    return [dict(r._mapping)
            for r in db.session.execute(text(SQL_PRODUCTS_BELOW_THRESHOLD), {"threshold": threshold})]