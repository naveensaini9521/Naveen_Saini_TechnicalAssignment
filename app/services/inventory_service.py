"""
Inventory service.

Part 6: Admin stock adjustments with mandatory reason + movement record.
"""

from app.extensions import db
from app.models import Product, StockMovement
from app.utils.validators import ValidationError, validate_int, validate_required


def adjust_stock(product_id: int, quantity_change, reason, user) -> dict:
    """
    Increase (+N) or decrease (-N) stock with mandatory reason.

    Rejects changes that would make stock negative.
    Always creates a StockMovement record.
    """
    qty, err = validate_int(quantity_change, "Quantity change")
    if err:
        raise ValidationError(err)
    if qty == 0:
        raise ValidationError("Quantity change must not be zero.")

    _, err = validate_required(reason, "Reason")
    if err:
        raise ValidationError(err)

    product = db.session.get(Product, int(product_id))
    if product is None:
        raise LookupError("Product not found.")

    # Lock the row to serialize concurrent adjustments
    product = db.session.query(Product).filter(Product.id == product.id).with_for_update().first()

    new_stock = product.stock_quantity + qty
    if new_stock < 0:
        raise ValidationError(
            f"Adjustment would make stock negative "
            f"(current={product.stock_quantity}, change={qty})."
        )

    product.stock_quantity = new_stock
    db.session.add(StockMovement(
        product_id=product.id,
        movement_type="Adjustment",
        quantity_change=qty,
        related_order_id=None,
        reason=reason.strip(),
        created_by=user.id,
    ))
    db.session.commit()
    return {
        "product_id": product.id,
        "new_stock": product.stock_quantity,
        "change": qty,
    }


def list_movements(product_id: int = None, page: int = 1, per_page: int = 20):
    from app.utils.helpers import paginate_query
    q = db.session.query(StockMovement).order_by(StockMovement.created_at.desc())
    if product_id:
        q = q.filter(StockMovement.product_id == int(product_id))
    return paginate_query(q, page=page, per_page=per_page)


def low_stock_products(threshold: int):
    t, err = validate_int(threshold, "Threshold", min_value=0)
    if err:
        raise ValidationError(err)
    return db.session.query(Product).filter(
        Product.stock_quantity < t,
        Product.is_active.is_(True),
    ).order_by(Product.stock_quantity.asc()).all()