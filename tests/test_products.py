"""
Product service tests (Part 4).
"""

import pytest
from decimal import Decimal

from app.extensions import db
from app.models import Product, StockMovement
from app.services.product_service import (
    create_product, update_product, delete_product,
    list_products, get_product, list_categories,
)
from app.utils.validators import ValidationError


def _product(**kw):
    base = {"product_code": "PRD-T1", "name": "Test", "category": "Cat",
            "price": "100", "stock_quantity": "10", "status": "Active"}
    base.update(kw)
    return base


class TestCreate:
    def test_create_valid(self, app):
        p = create_product(_product())
        assert p.id is not None
        assert p.product_code == "PRD-T1"

    def test_code_uppercased(self, app):
        p = create_product(_product(product_code="prd-lower"))
        assert p.product_code == "PRD-LOWER"

    def test_duplicate_code_rejected(self, app):
        create_product(_product(product_code="PRD-DUP"))
        with pytest.raises(ValidationError, match="already exists"):
            create_product(_product(product_code="PRD-DUP"))

    def test_duplicate_code_case_insensitive(self, app):
        create_product(_product(product_code="PRD-CASE"))
        with pytest.raises(ValidationError, match="already exists"):
            create_product(_product(product_code="prd-case"))

    def test_negative_price_rejected(self, app):
        with pytest.raises(ValidationError, match="Price"):
            create_product(_product(price="-10"))

    def test_negative_stock_rejected(self, app):
        with pytest.raises(ValidationError, match="Stock"):
            create_product(_product(stock_quantity="-5"))

    def test_invalid_status_rejected(self, app):
        with pytest.raises(ValidationError, match="Status"):
            create_product(_product(status="Bogus"))

    def test_missing_name_rejected(self, app):
        with pytest.raises(ValidationError, match="Name"):
            create_product(_product(name=""))

    def test_bad_code_format_rejected(self, app):
        with pytest.raises(ValidationError, match="Product code"):
            create_product(_product(product_code="x"))   # too short


class TestUpdate:
    def test_update_price(self, app, sample_product):
        update_product(sample_product.id, {
            "product_code": sample_product.product_code,
            "name": sample_product.name,
            "category": sample_product.category,
            "price": "200",
        })
        assert sample_product.price == Decimal("200.00")

    def test_cannot_change_stock_via_update(self, app, sample_product):
        """Stock changes must go through inventory_service."""
        original_stock = sample_product.stock_quantity
        update_product(sample_product.id, {
            "product_code": sample_product.product_code,
            "name": sample_product.name,
            "category": sample_product.category,
            "price": "200",
            "stock_quantity": "999",   # should be ignored
        })
        assert sample_product.stock_quantity == original_stock


class TestSearch:
    def test_search_by_code(self, app, sample_products):
        page = list_products(search="PRD-A")
        assert len(page.items) == 1

    def test_search_by_name(self, app, sample_products):
        page = list_products(search="Keyboard")
        assert len(page.items) == 1

    def test_filter_by_category(self, app, sample_products):
        create_product(_product(product_code="PRD-C1", name="X", category="Other"))
        page = list_products(category="Acc")
        assert len(page.items) == 2

    def test_filter_by_active(self, app, sample_products):
        p = sample_products[0]
        update_product(p.id, {
            "product_code": p.product_code, "name": p.name,
            "category": p.category, "price": str(p.price), "status": "Inactive",
        })
        active = list_products(status="active")
        inactive = list_products(status="inactive")
        assert len(active.items) == 1
        assert len(inactive.items) == 1

    def test_list_categories(self, app, sample_products):
        cats = list_categories()
        assert "Acc" in cats


class TestSafeDelete:
    def test_delete_clean_product(self, app):
        p = create_product(_product())
        pid = p.id
        delete_product(pid)
        assert db.session.get(Product, pid) is None

    def test_delete_with_order_rejected(self, app, sample_customer, sample_product, sales_user):
        from app.services.order_service import create_order
        create_order(
            {"customer_id": sample_customer.id,
             "items": [{"product_id": sample_product.id, "quantity": 1}]},
            sales_user,
        )
        with pytest.raises(ValidationError, match="referenced"):
            delete_product(sample_product.id)

    def test_delete_with_movement_rejected(self, app, admin_user, sample_product):
        db.session.add(StockMovement(
            product_id=sample_product.id, movement_type="Adjustment",
            quantity_change=5, reason="test", created_by=admin_user.id,
        ))
        db.session.commit()
        with pytest.raises(ValidationError, match="stock movements"):
            delete_product(sample_product.id)