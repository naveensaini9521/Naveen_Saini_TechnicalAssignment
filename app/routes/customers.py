"""
Customer routes (Part 4).

Admin-only for create/edit/delete; both roles can browse.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify,
)
from flask_login import login_required, current_user

from app.services.customer_service import (
    list_customers, get_customer, create_customer, update_customer, delete_customer,
)
from app.utils.decorators import admin_required
from app.utils.validators import ValidationError


customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/")
@login_required
def list_customers_view():
    search = request.args.get("q", "")
    status = request.args.get("status", "all")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    pagination = list_customers(search=search, status=status, page=page, per_page=per_page)
    return render_template(
        "customers/list.html",
        pagination=pagination,
        search=search,
        status=status,
    )


@customers_bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    if request.method == "POST":
        try:
            c = create_customer(request.form)
            flash(f"Customer '{c.name}' created.", "success")
            return redirect(url_for("customers.list_customers_view"))
        except ValidationError as e:
            flash(str(e), "error")
    return render_template("customers/create.html")


@customers_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(customer_id):
    try:
        customer = get_customer(customer_id)
    except LookupError:
        flash("Customer not found.", "error")
        return redirect(url_for("customers.list_customers_view"))

    if request.method == "POST":
        try:
            update_customer(customer_id, request.form)
            flash("Customer updated.", "success")
            return redirect(url_for("customers.list_customers_view"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("customers/edit.html", customer=customer)


@customers_bp.route("/<int:customer_id>/delete", methods=["POST"])
@admin_required
def delete(customer_id):
    try:
        delete_customer(customer_id)
        flash("Customer deleted.", "success")
    except (ValidationError, LookupError) as e:
        flash(str(e), "error")
    return redirect(url_for("customers.list_customers_view"))