from app.extensions import db


class SalesOrder(db.Model):
    __tablename__ = "sales_orders"

    id                  = db.Column(db.Integer, primary_key=True)
    order_number        = db.Column(db.String(30), nullable=False, unique=True, index=True)
    customer_id         = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_date          = db.Column(db.Date, nullable=False, index=True)
    status              = db.Column(
        db.Enum("Draft", "Confirmed", "Cancelled", name="order_status"),
        nullable=False, default="Draft", index=True,
    )
    discount_percentage = db.Column(db.Numeric(5, 2),  nullable=False, default=0)
    subtotal            = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_amount     = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    grand_total         = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_by          = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at          = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at          = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    customer = db.relationship("Customer", back_populates="orders")
    creator  = db.relationship("User",     foreign_keys=[created_by])
    items    = db.relationship(
        "SalesOrderItem", back_populates="order",
        cascade="all, delete-orphan", lazy="select",
    )

    # ---- State helpers (used everywhere) ----
    @property
    def is_draft(self) -> bool:
        return self.status == "Draft"

    @property
    def is_confirmed(self) -> bool:
        return self.status == "Confirmed"

    @property
    def is_cancelled(self) -> bool:
        return self.status == "Cancelled"

    @property
    def is_read_only(self) -> bool:
        """Confirmed and Cancelled orders must be read-only (Part 6)."""
        return self.status in ("Confirmed", "Cancelled")

    def to_dict(self, include_items: bool = False) -> dict:
        data = {
            "id": self.id,
            "order_number": self.order_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "status": self.status,
            "discount_percentage": str(self.discount_percentage),
            "subtotal": str(self.subtotal),
            "discount_amount": str(self.discount_amount),
            "grand_total": str(self.grand_total),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data

    def __repr__(self) -> str:
        return f"<SalesOrder {self.order_number} {self.status}>"