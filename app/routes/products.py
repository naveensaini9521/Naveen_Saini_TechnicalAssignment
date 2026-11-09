"""
Product routes (Part 4).

Admin-only for create/edit/delete; both roles can browse.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
)
from flask_login import login_required

from app.services.product_service import (
    list_products, get_product, create_product, update_product,
    delete_product, list_categories,
)
from app.utils.decorators import admin_required
from app.utils.validators import ValidationError


products_bp = Blueprint("products", __name__)


@products_bp.route("/")
@login_required
def list_products_view():
    search = request.args.get("q", "")
    category = request.args.get("category", "")
    status = request.args.get("status", "all")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    pagination = list_products(
        search=search, category=category, status=status,
        page=page, per_page=per_page,
    )
    return render_template(
        "products/list.html",
        pagination=pagination,
        search=search,
        category=category,
        status=status,
        categories=list_categories(),
    )


@products_bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    if request.method == "POST":
        try:
            p = create_product(request.form)
            flash(f"Product '{p.name}' created.", "success")
            return redirect(url_for("products.list_products_view"))
        except ValidationError as e:
            flash(str(e), "error")
    return render_template("products/create.html")


@products_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(product_id):
    try:
        product = get_product(product_id)
    except LookupError:
        flash("Product not found.", "error")
        return redirect(url_for("products.list_products_view"))

    if request.method == "POST":
        try:
            update_product(product_id, request.form)
            flash("Product updated.", "success")
            return redirect(url_for("products.list_products_view"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("products/edit.html", product=product)


@products_bp.route("/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete(product_id):
    try:
        delete_product(product_id)
        flash("Product deleted.", "success")
    except (ValidationError, LookupError) as e:
        flash(str(e), "error")
    return redirect(url_for("products.list_products_view"))