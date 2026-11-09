"""
Permission tests (Part 2, Part 12).

Dedicated coverage of:
  - Sales User cannot access another user's order
  - Sales User cannot modify master data
  - Sales User cannot adjust stock
  - Sales User cannot view reports
  - Sales User cannot import CSV
  - Admin can do all of the above
  - Unauthenticated requests are rejected (401 for API, redirect for HTML)

Tested at TWO layers:
  1. Service/helper layer (can_access_order)
  2. HTTP layer (test_client with logged-in session)
"""

import pytest

from app.extensions import db
from app.models import Customer, Product
from app.services.order_service import create_order


def _mk_order(customer, product, user):
    return create_order({
        "customer_id": customer.id,
        "items": [{"product_id": product.id, "quantity": 1}],
    }, user)


# ============================================================
# Layer 1: Helper-level permission check
# ============================================================
class TestCanAccessOrderHelper:
    def test_owner_can_access_own_order(self, app, sample_customer, sample_product, sales_user):
        from app.utils.decorators import can_access_order
        order = _mk_order(sample_customer, sample_product, sales_user)
        assert can_access_order(order, sales_user) is True

    def test_other_sales_user_denied(self, app, sample_customer, sample_product,
                                      sales_user, other_sales_user):
        from app.utils.decorators import can_access_order
        order = _mk_order(sample_customer, sample_product, sales_user)
        assert can_access_order(order, other_sales_user) is False

    def test_admin_can_access_any_order(self, app, sample_customer, sample_product,
                                         sales_user, admin_user):
        from app.utils.decorators import can_access_order
        order = _mk_order(sample_customer, sample_product, sales_user)
        assert can_access_order(order, admin_user) is True

    def test_unauthenticated_denied(self, app, sample_customer, sample_product, sales_user):
        from app.utils.decorators import can_access_order
        from types import SimpleNamespace
        order = _mk_order(sample_customer, sample_product, sales_user)
        anon = SimpleNamespace(is_authenticated=False, role=None, id=None)
        assert can_access_order(order, anon) is False


# ============================================================
# Layer 2: HTTP-level — Sales User cross-order access
# ============================================================
class TestSalesUserCrossOrderHTTP:
    def test_other_sales_user_cannot_view_order_page(self, app, sample_customer,
                                                    sample_product, sales_user,
                                                    other_sales_client):
        order = _mk_order(sample_customer, sample_product, sales_user)
        order_number = order.order_number

        r = other_sales_client.get(f"/orders/{order.id}", follow_redirects=True)

        assert r.status_code == 200
        assert order_number.encode() not in r.data   # ← no data leak
        assert b"access" in r.data.lower()            # ← flash message renders
        
    def test_other_sales_user_api_get_order_403(self, app, sample_customer,
                                                 sample_product, sales_user,
                                                 other_sales_user):
        order = _mk_order(sample_customer, sample_product, sales_user)

        client = app.test_client()
        client.post("/login", data={
            "email": "sales2@test.com", "password": "salespass2",
        })
        r = client.get(f"/api/orders/{order.id}")
        assert r.status_code == 403
        assert r.is_json

    def test_other_sales_user_api_confirm_403(self, app, sample_customer,
                                               sample_product, sales_user,
                                               other_sales_user):
        order = _mk_order(sample_customer, sample_product, sales_user)

        client = app.test_client()
        client.post("/login", data={
            "email": "sales2@test.com", "password": "salespass2",
        })
        r = client.post(f"/api/orders/{order.id}/confirm")
        assert r.status_code == 403

    def test_other_sales_user_api_cancel_403(self, app, sample_customer,
                                              sample_product, sales_user,
                                              other_sales_user):
        order = _mk_order(sample_customer, sample_product, sales_user)

        client = app.test_client()
        client.post("/login", data={
            "email": "sales2@test.com", "password": "salespass2",
        })
        r = client.post(f"/api/orders/{order.id}/cancel")
        assert r.status_code == 403

    def test_owner_can_view_own_order(self, app, sample_customer, sample_product, sales_user):
        order = _mk_order(sample_customer, sample_product, sales_user)

        client = app.test_client()
        client.post("/login", data={
            "email": "sales@test.com", "password": "salespass",
        })
        r = client.get(f"/api/orders/{order.id}")
        assert r.status_code == 200

    def test_admin_can_view_any_order(self, app, sample_customer, sample_product,
                                      sales_user, admin_user):
        order = _mk_order(sample_customer, sample_product, sales_user)

        client = app.test_client()
        client.post("/login", data={
            "email": "admin@test.com", "password": "adminpass",
        })
        r = client.get(f"/api/orders/{order.id}")
        assert r.status_code == 200


