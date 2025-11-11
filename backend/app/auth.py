import uuid

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
    JWTStrategy,
)

from .config import get_settings
from .manager import get_user_manager  # <-- Import from new file
from .models import User

# --- 2. JWT Strategies ---


# Short-lived ACCESS token (15 minutes)
def get_access_token_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=get_settings().JWT_SECRET,
        lifetime_seconds=900,  # 15 minutes
    )


# Long-lived REFRESH token (7 days)
def get_refresh_token_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=get_settings().JWT_SECRET,
        lifetime_seconds=604800,  # 7 days
    )


# --- 3. Transports ---

# Bearer transport for ACCESS tokens
bearer_transport = BearerTransport(tokenUrl="/auth/login")

# Cookie transport for REFRESH tokens
cookie_transport = CookieTransport(
    cookie_name="refresh_token",
    cookie_max_age=604800,
    cookie_httponly=True,
    cookie_secure=get_settings().ENVIRONMENT == "production",
    cookie_samesite="lax",
)

# --- 4. Authentication Backends ---

# ACCESS token backend
access_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_access_token_strategy,
)

# REFRESH token backend
refresh_backend = AuthenticationBackend(
    name="refresh",
    transport=cookie_transport,
    get_strategy=get_refresh_token_strategy,
)

# --- 5. FastAPIUsers Instance ---
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,  # <-- This is imported from manager.py
    [access_backend, refresh_backend],
)

# --- 6. Current User Dependency ---
current_active_user = fastapi_users.current_user(active=True)

# --- 7. ADD THIS NEW DEPENDENCY ---
# Dependency for a user who is logged in AND verified
current_active_verified_user = fastapi_users.current_user(active=True, verified=True)
