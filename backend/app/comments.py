# app/comments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from .auth import current_active_verified_user
from .database import get_db_session
from .logging_config import logger
from .models import Comment, User
from .schemas import CommentReadWithUser, CommentUpdate

# Create a new router
router = APIRouter(prefix="/comments", tags=["Comments"])


# === 1. Update Comment (Owner Only & Verified) ===
@router.patch("/{comment_id}", response_model=CommentReadWithUser)
async def update_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    user: User = Depends(current_active_verified_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update a comment. The user must be the owner AND VERIFIED.
    """
    logger.info(f"User {user.email} attempting to update comment {comment_id}")

    # Use selectinload to get the owner relationship, which is
    # required by the CommentReadWithUser response model.
    query = (
        select(Comment)
        .where(Comment.id == comment_id)
        .options(selectinload(Comment.owner))
    )
    result = await session.execute(query)
    comment = result.scalar_one_or_none()

    if comment is None:
        logger.warning(f"Comment {comment_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    if comment.owner_id != user.id:
        logger.warning(
            f"User {user.email} failed to update comment {comment_id}: Not owner."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this comment",
        )

    # Update the data
    update_data = comment_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(comment, key, value)

    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    logger.success(f"Comment {comment_id} updated successfully by {user.email}")
    return comment


# === 2. Delete Comment (Owner Only & Verified) ===
@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    user: User = Depends(current_active_verified_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete a comment. The user must be the owner AND VERIFIED.
    """
    logger.info(f"User {user.email} attempting to delete comment {comment_id}")

    # We only need to fetch the comment, no relationships needed
    result = await session.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()

    if comment is None:
        logger.warning(f"Comment {comment_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    if comment.owner_id != user.id:
        logger.warning(
            f"User {user.email} failed to delete comment {comment_id}: Not owner."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment",
        )

    await session.delete(comment)
    await session.commit()

    logger.success(f"Comment {comment_id} deleted successfully by {user.email}")
    return None