# ============================================================
# Sales User cannot modify master data
# ============================================================
class TestSalesUserMasterDataBlocked:
    def test_cannot_create_customer_page(self, sales_client):
        r = sales_client.get("/customers/new")
        assert r.status_code == 403

    def test_cannot_edit_customer_page(self, sales_client, sample_customer):
        r = sales_client.get(f"/customers/{sample_customer.id}/edit")
        assert r.status_code == 403

    def test_cannot_delete_customer(self, sales_client, sample_customer):
        r = sales_client.post(f"/customers/{sample_customer.id}/delete")
        assert r.status_code == 403

    def test_cannot_create_product_page(self, sales_client):
        r = sales_client.get("/products/new")
        assert r.status_code == 403

    def test_cannot_edit_product_page(self, sales_client, sample_product):
        r = sales_client.get(f"/products/{sample_product.id}/edit")
        assert r.status_code == 403

    def test_cannot_delete_product(self, sales_client, sample_product):
        r = sales_client.post(f"/products/{sample_product.id}/delete")
        assert r.status_code == 403


# ============================================================
# Sales User cannot reach admin-only pages
# ============================================================
class TestSalesUserAdminPagesBlocked:
    @pytest.mark.parametrize("url", [
        "/inventory/",
        "/inventory/adjust",
        "/inventory/movements",
        "/reports/",
        "/reports/customer-sales",
        "/reports/product-sales",
        "/reports/low-stock",
        "/reports/stock-movements",
        "/imports/",
    ])
    def test_admin_only_routes_return_403(self, sales_client, url):
        r = sales_client.get(url)
        assert r.status_code == 403


# ============================================================
# Sales User CAN read master data (needed to create orders)
# ============================================================
class TestSalesUserReadAccess:
    def test_can_list_customers(self, sales_client):
        r = sales_client.get("/customers/")
        assert r.status_code == 200

    def test_can_list_products(self, sales_client):
        r = sales_client.get("/products/")
        assert r.status_code == 200

    def test_can_list_own_orders(self, sales_client):
        r = sales_client.get("/orders/")
        assert r.status_code == 200

    def test_can_create_order_page(self, sales_client):
        r = sales_client.get("/orders/new")
        assert r.status_code == 200

    def test_can_list_products_api(self, sales_client):
        r = sales_client.get("/api/products")
        assert r.status_code == 200
        assert r.is_json


# ============================================================
# Unauthenticated access
# ============================================================
class TestUnauthenticated:
    @pytest.mark.parametrize("url", [
        "/",
        "/customers/",
        "/products/",
        "/orders/",
        "/inventory/",
        "/reports/",
        "/imports/",
    ])
    def test_html_pages_redirect_to_login(self, client, url):
        r = client.get(url, follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    @pytest.mark.parametrize("method,url", [
        ("get",  "/api/products"),
        ("get",  "/api/orders/1"),
        ("post", "/api/orders"),
        ("post", "/api/orders/1/confirm"),
        ("post", "/api/orders/1/cancel"),
    ])
    def test_api_returns_401_json(self, client, method, url):
        r = getattr(client, method)(url)
        assert r.status_code == 401
        assert r.is_json
        assert "error" in r.get_json()


# ============================================================
# Admin CAN do everything
# ============================================================
class TestAdminAccess:
    def test_can_view_customers_page(self, admin_client):
        assert admin_client.get("/customers/").status_code == 200

    def test_can_access_create_customer(self, admin_client):
        assert admin_client.get("/customers/new").status_code == 200

    def test_can_access_inventory(self, admin_client):
        assert admin_client.get("/inventory/").status_code == 200

    def test_can_access_reports(self, admin_client):
        assert admin_client.get("/reports/").status_code == 200

    def test_can_access_imports(self, admin_client):
        assert admin_client.get("/imports/").status_code == 200

    def test_can_access_products_api(self, admin_client):
        r = admin_client.get("/api/products")
        assert r.status_code == 200