"""
Seed the database with sample data.

Run from the project root:
    python scripts/seed.py

Idempotent: clears existing rows before inserting.
"""

import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (
    User, Customer, Product,
    SalesOrder, SalesOrderItem, StockMovement,
)


USERS = [
    {"name": "Admin User",  "email": "admin@gmail.com", "password": "Admin@123", "role": "Admin"},
    {"name": "Sales User",  "email": "sales@gmail.com", "password": "Sales@123", "role": "Sales User"},
]

CUSTOMERS = [
    {"name": "Acme Traders",         "email": "acme@gmail.com",      "mobile": "9876543210", "city": "Mumbai",  "is_active": True},
    {"name": "Blue Ocean Supplies",  "email": "blueocean@gmail.com", "mobile": "9123456780", "city": "Pune",    "is_active": True},
    {"name": "Closed Mart",          "email": "closed@gmail.com",    "mobile": "9000000001", "city": "Nagpur",  "is_active": False},
]

PRODUCTS = [
    {"product_code": "PRD-001", "name": "Keyboard",     "category": "Accessories", "price": Decimal("1500.00"),  "stock_quantity": 20, "is_active": True},
    {"product_code": "PRD-002", "name": "Mouse",        "category": "Accessories", "price": Decimal("500.00"),   "stock_quantity": 50, "is_active": True},
    {"product_code": "PRD-003", "name": "Monitor 24\"", "category": "Displays",    "price": Decimal("12000.00"), "stock_quantity": 10, "is_active": True},
    {"product_code": "PRD-004", "name": "USB Hub",      "category": "Accessories", "price": Decimal("800.00"),   "stock_quantity": 30, "is_active": True},
    {"product_code": "PRD-005", "name": "Webcam HD",    "category": "Cameras",     "price": Decimal("2200.00"),  "stock_quantity": 15, "is_active": True},
    {"product_code": "PRD-006", "name": "Desk Lamp",    "category": "Furniture",   "price": Decimal("750.00"),   "stock_quantity": 0,  "is_active": False},
]


def seed():
    app = create_app()
    with app.app_context():
        print("Clearing existing data...")
        StockMovement.query.delete()
        SalesOrderItem.query.delete()
        SalesOrder.query.delete()
        Product.query.delete()
        Customer.query.delete()
        User.query.delete()
        db.session.commit()

        # ---- Users ----
        print("Inserting users...")
        users = []
        for u in USERS:
            user = User(
                name=u["name"],
                email=u["email"],
                password_hash=generate_password_hash(u["password"]),
                role=u["role"],
            )
            db.session.add(user)
            users.append(user)
        db.session.flush()
        admin = next(u for u in users if u.role == "Admin")

        # ---- Customers ----
        print("Inserting customers...")
        customers = []
        for c in CUSTOMERS:
            cust = Customer(**c)
            db.session.add(cust)
            customers.append(cust)
        db.session.flush()

        # ---- Products ----
        print("Inserting products...")
        products = []
        for p in PRODUCTS:
            prod = Product(**p)
            db.session.add(prod)
            products.append(prod)
        db.session.flush()

        # ---- Opening stock movements ----
        print("Inserting opening stock movements...")
        for prod in products:
            if prod.stock_quantity > 0:
                db.session.add(StockMovement(
                    product_id=prod.id,
                    movement_type="Opening",
                    quantity_change=prod.stock_quantity,
                    related_order_id=None,
                    reason="Initial stock",
                    created_by=admin.id,
                ))

        db.session.commit()

        print("\n Seed complete.")
        print("Sample accounts (passwords case-sensitive):")
        for u in USERS:
            print(f"  {u['role']:<12} | {u['email']:<22} | {u['password']}")
        print(f"\nCustomers: {Customer.query.count()}")
        print(f"Products:  {Product.query.count()}")
        print(f"Movements: {StockMovement.query.count()}")


if __name__ == "__main__":
    seed()