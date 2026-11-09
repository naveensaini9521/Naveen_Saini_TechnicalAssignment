"""
Reports routes (Part 9).

All reports are Admin-only.
"""

from flask import Blueprint, render_template, request, flash
from flask_login import login_required

from app.services.report_service import (
    customer_sales_summary, product_sales_summary,
    low_stock_report, stock_movement_history,
)
from app.utils.decorators import admin_required
from app.utils.validators import ValidationError


reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/")
@admin_required
def home():
    return render_template("reports/home.html")


@reports_bp.route("/customer-sales")
@admin_required
def customer_sales():
    date_from = request.args.get("date_from", "")
    date_to   = request.args.get("date_to", "")
    rows = []
    try:
        rows = customer_sales_summary(date_from or None, date_to or None)
    except ValidationError as e:
        flash(str(e), "error")
    return render_template(
        "reports/customer_sales.html",
        rows=rows, date_from=date_from, date_to=date_to,
    )


@reports_bp.route("/product-sales")
@admin_required
def product_sales():
    date_from = request.args.get("date_from", "")
    date_to   = request.args.get("date_to", "")
    rows = []
    try:
        rows = product_sales_summary(date_from or None, date_to or None)
    except ValidationError as e:
        flash(str(e), "error")
    return render_template(
        "reports/product_sales.html",
        rows=rows, date_from=date_from, date_to=date_to,
    )


@reports_bp.route("/low-stock")
@admin_required
def low_stock():
    threshold = request.args.get("threshold", "")
    rows = []
    if threshold:
        try:
            rows = low_stock_report(threshold)
        except ValidationError as e:
            flash(str(e), "error")
    return render_template("reports/low_stock.html", rows=rows, threshold=threshold)


@reports_bp.route("/stock-movements")
@admin_required
def stock_movements():
    product_id = request.args.get("product_id", "")
    date_from  = request.args.get("date_from", "")
    date_to    = request.args.get("date_to", "")
    rows = stock_movement_history(
        product_id=product_id or None,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    return render_template(
        "reports/stock_movements.html",
        rows=rows, product_id=product_id, date_from=date_from, date_to=date_to,
    )