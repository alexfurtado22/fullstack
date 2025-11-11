# app/utils.py
from urllib.parse import urlparse

from fastapi import UploadFile

from .config import get_settings  # 👈 1. ADD THIS IMPORT
from .imagekit_client import imagekit
from .logging_config import logger


# This function is NO LONGER USED in Path A for creating posts,
# but it's fine to leave it for future reference.
async def upload_file_to_imagekit(
    file: UploadFile,
    file_name: str | None = None,
    folder: str = "posts",
) -> str | None:
    """
    (NO LONGER USED for post creation in Path A)
    Uploads a file to ImageKit and returns the public URL.
    """
    if not file or imagekit is None:
        return None

    # Read file content
    file_bytes = await file.read()

    try:
        logger.info(f"Uploading file '{file_name}' to ImageKit folder '{folder}'...")

        upload_result = imagekit.upload(
            file=file_bytes,
            file_name=file_name,
            options={
                "folder": folder,
                "is_private_file": False,
                "use_unique_file_name": False,
            },
        )
        logger.success(f"File uploaded successfully: {upload_result.url}")
        return upload_result.url
    except Exception as e:
        logger.error(f"Error uploading file '{file_name}': {e}")
        # In this (unused) version, we don't raise an exception
        return None


# 👇 THIS IS THE UPDATED FUNCTION
async def delete_file_from_imagekit(file_url: str):
    """
    Deletes a file from ImageKit using its full URL.
    """
    settings = get_settings()

    # --- 👇 2. ADD THIS VALIDATION BLOCK ---
    if not file_url or imagekit is None:
        logger.warning("No file URL provided or ImageKit client not init.")
        return

    # Check if it's a real ImageKit URL before trying to delete
    if not file_url.startswith(settings.IMAGEKIT_URL_ENDPOINT):
        logger.warning(
            f"Skipping delete: URL '{file_url}' is not a valid ImageKit URL."
        )
        return  # Not our URL, so don't try to delete it
    # --- END OF VALIDATION BLOCK ---

    try:
        # 1. Parse the URL to get the path
        # e.g., "https://ik.imagekit.io/your_id/post_images/file.jpg"
        path = urlparse(file_url).path

        # 2. Search for the file by its path
        logger.info(f"Attempting to find file with path: {path}")
        file_list = imagekit.list_files({"path": path})

        if file_list.list:
            file_id = file_list.list[0].file_id
            logger.info(f"Found file_id: {file_id}. Deleting...")

            # 3. Delete the file using its unique ID
            imagekit.delete_file(file_id=file_id)
            logger.success(f"Successfully deleted file {file_id} from ImageKit.")
        else:
            logger.warning(f"Could not find file at path {path} in ImageKit to delete.")

    except Exception as e:
        logger.error(f"Error deleting file {file_url} from ImageKit: {e}")
        # We log the error but don't stop the HTTP request
