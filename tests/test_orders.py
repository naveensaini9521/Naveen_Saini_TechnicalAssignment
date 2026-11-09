"""
Order service tests (Parts 5, 6, 12).

Covers:
  - Multi-item order with discount: correct totals
  - Confirm with sufficient stock: stock deducted, movement created
  - Confirm with insufficient stock: no changes
  - Repeated confirm: no extra deduction
  - Cancel of Draft: no stock change
  - Cancel of Confirmed: stock restored once
  - Sales User accessing another user's order: forbidden
  - Draft editing
  - Duplicate products rejected
"""

import pytest
from decimal import Decimal

from app.extensions import db
from app.models import SalesOrder, StockMovement, Product
from app.services.order_service import (
    create_order, update_order, confirm_order, cancel_order,
    OrderError,
)
from app.utils.validators import ValidationError


def _payload(customer, items, discount=0):
    return {
        "customer_id": customer.id,
        "discount_percentage": discount,
        "items": [{"product_id": p.id, "quantity": q} for p, q in items],
    }


class TestCreateOrder:
    def test_multi_item_with_discount(self, app, sample_customer, sample_products, sales_user):
        """Part 12: correct subtotal and grand total."""
        kb, mouse = sample_products
        order = create_order(
            _payload(sample_customer, [(kb, 2), (mouse, 3)], discount=10),
            sales_user,
        )
        assert order.subtotal        == Decimal("4500.00")
        assert order.discount_amount == Decimal("450.00")
        assert order.grand_total     == Decimal("4050.00")
        assert len(order.items) == 2

    def test_order_number_generated(self, app, sample_customer, sample_product, sales_user):
        order = create_order(
            _payload(sample_customer, [(sample_product, 1)]), sales_user,
        )
        assert order.order_number.startswith("SO-")

    def test_rate_frozen_at_creation(self, app, sample_customer, sample_product, sales_user):
        """Part 5: changing product price later must not change the order."""
        order = create_order(
            _payload(sample_customer, [(sample_product, 2)]), sales_user,
        )
        original_rate = order.items[0].rate

        # Change the product price AFTER the order was created
        sample_product.price = Decimal("999.00")
        db.session.commit()

        db.session.refresh(order)
        assert order.items[0].rate == original_rate

    def test_duplicate_product_rejected(self, app, sample_customer, sample_product, sales_user):
        with pytest.raises(ValidationError, match="Duplicate product"):
            create_order(
                _payload(sample_customer, [(sample_product, 1), (sample_product, 2)]),
                sales_user,
            )

    def test_empty_items_rejected(self, app, sample_customer, sales_user):
        with pytest.raises(ValidationError):
            create_order(
                {"customer_id": sample_customer.id, "items": []},
                sales_user,
            )

    def test_inactive_product_rejected(self, app, sample_customer, sample_product, sales_user):
        sample_product.is_active = False
        db.session.commit()
        with pytest.raises(ValidationError, match="inactive"):
            create_order(
                _payload(sample_customer, [(sample_product, 1)]), sales_user,
            )


class TestConfirm:
    def test_confirm_deducts_stock(self, app, sample_customer, sample_products, sales_user):
        """Part 12: confirmation with sufficient stock → confirmed + deducted."""
        kb, mouse = sample_products
        starting_kb = kb.stock_quantity
        starting_mouse = mouse.stock_quantity

        order = create_order(
            _payload(sample_customer, [(kb, 2), (mouse, 3)]), sales_user,
        )
        confirm_order(order.id, sales_user)

        db.session.refresh(kb)
        db.session.refresh(mouse)
        assert kb.stock_quantity    == starting_kb - 2
        assert mouse.stock_quantity == starting_mouse - 3
        assert order.status == "Confirmed"

    def test_confirm_creates_stock_movements(self, app, sample_customer, sample_product, sales_user):
        order = create_order(
            _payload(sample_customer, [(sample_product, 5)]), sales_user,
        )
        confirm_order(order.id, sales_user)

        movements = db.session.query(StockMovement).filter_by(
            movement_type="Order Confirm", related_order_id=order.id,
        ).all()
        assert len(movements) == 1
        assert movements[0].quantity_change == -5

    def test_insufficient_stock_rejects_entirely(self, app, sample_customer, sample_products, sales_user):
        """Part 12: one insufficient item → no stock/status changes at all."""
        kb, mouse = sample_products
        kb.stock_quantity = 1  # only 1 available
        db.session.commit()

        order = create_order(
            _payload(sample_customer, [(kb, 5), (mouse, 2)]), sales_user,
        )

        with pytest.raises(OrderError, match="Insufficient stock"):
            confirm_order(order.id, sales_user)

        # Neither product changed
        db.session.refresh(kb)
        db.session.refresh(mouse)
        assert kb.stock_quantity    == 1
        assert mouse.stock_quantity == 20
        assert order.status == "Draft"

    def test_repeated_confirm_is_idempotent(self, app, sample_customer, sample_product, sales_user):
        """Part 12: no additional deduction."""
        starting = sample_product.stock_quantity
        order = create_order(
            _payload(sample_customer, [(sample_product, 3)]), sales_user,
        )
        confirm_order(order.id, sales_user)
        db.session.refresh(sample_product)
        after_first = sample_product.stock_quantity
        assert after_first == starting - 3

        # Confirm again
        confirm_order(order.id, sales_user)
        db.session.refresh(sample_product)
        assert sample_product.stock_quantity == after_first  # unchanged


