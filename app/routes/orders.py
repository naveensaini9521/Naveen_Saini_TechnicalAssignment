"""
Order routes (Parts 5, 6).

Sales User sees only own orders; Admin sees all.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import SalesOrder, Customer, Product
from app.services.order_service import (
    create_order, update_order, confirm_order, cancel_order, OrderError,
)
from app.services.customer_service import active_customers_for_select
from app.services.product_service import active_products_for_select
from app.utils.decorators import admin_required, can_access_order
from app.utils.validators import ValidationError


orders_bp = Blueprint("orders", __name__)


def _visible_orders_query():
    q = db.session.query(SalesOrder).order_by(SalesOrder.created_at.desc())
    if current_user.role != "Admin":
        q = q.filter(SalesOrder.created_by == current_user.id)
    return q


@orders_bp.route("/")
@login_required
def list_orders():
    page = int(request.args.get("page", 1))
    per_page = 20
    pagination = _visible_orders_query().paginate(page=page, per_page=per_page, error_out=False)
    return render_template("orders/list.html", pagination=pagination)


@orders_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        payload = {
            "customer_id": request.form.get("customer_id"),
            "discount_percentage": request.form.get("discount_percentage", 0),
            "order_date": request.form.get("order_date"),
            "items": [
                {"product_id": pid, "quantity": qty}
                for pid, qty in zip(
                    request.form.getlist("product_id[]"),
                    request.form.getlist("quantity[]"),
                )
                if pid and qty
            ],
        }
        try:
            order = create_order(payload, current_user)
            flash(f"Order {order.order_number} created.", "success")
            return redirect(url_for("orders.detail", order_id=order.id))
        except (ValidationError, OrderError) as e:
            flash(str(e), "error")

    return render_template(
        "orders/create.html",
        customers=active_customers_for_select(),
        products=active_products_for_select(),
    )


@orders_bp.route("/<int:order_id>")
@login_required
def detail(order_id):
    order = db.session.get(SalesOrder, order_id)
    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("orders.list_orders"))
    if not can_access_order(order, current_user):
        flash("You don't have access to that order.", "error")
        return redirect(url_for("orders.list_orders"))
    return render_template("orders/detail.html", order=order)


@orders_bp.route("/<int:order_id>/edit", methods=["GET", "POST"])
@login_required
def edit(order_id):
    order = db.session.get(SalesOrder, order_id)
    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("orders.list_orders"))
    if not can_access_order(order, current_user):
        flash("You don't have access to that order.", "error")
        return redirect(url_for("orders.list_orders"))
    if order.status != "Draft":
        flash("Only Draft orders can be edited.", "error")
        return redirect(url_for("orders.detail", order_id=order.id))

    if request.method == "POST":
        payload = {
            "discount_percentage": request.form.get("discount_percentage", order.discount_percentage),
            "items": [
                {"product_id": pid, "quantity": qty}
                for pid, qty in zip(
                    request.form.getlist("product_id[]"),
                    request.form.getlist("quantity[]"),
                )
                if pid and qty
            ],
        }
        try:
            update_order(order_id, payload, current_user)
            flash("Order updated.", "success")
            return redirect(url_for("orders.detail", order_id=order.id))
        except (ValidationError, OrderError) as e:
            flash(str(e), "error")

    return render_template(
        "orders/edit.html",
        order=order,
        products=active_products_for_select(),
    )


@orders_bp.route("/<int:order_id>/confirm", methods=["POST"])
@login_required
def confirm(order_id):
    order = db.session.get(SalesOrder, order_id)
    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("orders.list_orders"))
    if not can_access_order(order, current_user):
        flash("You don't have access to that order.", "error")
        return redirect(url_for("orders.list_orders"))
    try:
        confirm_order(order_id, current_user)
        flash(f"Order {order.order_number} confirmed.", "success")
    except (ValidationError, OrderError) as e:
        flash(str(e), "error")
    return redirect(url_for("orders.detail", order_id=order.id))


@orders_bp.route("/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel(order_id):
    order = db.session.get(SalesOrder, order_id)
    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("orders.list_orders"))
    if not can_access_order(order, current_user):
        flash("You don't have access to that order.", "error")
        return redirect(url_for("orders.list_orders"))
    try:
        cancel_order(order_id, current_user)
        flash(f"Order {order.order_number} cancelled.", "success")
    except (ValidationError, OrderError) as e:
        flash(str(e), "error")
    return redirect(url_for("orders.detail", order_id=order.id))