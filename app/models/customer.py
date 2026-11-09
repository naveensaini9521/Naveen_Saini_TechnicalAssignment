from app.extensions import db


class Customer(db.Model):
    __tablename__ = "customers"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(150), nullable=False, index=True)
    email      = db.Column(db.String(190), nullable=True, index=True)
    mobile     = db.Column(db.String(20), nullable=True, index=True)
    city       = db.Column(db.String(100), nullable=True)
    is_active  = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    # One customer → many orders. No cascade delete: prevent removing
    # referenced customers (Part 3 requirement).
    orders = db.relationship(
        "SalesOrder",
        back_populates="customer",
        lazy="select",
        passive_deletes=True,
    )

    @property
    def status_label(self) -> str:
        return "Active" if self.is_active else "Inactive"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "mobile": self.mobile,
            "city": self.city,
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return f"<Customer {self.id} {self.name}>"