class TestCancel:
    def test_cancel_draft_no_stock_change(self, app, sample_customer, sample_product, sales_user):
        starting = sample_product.stock_quantity
        order = create_order(
            _payload(sample_customer, [(sample_product, 3)]), sales_user,
        )
        cancel_order(order.id, sales_user)
        db.session.refresh(sample_product)
        assert sample_product.stock_quantity == starting
        assert order.status == "Cancelled"

    def test_cancel_confirmed_restores_stock_once(self, app, sample_customer, sample_product, sales_user):
        """Part 12: cancellation of confirmed order → stock restored once."""
        starting = sample_product.stock_quantity
        order = create_order(
            _payload(sample_customer, [(sample_product, 3)]), sales_user,
        )
        confirm_order(order.id, sales_user)
        cancel_order(order.id, sales_user)

        db.session.refresh(sample_product)
        assert sample_product.stock_quantity == starting

    def test_repeated_cancel_idempotent(self, app, sample_customer, sample_product, sales_user):
        starting = sample_product.stock_quantity
        order = create_order(
            _payload(sample_customer, [(sample_product, 2)]), sales_user,
        )
        confirm_order(order.id, sales_user)
        cancel_order(order.id, sales_user)
        db.session.refresh(sample_product)
        after_first = sample_product.stock_quantity

        # Cancel again
        cancel_order(order.id, sales_user)
        db.session.refresh(sample_product)
        assert sample_product.stock_quantity == after_first


class TestDraftEditing:
    def test_edit_draft_changes_totals(self, app, sample_customer, sample_products, sales_user):
        kb, mouse = sample_products
        order = create_order(
            _payload(sample_customer, [(kb, 1)], discount=0), sales_user,
        )
        assert order.grand_total == Decimal("1500.00")

        update_order(order.id, {
            "items": [
                {"product_id": kb.id,    "quantity": 2},
                {"product_id": mouse.id, "quantity": 1},
            ],
            "discount_percentage": 10,
        }, sales_user)

        db.session.refresh(order)
        assert order.subtotal     == Decimal("3500.00")
        assert order.grand_total  == Decimal("3150.00")
        assert len(order.items) == 2

    def test_confirm_then_edit_rejected(self, app, sample_customer, sample_product, sales_user):
        order = create_order(
            _payload(sample_customer, [(sample_product, 1)]), sales_user,
        )
        confirm_order(order.id, sales_user)
        with pytest.raises(OrderError, match="Only Draft orders"):
            update_order(order.id, {"discount_percentage": 5}, sales_user)


class TestPermission:
    def test_sales_user_cannot_see_another_users_order(self, app, sample_customer, sample_product,
                                                        sales_user, other_sales_user):
        """Part 12: Sales User accessing another user's order → denied."""
        from app.utils.decorators import can_access_order
        order = create_order(
            _payload(sample_customer, [(sample_product, 1)]), sales_user,
        )
        assert can_access_order(order, sales_user) is True
        assert can_access_order(order, other_sales_user) is False

    def test_admin_can_see_any_order(self, app, sample_customer, sample_product,
                                      sales_user, admin_user):
        from app.utils.decorators import can_access_order
        order = create_order(
            _payload(sample_customer, [(sample_product, 1)]), sales_user,
        )
        assert can_access_order(order, admin_user) is True