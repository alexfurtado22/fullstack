import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Callable
from uuid import UUID

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware

from .admin import CommentAdmin, PostAdmin, UserAdmin
from .auth import (
    fastapi_users,
    get_access_token_strategy,
    get_refresh_token_strategy,
    get_user_manager,
)
from .auth_backend import AdminAuthBackend
from .comments import router as comments_router
from .config import get_settings
from .database import engine
from .dependencies import get_user_db
from .logging_config import logger
from .models import Comment, Post, User  # noqa: F401
from .posts import router as posts_router
from .schemas import UserCreate, UserRead, UserUpdate
from .uploads import router as uploads_router


# --- 1. Lifespan (Handles Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting up FastAPI application...")
    logger.success("🌐 App instance created successfully!")
    try:
        yield
    finally:
        logger.info("🧹 Shutting down and disposing engine...")
        await engine.dispose()
        logger.success("✅ Shutdown complete.")


app = FastAPI(lifespan=lifespan)

# ContextVar for per-request logging context
request_logger: ContextVar = ContextVar("request_logger", default=logger)


# --- 2. Request Logging Middleware ---
@app.middleware("http")
async def add_request_context(request: Request, call_next: Callable):
    start_time = time.perf_counter()
    log = logger.bind(
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown",
    )

    token = request_logger.set(log)

    try:
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000
        log.info(
            f"✅ {request.method} {request.url.path} completed in {process_time:.2f}ms"
        )
        return response
    except Exception as e:
        log.exception(f"❌ Error handling request: {e}")
        raise
    finally:
        request_logger.reset(token)


# --- 2. Middleware ---
# REQUIRED for admin authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().JWT_SECRET,
)

# --- 3. SQLAdmin Panel with Authentication Backend ---
# This is the CORRECT way to secure the entire admin panel
authentication_backend = AdminAuthBackend(secret_key=get_settings().JWT_SECRET)

admin = Admin(
    app=app,
    engine=engine,
    authentication_backend=authentication_backend,  # 👈 THIS PROTECTS EVERYTHING
)

admin.add_view(UserAdmin)
admin.add_view(PostAdmin)
admin.add_view(CommentAdmin)


# --- 4. Custom Auth Routes (Login, Refresh, Logout) ---
@app.post("/auth/login", tags=["auth"])
async def login(
    response: Response,
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_manager=Depends(get_user_manager),
):
    """
    Login endpoint: returns access token in body, sets refresh token in cookie.
    """
    logger.info(f"👤 Login attempt for user: {credentials.username}")

    user = await user_manager.authenticate(credentials)
    if user is None or not user.is_active:
        logger.warning(f"⚠️ Failed login for user: {credentials.username}")
        raise HTTPException(status_code=400, detail="LOGIN_BAD_CREDENTIALS")

    # Create Access Token
    access_strategy = get_access_token_strategy()
    access_token = await access_strategy.write_token(user)

    # Create Refresh Token
    refresh_strategy = get_refresh_token_strategy()
    refresh_token = await refresh_strategy.write_token(user)

    # Set the secure refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=604800,  # 7 days
        httponly=True,
        secure=get_settings().ENVIRONMENT == "production",
        samesite="lax",
    )
    logger.success(f"✅ User {user.email} logged in successfully.")
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/refresh", tags=["auth"])
async def refresh_token(
    request: Request,
    response: Response,
    user_manager=Depends(get_user_manager),
):
    """
    Uses the refresh token from cookie to generate a new access token.
    """
    refresh_token_value = request.cookies.get("refresh_token")
    if not refresh_token_value:
        raise HTTPException(
            status_code=401, detail="Refresh token not found. Please login again."
        )
    try:
        strategy = get_refresh_token_strategy()
        user = await strategy.read_token(refresh_token_value, user_manager)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=401, detail="Invalid refresh token or inactive user"
            )

        access_strategy = get_access_token_strategy()
        new_access_token = await access_strategy.write_token(user)

        refresh_strategy = get_refresh_token_strategy()
        new_refresh_token = await refresh_strategy.write_token(user)

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            max_age=604800,
            httponly=True,
            secure=get_settings().ENVIRONMENT == "production",
            samesite="lax",
        )
        return {"access_token": new_access_token, "token_type": "bearer"}
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token. Please login again.",
        )


# --- 4.0 Logout Route ---
@app.post("/auth/logout", tags=["auth"])
async def logout(response: Response):
    """
    Clears the refresh token cookie.
    """
    logger.info("🚪 Logout request received.")
    response.delete_cookie(key="refresh_token")
    logger.success("✅ Refresh token cookie cleared and user logged out.")
    return {"message": "Successfully logged out"}


