"""
CSV import routes (Part 10).

Admin-only. All-or-nothing. Row-level error reporting.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, send_file,
)
from flask_login import login_required, current_user

from app.services.csv_import_service import import_products
from app.utils.decorators import admin_required
from app.utils.validators import ValidationError

import os


imports_bp = Blueprint("imports", __name__)

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data")


@imports_bp.route("/", methods=["GET", "POST"])
@admin_required
def upload():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or f.filename == "":
            flash("Please choose a CSV file.", "error")
            return render_template("imports/upload.html")

        if not f.filename.lower().endswith(".csv"):
            flash("Only .csv files are accepted.", "error")
            return render_template("imports/upload.html")

        try:
            text = f.read().decode("utf-8-sig")   # handles BOM
        except UnicodeDecodeError:
            flash("File must be UTF-8 encoded.", "error")
            return render_template("imports/upload.html")

        try:
            result = import_products(text, current_user)
            flash(f"Imported {result['imported']} products.", "success")
            return redirect(url_for("products.list_products_view"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("imports/upload.html")


@imports_bp.route("/sample/<string:kind>")
@admin_required
def sample(kind):
    """Download the valid/invalid sample CSVs."""
    if kind not in ("valid", "invalid"):
        flash("Unknown sample.", "error")
        return redirect(url_for("imports.upload"))
    path = os.path.join(SAMPLE_DIR, f"{kind}_products.csv")
    return send_file(path, as_attachment=True, download_name=f"{kind}_products.csv")