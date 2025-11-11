from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from .database import async_session_maker
from .models import User


class AdminAuthBackend(AuthenticationBackend):
    """
    Custom authentication backend for SQLAdmin.
    This is the CORRECT way to protect the entire admin panel.
    """

    async def login(self, request: Request) -> bool:
        """
        Handle login form submission.
        Returns True if login successful, False otherwise.
        """
        form = await request.form()
        username = form.get("username")  # SQLAdmin uses 'username' field
        password = form.get("password")

        # Get user manager
        async with async_session_maker() as session:
            # Find user by email
            result = await session.execute(select(User).where(User.email == username))
            user = result.scalar_one_or_none()

            if not user:
                return False

            # Verify password using fastapi-users manager
            from fastapi_users.password import PasswordHelper

            password_helper = PasswordHelper()

            verified, updated_hash = password_helper.verify_and_update(
                password, user.hashed_password
            )

            if not verified:
                return False

            # Check if user is active and superuser
            if not user.is_active or not user.is_superuser:
                return False

            # Store user info in session
            request.session["user_id"] = str(user.id)
            request.session["user_email"] = user.email
            return True

    async def logout(self, request: Request) -> bool:
        """
        Handle logout.
        """
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """
        Check if user is authenticated.
        This is called on EVERY admin page request.
        """
        user_id = request.session.get("user_id")

        if not user_id:
            return False

        # Verify user still exists and is still a superuser
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user or not user.is_active or not user.is_superuser:
                request.session.clear()
                return False

            return True
