"""
Product service.

Part 4 requirements:
  - Create, view, edit products
  - Delete only when no order OR stock movement references them
  - Search by product code or name
  - Filter by category and active/inactive
  - Validate unique product codes
  - Prevent negative prices and stock quantities
"""

from sqlalchemy import or_

from app.extensions import db
from app.models import Product, SalesOrderItem, StockMovement
from app.utils.helpers import paginate_query
from app.utils.validators import (
    ValidationError, collect_errors,
    validate_required, validate_length, validate_int, validate_decimal,
    validate_product_code, validate_status,
)


# ------------------------------------------------------------
# Read
# ------------------------------------------------------------
def list_products(search: str = "", category: str = "", status: str = "all",
                  page: int = 1, per_page: int = 20):
    """
    Paginated product list.

    search:   matches product_code OR name (case-insensitive)
    category: exact match (case-insensitive)
    status:   "all" | "active" | "inactive"
    """
    q = db.session.query(Product)

    if search and search.strip():
        s = f"%{search.strip()}%"
        q = q.filter(or_(Product.product_code.ilike(s), Product.name.ilike(s)))

    if category and category.strip():
        q = q.filter(Product.category.ilike(category.strip()))

    status_norm = (status or "all").strip().lower()
    if status_norm == "active":
        q = q.filter(Product.is_active.is_(True))
    elif status_norm == "inactive":
        q = q.filter(Product.is_active.is_(False))

    q = q.order_by(Product.name.asc())
    return paginate_query(q, page=page, per_page=per_page)


def get_product(product_id: int) -> Product:
    p = db.session.get(Product, int(product_id))
    if p is None:
        raise LookupError("Product not found.")
    return p


def list_categories() -> list[str]:
    """Distinct categories for the filter dropdown."""
    rows = db.session.query(Product.category).distinct().order_by(Product.category).all()
    return [r[0] for r in rows]


def active_products_for_select():
    """For the order-creation dropdown — only active products."""
    return db.session.query(Product).filter(
        Product.is_active.is_(True)
    ).order_by(Product.name.asc()).all()


# ------------------------------------------------------------
# Write — Create
# ------------------------------------------------------------
def create_product(form_data: dict) -> Product:
    """
    Create a product.

    - Unique product_code (checked here AND by DB UNIQUE constraint)
    - price >= 0
    - stock_quantity >= 0
    - status = Active/Inactive (defaults to Active)
    """
    checks = {
        "code":     validate_product_code(form_data.get("product_code")),
        "name":     validate_required(form_data.get("name"), "Name"),
        "category": validate_required(form_data.get("category"), "Category"),
        "price":    validate_decimal(form_data.get("price"), "Price", min_value=0),
        "stock":    validate_int(form_data.get("stock_quantity", 0), "Stock", min_value=0),
        "status":   validate_status(form_data.get("status")),
    }
    errors = collect_errors(checks)
    if errors:
        raise ValidationError(" ".join(errors))

    code     = checks["code"][0]
    name     = checks["name"][0]
    category = checks["category"][0]
    price    = checks["price"][0]
    stock    = checks["stock"][0]
    is_active = checks["status"][0]

    # Explicit unique check for a friendlier message than the DB error
    existing = db.session.query(Product).filter(Product.product_code == code).first()
    if existing:
        raise ValidationError(f"Product code '{code}' already exists.")

    product = Product(
        product_code=code,
        name=name,
        category=category,
        price=price,
        stock_quantity=stock,
        is_active=is_active,
    )
    db.session.add(product)
    db.session.commit()
    return product


# ------------------------------------------------------------
# Write — Update
# ------------------------------------------------------------
def update_product(product_id: int, form_data: dict) -> Product:
    """
    Edit a product.

    NOTE: stock_quantity is deliberately NOT editable here —
    stock changes must go through inventory_service.adjust_stock()
    (Part 6), which records a StockMovement.
    """
    product = get_product(product_id)

    # Current values as fallback for partial updates
    checks = {
        "code":     validate_product_code(form_data.get("product_code", product.product_code)),
        "name":     validate_required(form_data.get("name", product.name), "Name"),
        "category": validate_required(form_data.get("category", product.category), "Category"),
        "price":    validate_decimal(form_data.get("price", product.price), "Price", min_value=0),
        "status":   validate_status(form_data.get("status", "Active" if product.is_active else "Inactive")),
    }
    errors = collect_errors(checks)
    if errors:
        raise ValidationError(" ".join(errors))

    code = checks["code"][0]

    # Unique check (excluding self)
    duplicate = db.session.query(Product).filter(
        Product.product_code == code, Product.id != product.id
    ).first()
    if duplicate:
        raise ValidationError(f"Product code '{code}' already used by another product.")

    product.product_code = code
    product.name         = checks["name"][0]
    product.category     = checks["category"][0]
    product.price        = checks["price"][0]
    product.is_active    = checks["status"][0]

    db.session.commit()
    return product


# ------------------------------------------------------------
# Write — Delete (safe)
# ------------------------------------------------------------
def delete_product(product_id: int) -> None:
    """
    Delete ONLY if no order items and no stock movements reference it.

    Otherwise raise ValidationError → user should deactivate instead.
    """
    product = get_product(product_id)

    has_order_item = db.session.query(
        SalesOrderItem.query.filter(SalesOrderItem.product_id == product.id).exists()
    ).scalar()

    has_movement = db.session.query(
        StockMovement.query.filter(StockMovement.product_id == product.id).exists()
    ).scalar()

    if has_order_item or has_movement:
        reasons = []
        if has_order_item: reasons.append("sales orders")
        if has_movement:   reasons.append("stock movements")
        raise ValidationError(
            f"Cannot delete this product: it is referenced by {' and '.join(reasons)}. "
            "Deactivate it instead."
        )

    db.session.delete(product)
    db.session.commit()