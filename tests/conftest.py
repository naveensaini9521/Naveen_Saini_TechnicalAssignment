"""
Pytest fixtures.
"""

import pytest

from app import create_app
from app.extensions import db
from app.models import User, Customer, Product
from config import TestConfig


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    return db.session


@pytest.fixture
def admin_user(app):
    user = User(name="Admin", email="admin@test.com", role="Admin")
    user.set_password("adminpass")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sales_user(app):
    user = User(name="Sales", email="sales@test.com", role="Sales User")
    user.set_password("salespass")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def other_sales_user(app):
    user = User(name="Other Sales", email="sales2@test.com", role="Sales User")
    user.set_password("salespass2")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_client(app, admin_user):
    c = app.test_client()
    c.post("/login", data={"email": "admin@test.com", "password": "adminpass"})
    return c


@pytest.fixture
def sales_client(app, sales_user):
    c = app.test_client()
    c.post("/login", data={"email": "sales@test.com", "password": "salespass"})
    return c


# ADD THIS NEW FIXTURE HERE:
@pytest.fixture
def other_sales_client(app, other_sales_user):
    c = app.test_client()
    c.post("/login", data={"email": "sales2@test.com", "password": "salespass2"})
    return c


@pytest.fixture
def sample_customer(app):
    c = Customer(name="Test Customer", email="cust@test.com",
                 mobile="9876543210", city="Mumbai", is_active=True)
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture
def sample_product(app):
    p = Product(product_code="PRD-TEST-1", name="Test Product",
                category="Test", price=100, stock_quantity=50, is_active=True)
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def sample_products(app):
    items = [
        Product(product_code="PRD-A", name="Keyboard", category="Acc",
                price=1500, stock_quantity=10, is_active=True),
        Product(product_code="PRD-B", name="Mouse",    category="Acc",
                price=500,  stock_quantity=20, is_active=True),
    ]
    for p in items:
        db.session.add(p)
    db.session.commit()
    return items