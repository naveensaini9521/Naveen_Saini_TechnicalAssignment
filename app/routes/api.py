"""
REST API (Part 8).

Endpoints:
    GET  /api/products               list active products with search & pagination
    POST /api/orders                 create a Draft order
    GET  /api/orders/{id}            retrieve an accessible order with items
    POST /api/orders/{id}/confirm    confirm an order and deduct stock
    POST /api/orders/{id}/cancel     cancel an order and restore stock where required

All endpoints require authentication. Errors are JSON {"error": "..."}.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import or_

from app.extensions import db
from app.models import Product, SalesOrder
from app.services.order_service import (
    create_order, confirm_order, cancel_order, OrderError,
)
from app.utils.decorators import login_required_json, can_access_order, error_response
from app.utils.validators import ValidationError
from app.utils.helpers import paginate_query


api_bp = Blueprint("api", __name__)


# ------------------------------------------------------------
# GET /api/products
# ------------------------------------------------------------
@api_bp.route("/products", methods=["GET"])
@login_required_json
def list_products():
    search = (request.args.get("q") or "").strip()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    q = db.session.query(Product).filter(Product.is_active.is_(True))
    if search:
        s = f"%{search}%"
        q = q.filter(or_(Product.product_code.ilike(s), Product.name.ilike(s)))
    q = q.order_by(Product.name.asc())

    page_obj = paginate_query(q, page=page, per_page=per_page)
    return jsonify({
        "items": [p.to_dict() for p in page_obj.items],
        "page": page_obj.page,
        "per_page": page_obj.per_page,
        "total": page_obj.total,
        "pages": page_obj.pages,
    }), 200


# ------------------------------------------------------------
# POST /api/orders
# ------------------------------------------------------------
@api_bp.route("/orders", methods=["POST"])
@login_required_json
def create_order_api():
    payload = request.get_json(silent=True) or {}
    try:
        order = create_order(payload, current_user)
        return jsonify(order.to_dict(include_items=True)), 201
    except ValidationError as e:
        return error_response(str(e), 400)
    except OrderError as e:
        return error_response(str(e), 400)
    except Exception:
        db.session.rollback()
        return error_response("Internal error while creating order.", 500)


# ------------------------------------------------------------
# GET /api/orders/{id}
# ------------------------------------------------------------
@api_bp.route("/orders/<int:order_id>", methods=["GET"])
@login_required_json
def get_order_api(order_id):
    order = db.session.get(SalesOrder, order_id)
    if order is None:
        return error_response("Order not found.", 404)
    if not can_access_order(order, current_user):
        return error_response("Forbidden.", 403)
    return jsonify(order.to_dict(include_items=True)), 200


# ------------------------------------------------------------
# POST /api/orders/{id}/confirm
# ------------------------------------------------------------
@api_bp.route("/orders/<int:order_id>/confirm", methods=["POST"])
@login_required_json
def confirm_order_api(order_id):
    order = db.session.get(SalesOrder, order_id)
    if order is None:
        return error_response("Order not found.", 404)
    if not can_access_order(order, current_user):
        return error_response("Forbidden.", 403)
    try:
        confirm_order(order_id, current_user)
        # Re-fetch to reflect the state after commit
        order = db.session.get(SalesOrder, order_id)
        return jsonify(order.to_dict(include_items=True)), 200
    except ValidationError as e:
        return error_response(str(e), 400)
    except OrderError as e:
        return error_response(str(e), 409)
    except Exception:
        db.session.rollback()
        return error_response("Internal error while confirming order.", 500)


# ------------------------------------------------------------
# POST /api/orders/{id}/cancel
# ------------------------------------------------------------
@api_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required_json
def cancel_order_api(order_id):
    order = db.session.get(SalesOrder, order_id)
    if order is None:
        return error_response("Order not found.", 404)
    if not can_access_order(order, current_user):
        return error_response("Forbidden.", 403)
    try:
        cancel_order(order_id, current_user)
        order = db.session.get(SalesOrder, order_id)
        return jsonify(order.to_dict(include_items=True)), 200
    except ValidationError as e:
        return error_response(str(e), 400)
    except OrderError as e:
        return error_response(str(e), 409)
    except Exception:
        db.session.rollback()
        return error_response("Internal error while cancelling order.", 500)