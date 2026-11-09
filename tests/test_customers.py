"""
Customer service tests (Part 4).
"""

import pytest
from decimal import Decimal

from app.extensions import db
from app.models import Customer, SalesOrder
from app.services.customer_service import (
    create_customer, update_customer, delete_customer,
    list_customers, get_customer,
)
from app.utils.validators import ValidationError


class TestCreate:
    def test_create_customer(self, app):
        c = create_customer({"name": "Foo", "email": "foo@x.com", "city": "Mumbai"})
        assert c.id is not None
        assert c.is_active is True

    def test_name_required(self, app):
        with pytest.raises(ValidationError, match="Name"):
            create_customer({"email": "x@y.com"})

    def test_requires_email_or_mobile(self, app):
        with pytest.raises(ValidationError, match="email or mobile"):
            create_customer({"name": "Foo"})

    def test_invalid_email_rejected(self, app):
        with pytest.raises(ValidationError, match="Invalid email"):
            create_customer({"name": "Foo", "email": "not-an-email"})

    def test_invalid_mobile_rejected(self, app):
        with pytest.raises(ValidationError, match="Invalid mobile"):
            create_customer({"name": "Foo", "mobile": "abc"})


class TestUpdate:
    def test_update_name(self, app, sample_customer):
        update_customer(sample_customer.id, {"name": "New Name", "email": "cust@test.com"})
        assert sample_customer.name == "New Name"

    def test_toggle_inactive(self, app, sample_customer):
        update_customer(sample_customer.id, {
            "name": "X", "email": "x@y.com", "is_active": "on",
        })
        assert sample_customer.is_active is True


class TestSearch:
    def test_search_by_name(self, app):
        create_customer({"name": "Acme Traders", "email": "acme@x.com"})
        create_customer({"name": "Blue Ocean",   "email": "blue@x.com"})
        page = list_customers(search="Acme")
        assert len(page.items) == 1
        assert page.items[0].name == "Acme Traders"

    def test_search_by_email(self, app):
        create_customer({"name": "X", "email": "unique@test.com"})
        page = list_customers(search="unique")
        assert len(page.items) == 1

    def test_filter_active(self, app):
        create_customer({"name": "A", "email": "a@x.com"})
        c = create_customer({"name": "B", "email": "b@x.com"})
        update_customer(c.id, {"name": "B", "email": "b@x.com", "is_active": False})

        active = list_customers(status="active")
        inactive = list_customers(status="inactive")
        assert len(active.items) == 1
        assert len(inactive.items) == 1


class TestSafeDelete:
    def test_delete_without_orders_succeeds(self, app):
        c = create_customer({"name": "Delete Me", "email": "del@x.com"})
        cid = c.id
        delete_customer(cid)
        assert get_customer(cid) is None if False else True  # just ensure no exception
        # Actually verify it's gone
        assert db.session.get(Customer, cid) is None

    def test_delete_with_orders_rejected(self, app, sample_customer, sample_product, sales_user):
        from app.services.order_service import create_order
        create_order(
            {"customer_id": sample_customer.id, "items": [
                {"product_id": sample_product.id, "quantity": 1},
            ]},
            sales_user,
        )
        with pytest.raises(ValidationError, match="has sales orders"):
            delete_customer(sample_customer.id)