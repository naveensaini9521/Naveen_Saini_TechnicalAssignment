"""
Inventory adjustment tests (Part 6).
"""

import pytest
from decimal import Decimal

from app.extensions import db
from app.models import StockMovement
from app.services.inventory_service import (
    adjust_stock, list_movements, low_stock_products,
)
from app.utils.validators import ValidationError


class TestAdjustStock:
    def test_increase_creates_movement(self, app, sample_product, admin_user):
        starting = sample_product.stock_quantity
        result = adjust_stock(sample_product.id, "10", "Restock", admin_user)

        db.session.refresh(sample_product)
        assert sample_product.stock_quantity == starting + 10
        assert result["new_stock"] == starting + 10

        movement = db.session.query(StockMovement).filter_by(
            product_id=sample_product.id, movement_type="Adjustment",
        ).order_by(StockMovement.id.desc()).first()
        assert movement.quantity_change == 10
        assert movement.reason == "Restock"
        assert movement.created_by == admin_user.id

    def test_decrease(self, app, sample_product, admin_user):
        starting = sample_product.stock_quantity
        adjust_stock(sample_product.id, "-5", "Damaged", admin_user)
        db.session.refresh(sample_product)
        assert sample_product.stock_quantity == starting - 5

    def test_negative_stock_rejected(self, app, sample_product, admin_user):
        with pytest.raises(ValidationError, match="negative"):
            adjust_stock(sample_product.id, "-1000", "Too much", admin_user)

    def test_zero_change_rejected(self, app, sample_product, admin_user):
        with pytest.raises(ValidationError, match="must not be zero"):
            adjust_stock(sample_product.id, "0", "Nothing", admin_user)

    def test_reason_required(self, app, sample_product, admin_user):
        with pytest.raises(ValidationError, match="Reason"):
            adjust_stock(sample_product.id, "5", "", admin_user)

    def test_nonexistent_product(self, app, admin_user):
        with pytest.raises(LookupError):
            adjust_stock(99999, "5", "X", admin_user)


class TestMovements:
    def test_movement_created_per_adjustment(self, app, sample_product, admin_user):
        adjust_stock(sample_product.id, "10", "First", admin_user)
        adjust_stock(sample_product.id, "-3", "Second", admin_user)
        page = list_movements(product_id=sample_product.id)
        assert len(page.items) == 2


class TestLowStock:
    def test_finds_products_below_threshold(self, app, sample_products):
        sample_products[0].stock_quantity = 3
        sample_products[1].stock_quantity = 25
        db.session.commit()

        low = low_stock_products(threshold=10)
        assert len(low) == 1
        assert low[0].product_code == "PRD-A"

    def test_inactive_excluded(self, app, sample_products):
        p = sample_products[0]
        p.stock_quantity = 1
        p.is_active = False
        db.session.commit()
        low = low_stock_products(threshold=10)
        assert len(low) == 0

    def test_invalid_threshold_rejected(self, app):
        with pytest.raises(ValidationError):
            low_stock_products(threshold=-1)