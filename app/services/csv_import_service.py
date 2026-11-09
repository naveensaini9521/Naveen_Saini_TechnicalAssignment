"""
CSV product import.

Part 10: Admin-only, all-or-nothing, row-level errors, opening stock
recorded as stock movements.
"""

import csv
import io
from decimal import Decimal

from app.extensions import db
from app.models import Product, StockMovement
from app.utils.validators import (
    ValidationError,
    validate_product_code, validate_required, validate_decimal,
    validate_int, validate_status,
)


REQUIRED_COLUMNS = ["product_code", "product_name", "category",
                    "price", "stock_quantity", "status"]


def import_products(csv_text: str, user) -> dict:
    """
    Parse and validate the whole file. If ANY row is invalid, import NOTHING.
    On success: insert all products + one 'Opening' StockMovement per product.

    Returns: {"imported": N}
    Raises ValidationError with row-numbered reasons on any failure.
    """
    reader = csv.DictReader(io.StringIO(csv_text))

    # 1. Validate header
    if not reader.fieldnames:
        raise ValidationError("CSV file is empty or has no header.")

    missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise ValidationError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Expected: {','.join(REQUIRED_COLUMNS)}"
        )

    rows = list(reader)
    if not rows:
        raise ValidationError("CSV file has no data rows.")

    # 2. Validate every row, collect ALL errors
    errors = []
    cleaned_rows = []
    seen_codes = set()

    # Pre-load existing codes (so duplicates in DB fail cleanly)
    existing_codes = {
        r[0] for r in db.session.query(Product.product_code).all()
    }

    for i, row in enumerate(rows, start=2):  # row 1 = header
        row_errors = []

        code, err = validate_product_code(row.get("product_code", ""))
        if err:
            row_errors.append(err)
        else:
            if code in seen_codes:
                row_errors.append(f"Product code '{code}' is duplicated within the file.")
            elif code in existing_codes:
                row_errors.append(f"Product code '{code}' already exists in the database.")
            seen_codes.add(code)

        name, err = validate_required(row.get("product_name", ""), "Product name")
        if err:
            row_errors.append(err)

        category, err = validate_required(row.get("category", ""), "Category")
        if err:
            row_errors.append(err)

        price, err = validate_decimal(row.get("price", ""), "Price", min_value=0)
        if err:
            row_errors.append(err)

        stock, err = validate_int(row.get("stock_quantity", ""), "Stock", min_value=0)
        if err:
            row_errors.append(err)

        is_active, err = validate_status(row.get("status", ""))
        if err:
            row_errors.append(err)

        if row_errors:
            errors.append(f"Row {i}: " + "; ".join(row_errors))
        else:
            cleaned_rows.append({
                "product_code": code,
                "name": name,
                "category": category,
                "price": price,
                "stock_quantity": stock,
                "is_active": is_active,
            })

    if errors:
        raise ValidationError("Import rejected. " + " | ".join(errors))

    # 3. All-or-nothing insert
    try:
        imported = 0
        for r in cleaned_rows:
            p = Product(
                product_code=r["product_code"],
                name=r["name"],
                category=r["category"],
                price=r["price"],
                stock_quantity=r["stock_quantity"],
                is_active=r["is_active"],
            )
            db.session.add(p)
            db.session.flush()   # need id for movement

            if r["stock_quantity"] > 0:
                db.session.add(StockMovement(
                    product_id=p.id,
                    movement_type="Opening",
                    quantity_change=r["stock_quantity"],
                    related_order_id=None,
                    reason="CSV import opening stock",
                    created_by=user.id,
                ))
            imported += 1

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {"imported": imported}