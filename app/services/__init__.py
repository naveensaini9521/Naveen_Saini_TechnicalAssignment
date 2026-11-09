"""
Service layer.

Business logic lives here. Routes call services; services call models
and utilities. Services never touch request/response objects — that
keeps them testable in isolation (Part 12).

Convenience re-exports so routes can do:

    from app.services import auth_service, customer_service, product_service
    from app.services import order_service, inventory_service
    from app.services import report_service, csv_import_service
"""

from app.services import (
    auth_service,
    customer_service,
    product_service,
    order_service,
    inventory_service,
    report_service,
    csv_import_service,
)

__all__ = [
    "auth_service",
    "customer_service",
    "product_service",
    "order_service",
    "inventory_service",
    "report_service",
    "csv_import_service",
]