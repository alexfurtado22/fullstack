# app/imagekit_client.py
from imagekitio import ImageKit

from .config import get_settings
from .logging_config import logger

settings = get_settings()

try:
    imagekit = ImageKit(
        private_key=settings.IMAGEKIT_PRIVATE_KEY,
        public_key=settings.IMAGEKIT_PUBLIC_KEY,
        url_endpoint=settings.IMAGEKIT_URL_ENDPOINT,
    )
    logger.success("✅ ImageKit Client initialized successfully.")
except Exception as e:
    logger.critical(f"🔥 Failed to initialize ImageKit Client: {e}")
    # You might want to exit the app if ImageKit is critical
    # exit(1)
    imagekit = None
