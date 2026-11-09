"""
CSV import tests (Part 10 / Part 12).
"""

import pytest

from app.extensions import db
from app.models import Product, StockMovement
from app.services.csv_import_service import import_products
from app.utils.validators import ValidationError


VALID_CSV = """product_code,product_name,category,price,stock_quantity,status
CSV-001,Widget A,Test,100.00,10,Active
CSV-002,Widget B,Test,200.00,20,Active
"""

INVALID_DUP_IN_FILE = """product_code,product_name,category,price,stock_quantity,status
CSV-DUP,Widget A,Test,100.00,10,Active
CSV-DUP,Widget B,Test,200.00,20,Active
"""

INVALID_NEGATIVE_PRICE = """product_code,product_name,category,price,stock_quantity,status
CSV-NEG,Widget A,Test,-100.00,10,Active
"""

INVALID_BAD_STATUS = """product_code,product_name,category,price,stock_quantity,status
CSV-STAT,Widget A,Test,100.00,10,Bogus
"""

INVALID_NOT_A_NUMBER = """product_code,product_name,category,price,stock_quantity,status
CSV-NAN,Widget A,Test,abc,10,Active
"""

MISSING_COLUMN = """product_code,product_name,price,stock_quantity,status
CSV-MISS,Widget A,100.00,10,Active
"""


class TestHappyPath:
    def test_valid_file_imports_all(self, app, admin_user):
        result = import_products(VALID_CSV, admin_user)
        assert result["imported"] == 2
        assert db.session.query(Product).filter(Product.product_code.like("CSV-%")).count() == 2

    def test_opening_stock_movements_created(self, app, admin_user):
        import_products(VALID_CSV, admin_user)
        movements = db.session.query(StockMovement).filter_by(
            movement_type="Opening",
        ).all()
        # Two opening movements for the two imported products
        opening_for_csv = [m for m in movements if m.reason == "CSV import opening stock"]
        assert len(opening_for_csv) == 2


class TestRejectAll:
    def test_duplicate_in_file_rejects_everything(self, app, admin_user):
        with pytest.raises(ValidationError, match="duplicated within the file"):
            import_products(INVALID_DUP_IN_FILE, admin_user)
        assert db.session.query(Product).count() == 0

    def test_negative_price_rejects_everything(self, app, admin_user):
        with pytest.raises(ValidationError, match="Price"):
            import_products(INVALID_NEGATIVE_PRICE, admin_user)
        assert db.session.query(Product).count() == 0

    def test_invalid_status_rejects_everything(self, app, admin_user):
        with pytest.raises(ValidationError, match="Status"):
            import_products(INVALID_BAD_STATUS, admin_user)
        assert db.session.query(Product).count() == 0

    def test_non_numeric_price_rejects_everything(self, app, admin_user):
        with pytest.raises(ValidationError, match="number"):
            import_products(INVALID_NOT_A_NUMBER, admin_user)
        assert db.session.query(Product).count() == 0

    def test_missing_column_rejects(self, app, admin_user):
        with pytest.raises(ValidationError, match="Missing required column"):
            import_products(MISSING_COLUMN, admin_user)
        assert db.session.query(Product).count() == 0

    def test_valid_row_plus_invalid_row_imports_nothing(self, app, admin_user):
        """Part 12: CSV containing an invalid row → NO products imported."""
        csv_with_mixed = """product_code,product_name,category,price,stock_quantity,status
CSV-GOOD,Good Product,Test,100.00,10,Active
CSV-BAD,Bad Product,Test,-50.00,10,Active
"""
        with pytest.raises(ValidationError):
            import_products(csv_with_mixed, admin_user)
        assert db.session.query(Product).count() == 0

    def test_duplicate_with_db_rejects(self, app, admin_user):
        # First import
        import_products(VALID_CSV, admin_user)
        assert db.session.query(Product).count() == 2
        # Second import of the same file
        with pytest.raises(ValidationError, match="already exists in the database"):
            import_products(VALID_CSV, admin_user)
        # Still only 2 products
        assert db.session.query(Product).count() == 2