"""
Inventory routes (Part 6).

Admin-only: stock overview, adjustment, movement history.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Product, StockMovement
from app.services.inventory_service import adjust_stock, list_movements, low_stock_products
from app.utils.decorators import admin_required
from app.utils.validators import ValidationError


inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/")
@admin_required
def stock():
    products = db.session.query(Product).order_by(Product.name.asc()).all()
    return render_template("inventory/stock.html", products=products)


@inventory_bp.route("/adjust", methods=["GET", "POST"])
@admin_required
def adjust():
    products = db.session.query(Product).order_by(Product.name.asc()).all()
    if request.method == "POST":
        try:
            result = adjust_stock(
                product_id=request.form.get("product_id"),
                quantity_change=request.form.get("quantity_change"),
                reason=request.form.get("reason"),
                user=current_user,
            )
            flash(
                f"Stock adjusted. Product {result['product_id']} → {result['new_stock']}.",
                "success",
            )
            return redirect(url_for("inventory.stock"))
        except (ValidationError, LookupError) as e:
            flash(str(e), "error")

    return render_template("inventory/adjustment.html", products=products)


@inventory_bp.route("/movements")
@admin_required
def movements():
    product_id = request.args.get("product_id", type=int)
    page = int(request.args.get("page", 1))
    pagination = list_movements(product_id=product_id, page=page, per_page=25)

    products = db.session.query(Product).order_by(Product.name.asc()).all()
    return render_template(
        "inventory/movements.html",
        pagination=pagination,
        products=products,
        selected_product_id=product_id,
    )