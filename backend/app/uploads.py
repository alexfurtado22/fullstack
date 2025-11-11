# app/uploads.py
import time

from fastapi import APIRouter, Depends, HTTPException

from .auth import current_active_verified_user  # Import our security
from .imagekit_client import imagekit  # Import our initialized client
from .logging_config import logger
from .models import User

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.get("/auth")
async def get_imagekit_auth(user: User = Depends(current_active_verified_user)):
    """
    Get temporary authentication parameters for client-side
    upload to ImageKit.

    The user must be authenticated and verified to get these.
    """
    if imagekit is None:
        logger.error("ImageKit client is not initialized.")
        raise HTTPException(
            status_code=500, detail="File upload service is not configured."
        )

    # Generate a unique token, expiring in 60 seconds
    # This prevents users from just holding on to tokens.
    params = imagekit.get_authentication_parameters(
        token=f"{user.id}_{int(time.time())}", expire=60
    )

    logger.info(f"Generated ImageKit auth token for user {user.email}")
    return params