# --- 4.1 Custom Email Verification GET Endpoint ---
@app.get("/auth/verify", response_class=HTMLResponse, tags=["auth"])
async def verify_email_get(
    token: str,
    user_db=Depends(get_user_db),
):
    """
    GET endpoint for email verification - user clicks link in email.
    This handles the token and marks the user as verified.
    """
    try:
        logger.info("📧 Received email verification request.")

        # Decode and verify token
        payload = jwt.decode(
            token,
            get_settings().JWT_SECRET,
            audience="fastapi-users:verify",
            algorithms=["HS256"],
        )
        user_id = payload.get("sub")

        if not user_id:
            logger.warning("⚠️ Verification token missing user ID.")
            raise HTTPException(
                status_code=400, detail="Invalid token: missing user ID"
            )

        # Retrieve user
        user = await user_db.get(UUID(user_id))
        if not user:
            logger.warning(f"⚠️ Verification failed — user ID not found: {user_id}")
            raise HTTPException(status_code=400, detail="User not found")

        if user.is_verified:
            logger.info(f"ℹ️ User already verified: {user.email}")
            return f"""
            <html>
                <body style="font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f0f0;">
                    <div style="text-align: center; padding: 40px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <h1 style="color: #ffc107;">⚠️ Already Verified</h1>
                        <p>Your email <strong>{user.email}</strong> was already verified.</p>
                        <p>You can close this window.</p>
                        <a href="http://localhost:8000/docs" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 5px;">
                            Go to API Docs
                        </a>
                    </div>
                </body>
            </html>
            """

        # Mark as verified
        user.is_verified = True
        # Mark as verified
        await user_db.update(user, {"is_verified": True})

        logger.success(f"✅ User {user.email} verified successfully.")

        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f0f0;">
                <div style="text-align: center; padding: 40px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h1 style="color: #28a745;">✓ Email Verified!</h1>
                    <p>Your email <strong>{user.email}</strong> has been successfully verified.</p>
                    <p>You can now close this window and log in to your account.</p>
                    <a href="http://localhost:8000/docs" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 5px;">
                        Go to API Docs
                    </a>
                </div>
            </body>
        </html>
        """

    except jwt.ExpiredSignatureError:
        logger.warning("⏰ Email verification token expired.")
        return """
        <html>
            <body style="font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f0f0;">
                <div style="text-align: center; padding: 40px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h1 style="color: #dc3545;">⏰ Token Expired</h1>
                    <p>Your verification link has expired.</p>
                    <p>Please request a new verification email.</p>
                </div>
            </body>
        </html>
        """
    except jwt.InvalidTokenError:
        logger.error("❌ Invalid verification token.")
        return """
        <html>
            <body style="font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f0f0;">
                <div style="text-align: center; padding: 40px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h1 style="color: #dc3545;">❌ Invalid Token</h1>
                    <p>The verification link is invalid.</p>
                    <p>Please check your email and try again.</p>
                </div>
            </body>
        </html>
        """
    except Exception as e:
        logger.exception(f"❌ Error verifying email: {e}")
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f0f0;">
                <div style="text-align: center; padding: 40px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h1 style="color: #dc3545;">❌ Verification Failed</h1>
                    <p>An error occurred during verification.</p>
                    <p style="color: #666; font-size: 12px;">Error: {str(e)}</p>
                </div>
            </body>
        </html>
        """


# --- 5. Pre-built FastAPI_Users Routes ---
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# --- 5.1 Verification and Password Reset Routes ---
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

# --- 6. Your "Posts" App ---
app.include_router(posts_router)
app.include_router(comments_router)  # 👈 2. ADD THIS
app.include_router(uploads_router)


# --- 7. Example & Debug Routes ---
@app.get("/protected")
async def protected_route(
    user: User = Depends(fastapi_users.current_user(active=True)),
):
    logger.info(f"🔐 Protected route accessed by {user.email}")
    return {
        "message": "This is a protected route",
        "user_id": str(user.id),
        "email": user.email,
    }


@app.get("/debug/cookies")
async def debug_cookies(request: Request):
    logger.debug(f"🍪 Debug cookies: {request.cookies}")
    return {"cookies": dict(request.cookies)}


@app.get("/")
def read_root():
    logger.info("🏠 Root endpoint accessed.")
    return {"status": "ok", "message": "Welcome to the API"}
