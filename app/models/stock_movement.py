from app.extensions import db


class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    id               = db.Column(db.Integer, primary_key=True)
    product_id       = db.Column(db.Integer, db.ForeignKey("products.id",     ondelete="RESTRICT"), nullable=False, index=True)
    movement_type    = db.Column(
        db.Enum("Opening", "Adjustment", "Order Confirm", "Order Cancel", name="movement_type"),
        nullable=False, index=True,
    )
    quantity_change  = db.Column(db.Integer, nullable=False)   # +5 = increase, -5 = decrease
    related_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=True, index=True)
    reason           = db.Column(db.String(255), nullable=True)
    created_by       = db.Column(db.Integer, db.ForeignKey("users.id",        ondelete="RESTRICT"), nullable=False)
    created_at       = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)

    __table_args__ = (
        db.CheckConstraint("quantity_change <> 0", name="chk_mv_qty_nonzero"),
    )

    product = db.relationship("Product",    back_populates="stock_movements")
    order   = db.relationship("SalesOrder", foreign_keys=[related_order_id])
    creator = db.relationship("User",       foreign_keys=[created_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_code": self.product.product_code if self.product else None,
            "movement_type": self.movement_type,
            "quantity_change": self.quantity_change,
            "related_order_id": self.related_order_id,
            "reason": self.reason,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Movement {self.movement_type} product={self.product_id} Δ={self.quantity_change}>"