"""
Role decorators and API error handling.

Provides:
    @admin_required       — only Admin can pass
    @login_required_json  — 401 JSON instead of redirect
    @role_required(...)   — generic
    error_response(...)   — uniform JSON error shape

Part 2: enforce roles on the backend.
Part 8: return proper status codes and clear JSON errors.
"""

from functools import wraps
from flask import jsonify, redirect, request, url_for, flash
from flask_login import current_user


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _is_api_request() -> bool:
    """Heuristic: requests under /api/ should return JSON, not redirects."""
    return request.path.startswith("/api/") or \
           request.accept_mimetypes.best == "application/json"


def error_response(message: str, status: int = 400, **extra):
    """Uniform JSON error shape (Part 8)."""
    payload = {"error": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), status


# ------------------------------------------------------------
# Role decorators
# ------------------------------------------------------------
def role_required(*allowed_roles):
    """
    Restrict a view to one or more roles.

    Behaviour:
      - Not logged in   → 401 (API) or redirect to login (HTML)
      - Wrong role      → 403 (API) or 403 page (HTML)
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                if _is_api_request():
                    return error_response("Authentication required.", 401)
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))

            if current_user.role not in allowed_roles:
                if _is_api_request():
                    return error_response(
                        f"Forbidden. Requires role: {', '.join(allowed_roles)}.",
                        403,
                    )
                # HTML → let the 403 error handler render
                from flask import abort
                abort(403)

            return view(*args, **kwargs)
        return wrapped
    return decorator


def admin_required(view):
    """Only Admin users (Part 4 access rule: master data is Admin-only)."""
    return role_required("Admin")(view)


def sales_or_admin(view):
    """Either Admin or Sales User — for shared read endpoints."""
    return role_required("Admin", "Sales User")(view)


def login_required_json(view):
    """
    Like flask_login.login_required, but returns JSON 401 for API calls
    instead of redirecting to the login page.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return error_response("Authentication required.", 401)
        return view(*args, **kwargs)
    return wrapped


# ------------------------------------------------------------
# Ownership check (used by order routes / services)
# ------------------------------------------------------------
def can_access_order(order, user) -> bool:
    """
    Admin can access any order.
    Sales User can only access orders they created (Part 2).
    """
    if not user.is_authenticated:
        return False
    if user.role == "Admin":
        return True
    return order.created_by == user.id