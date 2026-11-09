"""
Report tests (Part 9).

Covers:
  - Customer Sales Summary: date range, zero-order customers, no double-count
  - Product Sales Summary: gross value before discount
  - Low Stock Report
  - The 5 standalone SQL queries
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from app.extensions import db
from app.models import SalesOrder, SalesOrderItem
from app.services.order_service import create_order, confirm_order, cancel_order
from app.services.report_service import (
    customer_sales_summary, product_sales_summary, low_stock_report,
    run_top_3_customers, run_top_3_products,
    run_customers_with_no_orders, run_monthly_sales,
    run_products_below_threshold,
)


def _mk_order(customer, items, user, discount=0, confirm=True):
    """Helper: create order, optionally confirm it."""
    order = create_order({
        "customer_id": customer.id,
        "discount_percentage": discount,
        "items": [{"product_id": p.id, "quantity": q} for p, q in items],
    }, user)
    if confirm:
        confirm_order(order.id, user)
    return order


class TestCustomerSalesSummary:
    def test_zero_order_customer_included(self, app, admin_user, sales_user, sample_customer, sample_product):
        from app.models import Customer
        c2 = Customer(name="Never Ordered", email="no@x.com")
        db.session.add(c2)
        db.session.commit()

        _mk_order(sample_customer, [(sample_product, 1)], sales_user)
        rows = customer_sales_summary()

        names = {r["customer_name"]: r for r in rows}
        assert "Never Ordered" in names
        assert names["Never Ordered"]["order_count"] == 0
        assert names["Never Ordered"]["total_sales"] == Decimal("0.00")
        assert names["Test Customer"]["order_count"] == 1

    def test_no_double_count_multi_item_order(self, app, admin_user, sales_user,
                                               sample_customer, sample_products):
        """An order with 2 items must count as 1 order, not 2."""
        _mk_order(sample_customer, [(sample_products[0], 1), (sample_products[1], 1)], sales_user)
        rows = customer_sales_summary()
        row = next(r for r in rows if r["customer_name"] == "Test Customer")
        assert row["order_count"] == 1

    def test_only_confirmed_counted(self, app, admin_user, sales_user,
                                     sample_customer, sample_product):
        _mk_order(sample_customer, [(sample_product, 1)], sales_user, confirm=False)  # Draft
        rows = customer_sales_summary()
        row = next(r for r in rows if r["customer_name"] == "Test Customer")
        assert row["order_count"] == 0

    def test_cancelled_not_counted(self, app, admin_user, sales_user,
                                    sample_customer, sample_product):
        order = _mk_order(sample_customer, [(sample_product, 1)], sales_user)
        cancel_order(order.id, sales_user)
        rows = customer_sales_summary()
        row = next(r for r in rows if r["customer_name"] == "Test Customer")
        assert row["order_count"] == 0

    def test_date_range_filter(self, app, admin_user, sales_user, sample_customer, sample_product):
        _mk_order(sample_customer, [(sample_product, 1)], sales_user)
        # Query with a date range that excludes today
        future_from = (date.today() + timedelta(days=1)).isoformat()
        rows = customer_sales_summary(date_from=future_from)
        row = next(r for r in rows if r["customer_name"] == "Test Customer")
        assert row["order_count"] == 0


class TestProductSalesSummary:
    def test_gross_value_before_discount(self, app, admin_user, sales_user,
                                          sample_customer, sample_product):
        """Part 9: product sales uses gross item value, NOT discounted total."""
        # 2 × 100 = 200, order discount 10% → grand total 180, but gross = 200
        _mk_order(sample_customer, [(sample_product, 2)], sales_user, discount=10)
        rows = product_sales_summary()
        row = next(r for r in rows if r["product_code"] == "PRD-TEST-1")
        assert row["qty_sold"] == 2
        assert row["gross_value"] == Decimal("200.00")


class TestLowStock:
    def test_threshold_filter(self, app, sample_products):
        sample_products[0].stock_quantity = 3
        db.session.commit()
        rows = low_stock_report(threshold=10)
        assert len(rows) == 1
        assert rows[0]["product_code"] == "PRD-A"


class TestSQLQueries:
    def test_top_3_customers(self, app, admin_user, sales_user,
                             sample_customer, sample_product):
        _mk_order(sample_customer, [(sample_product, 5)], sales_user)
        rows = run_top_3_customers()
        assert len(rows) >= 1
        assert rows[0]["name"] == "Test Customer"

    def test_top_3_products(self, app, admin_user, sales_user,
                            sample_customer, sample_product):
        _mk_order(sample_customer, [(sample_product, 5)], sales_user)
        rows = run_top_3_products()
        assert len(rows) >= 1
        assert rows[0]["product_code"] == "PRD-TEST-1"

    def test_customers_with_no_orders(self, app, admin_user, sales_user,
                                    sample_customer, sample_product):
        from app.models import Customer
        # Two customers exist now: "Test Customer" (no orders) and "Zero Customer" (no orders)
        # BOTH should appear in the "no orders" query.
        db.session.add(Customer(name="Zero Customer", email="zero@x.com"))
        db.session.commit()

        # Give Test Customer an order so it drops OUT of the no-orders list
        _mk_order(sample_customer, [(sample_product, 1)], sales_user)

        rows = run_customers_with_no_orders()
        names = [r["name"] for r in rows]
        assert "Zero Customer" in names
        assert "Test Customer" not in names
        
    def test_monthly_sales(self, app, admin_user, sales_user, sample_customer, sample_product):
        _mk_order(sample_customer, [(sample_product, 3)], sales_user)
        rows = run_monthly_sales()
        assert len(rows) >= 1
        assert rows[0]["year"] == date.today().year
        assert rows[0]["month"] == date.today().month

    def test_products_below_threshold(self, app, sample_products):
        sample_products[0].stock_quantity = 2
        db.session.commit()
        rows = run_products_below_threshold(threshold=10)
        assert len(rows) == 1
        assert rows[0]["product_code"] == "PRD-A"