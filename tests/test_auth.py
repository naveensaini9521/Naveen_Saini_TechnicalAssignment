"""
Auth tests (Part 2).
"""

import pytest

from app.extensions import db
from app.models import User
from app.services.auth_service import authenticate, AuthError


class TestLoginService:
    def test_valid_admin_credentials(self, app, admin_user):
        user = authenticate("admin@test.com", "adminpass")
        assert user.id == admin_user.id
        assert user.role == "Admin"

    def test_valid_sales_credentials(self, app, sales_user):
        user = authenticate("sales@test.com", "salespass")
        assert user.role == "Sales User"

    def test_wrong_password_rejected(self, app, admin_user):
        with pytest.raises(AuthError, match="Invalid email or password"):
            authenticate("admin@test.com", "wrong")

    def test_unknown_email_rejected(self, app):
        with pytest.raises(AuthError, match="Invalid email or password"):
            authenticate("nobody@test.com", "anything")

    def test_same_error_for_unknown_and_wrong_password(self, app, admin_user):
        """Prevent username enumeration."""
        try:
            authenticate("nobody@test.com", "x")
        except AuthError as e1:
            msg1 = str(e1)
        try:
            authenticate("admin@test.com", "wrong")
        except AuthError as e2:
            msg2 = str(e2)
        assert msg1 == msg2

    def test_case_insensitive_email(self, app, admin_user):
        user = authenticate("ADMIN@TEST.COM", "adminpass")
        assert user.id == admin_user.id

    def test_empty_inputs_rejected(self, app):
        with pytest.raises(AuthError):
            authenticate("", "")
        with pytest.raises(AuthError):
            authenticate("admin@test.com", "")


class TestLoginRoute:
    def test_login_page_renders(self, client):
        r = client.get("/login")
        assert r.status_code == 200

    def test_login_success_redirects(self, client, admin_user):
        r = client.post("/login", data={
            "email": "admin@test.com", "password": "adminpass",
        }, follow_redirects=False)
        assert r.status_code == 302

    def test_login_failure_shows_error(self, client, admin_user):
        r = client.post("/login", data={
            "email": "admin@test.com", "password": "wrong",
        })
        assert r.status_code == 401
        assert b"Invalid email or password" in r.data

    def test_logout_clears_session(self, admin_client):
        r = admin_client.get("/logout", follow_redirects=True)
        assert r.status_code == 200
        assert b"Login" in r.data


class TestProtectedRoutes:
    def test_dashboard_requires_login(self, client):
        r = client.get("/", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_customers_requires_login(self, client):
        r = client.get("/customers/", follow_redirects=False)
        assert r.status_code == 302

    def test_api_returns_401_not_redirect(self, client):
        """Part 8: API must return JSON 401, not redirect."""
        r = client.get("/api/products")
        assert r.status_code == 401
        assert r.is_json

    def test_sales_user_cannot_access_inventory(self, sales_client):
        r = sales_client.get("/inventory/", follow_redirects=False)
        assert r.status_code == 403

    def test_sales_user_cannot_access_reports(self, sales_client):
        r = sales_client.get("/reports/", follow_redirects=False)
        assert r.status_code == 403