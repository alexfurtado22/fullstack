import uuid
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase

from .config import get_settings
from .dependencies import get_user_db
from .email import send_verification_email
from .models import User


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = get_settings().JWT_SECRET
    verification_token_secret = get_settings().JWT_SECRET

    async def on_after_register(self, user: User, request: Request | None = None):
        """
        Called after a user registers. This is where we trigger the verification email.
        """
        print(f"User {user.id} has registered.")

        # Generate a verification token manually
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "aud": "fastapi-users:verify",
            "exp": datetime.utcnow() + timedelta(hours=24),  # Token expires in 24 hours
        }
        token = jwt.encode(
            token_data, self.verification_token_secret, algorithm="HS256"
        )

        # Send the verification email
        await self.send_verification_email(user, token, request)

    async def send_verification_email(
        self, user: User, token: str, request: Request | None = None
    ):
        """
        Sends the verification email to the user.
        """
        print(f"Sending verification email to {user.email}")
        try:
            await send_verification_email(user.email, user, token)
            print(f"Sent verification email to {user.email}")
        except Exception as e:
            print(f"Error sending verification email to {user.email}: {e}")
            pass

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ):
        """
        Hook for forgot password (you can implement this later).
        """
        print(f"User {user.id} has requested a password reset. Token: {token}")
        pass


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """
    Dependency to get the UserManager.
    """
    yield UserManager(user_db)
