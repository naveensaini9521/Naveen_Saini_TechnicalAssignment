"""
Authentication service.

Pure business logic for login. No Flask request/response here.

Routes call:
    user = authenticate(email, password)
    login_user(user)

Tests call:
    user = authenticate("admin@example.com", "Admin@123")
    assert user.role == "Admin"
"""

from app.extensions import db
from app.models import User


class AuthError(ValueError):
    """Raised on failed authentication. Route converts to 401."""


def authenticate(email: str, password: str) -> User:
    """
    Verify credentials and return the User.

    Raises AuthError with a generic message on ANY failure.
    (Never reveal whether the email exists — Part 2 security best practice.)
    """
    if not email or not password:
        raise AuthError("Email and password are required.")

    user = db.session.execute(
        db.select(User).where(User.email == email.strip().lower())
    ).scalar_one_or_none()

    if user is None or not user.check_password(password):
        # Same message for "user not found" and "wrong password"
        raise AuthError("Invalid email or password.")

    return user


def get_user_by_id(user_id: int) -> User | None:
    """Used by tests and admin tooling."""
    return db.session.get(User, int(user_id))