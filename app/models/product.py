from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id             = db.Column(db.Integer, primary_key=True)
    product_code   = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name           = db.Column(db.String(150), nullable=False, index=True)
    category       = db.Column(db.String(100), nullable=False, index=True)
    price          = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    is_active      = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at     = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    # Relationships (defined but don't cascade)
    order_items     = db.relationship("SalesOrderItem",     back_populates="product", lazy="select", passive_deletes=True)
    stock_movements = db.relationship("StockMovement",      back_populates="product", lazy="select", passive_deletes=True)

    @property
    def status_label(self) -> str:
        return "Active" if self.is_active else "Inactive"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_code": self.product_code,
            "name": self.name,
            "category": self.category,
            "price": str(self.price),         # Decimal → string for JSON
            "stock_quantity": self.stock_quantity,
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return f"<Product {self.product_code} {self.name}>"