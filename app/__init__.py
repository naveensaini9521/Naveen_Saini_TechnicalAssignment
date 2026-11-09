from flask import Flask, render_template
from config import Config
from app.extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ---- Extensions ----
    db.init_app(app)
    login_manager.init_app(app)

    # ---- Models (must import before db.create_all / queries) ----
    from app import models  # noqa: F401  (registers all models with SQLAlchemy)

    # ---- Blueprints ----
    from app.routes.auth      import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.customers import customers_bp
    from app.routes.products  import products_bp
    from app.routes.orders    import orders_bp
    from app.routes.inventory import inventory_bp
    from app.routes.reports   import reports_bp
    from app.routes.imports   import imports_bp
    from app.routes.api       import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(products_bp,  url_prefix="/products")
    app.register_blueprint(orders_bp,    url_prefix="/orders")
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(reports_bp,   url_prefix="/reports")
    app.register_blueprint(imports_bp,   url_prefix="/imports")
    app.register_blueprint(api_bp,       url_prefix="/api")

    # ---- Error handlers ----
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # ---- Dev convenience ----
    if app.config.get("DEBUG") and app.config["SECRET_KEY"] == "dev-secret-change-me":
        app.logger.warning("SECRET_KEY is the dev default — set SECRET_KEY in .env before deploying.")

    return app