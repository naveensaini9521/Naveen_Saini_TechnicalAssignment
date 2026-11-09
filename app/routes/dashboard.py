"""
Dashboard / home page.
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models import Customer, Product, SalesOrder, StockMovement


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    stats = {
        "customers_active": db.session.query(func.count(Customer.id)).filter(Customer.is_active.is_(True)).scalar(),
        "products_active":  db.session.query(func.count(Product.id)).filter(Product.is_active.is_(True)).scalar(),
        "orders_draft":     db.session.query(func.count(SalesOrder.id)).filter(SalesOrder.status == "Draft").scalar(),
        "orders_confirmed": db.session.query(func.count(SalesOrder.id)).filter(SalesOrder.status == "Confirmed").scalar(),
        "orders_cancelled": db.session.query(func.count(SalesOrder.id)).filter(SalesOrder.status == "Cancelled").scalar(),
        "movements":        db.session.query(func.count(StockMovement.id)).scalar(),
    }
    recent_orders = (
        db.session.query(SalesOrder)
        .order_by(SalesOrder.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "dashboard/index.html",
        stats=stats,
        recent_orders=recent_orders,
        user=current_user,
    )