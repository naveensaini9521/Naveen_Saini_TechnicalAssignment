from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(190), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.Enum("Admin", "Sales User", name="user_role"), nullable=False)
    created_at    = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    # ---- Password helpers ----
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # ---- Role helpers (used by decorators / templates) ----
    @property
    def is_admin(self) -> bool:
        return self.role == "Admin"

    def to_dict(self) -> dict:
        # Never include password_hash
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))