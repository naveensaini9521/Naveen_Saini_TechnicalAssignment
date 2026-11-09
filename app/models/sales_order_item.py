from app.extensions import db


class SalesOrderItem(db.Model):
    __tablename__ = "sales_order_items"

    id             = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id     = db.Column(db.Integer, db.ForeignKey("products.id",     ondelete="RESTRICT"), nullable=False, index=True)
    quantity       = db.Column(db.Integer, nullable=False)
    rate           = db.Column(db.Numeric(10, 2), nullable=False)   # frozen at creation
    amount         = db.Column(db.Numeric(12, 2), nullable=False)   # qty * rate, backend-computed

    # Reject duplicate products in the same order (Part 5 requirement)
    __table_args__ = (
        db.UniqueConstraint("sales_order_id", "product_id", name="uq_items_order_product"),
        db.CheckConstraint("quantity > 0", name="chk_items_qty"),
        db.CheckConstraint("rate >= 0", name="chk_items_rate"),
    )

    order   = db.relationship("SalesOrder", back_populates="items")
    product = db.relationship("Product",    back_populates="order_items")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_code": self.product.product_code if self.product else None,
            "product_name": self.product.name if self.product else None,
            "quantity": self.quantity,
            "rate": str(self.rate),
            "amount": str(self.amount),
        }

    def __repr__(self) -> str:
        return f"<Item order={self.sales_order_id} product={self.product_id} qty={self.quantity}>"