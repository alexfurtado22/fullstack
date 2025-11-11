# --- 👇 1. ADD THIS IMPORT ---
import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from .auth import current_active_verified_user
from .database import get_db_session
from .models import Comment, Post, User
from .schemas import (
    CommentCreate,
    CommentReadWithUser,
    PostCreate,
    PostRead,
    PostReadWithDetails,
    PostUpdate,
)

# --- 👇 2. ADD THIS IMPORT ---
from .utils import delete_file_from_imagekit

# Create a new router
router = APIRouter(prefix="/posts", tags=["Posts"])


# === 1. Create Post (NO CHANGES) ===
@router.post("/", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    user: User = Depends(current_active_verified_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new post. The user must be authenticated AND VERIFIED.
    """
    new_post = Post(**post.model_dump(), owner_id=user.id)
    session.add(new_post)
    await session.commit()
    await session.refresh(new_post)
    return new_post


# === 2. Get All Posts (NO CHANGES) ===
@router.get("/", response_model=List[PostRead])
async def get_all_posts(
    session: AsyncSession = Depends(get_db_session), skip: int = 0, limit: int = 10
):
    """
    Get all posts. This endpoint is public.
    """
    query = select(Post).order_by(Post.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    posts = result.scalars().all()
    return posts


# === 3. Get Single Post (NO CHANGES) ===
@router.get("/{post_id}", response_model=PostReadWithDetails)
async def get_post_by_id(post_id: int, session: AsyncSession = Depends(get_db_session)):
    """
    Get a single post by its ID. Public and includes details.
    """
    query = (
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.owner),
            selectinload(Post.comments).selectinload(Comment.owner),
        )
    )
    result = await session.execute(query)
    post = result.scalar_one_or_none()

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    return post


# === 4. Update Post (NO CHANGES) ===
@router.patch("/{post_id}", response_model=PostRead)
async def update_post(
    post_id: int,
    post_update: PostUpdate,
    user: User = Depends(current_active_verified_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update a post. The user must be the owner AND VERIFIED.
    """
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    if post.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )

    update_data = post_update.model_dump(exclude_unset=True)

    # Store old URLs *before* updating the post object,
    # so we can delete them from ImageKit after the update.
    old_image_url = post.image_url if "image_url" in update_data else None
    old_video_url = post.video_url if "video_url" in update_data else None

    for key, value in update_data.items():
        setattr(post, key, value)

    session.add(post)
    await session.commit()
    await session.refresh(post)

    # Now that the DB update is successful, delete the old files.
    delete_tasks = []
    if old_image_url and old_image_url != post.image_url:
        delete_tasks.append(delete_file_from_imagekit(old_image_url))
    if old_video_url and old_video_url != post.video_url:
        delete_tasks.append(delete_file_from_imagekit(old_video_url))

    if delete_tasks:
        await asyncio.gather(*delete_tasks)

    return post


# === 5. Delete Post (NO CHANGES) ===
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    user: User = Depends(current_active_verified_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete a post. The user must be the owner AND VERIFIED.
    """
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    if post.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )

    # Store the URLs before we delete the post from the DB
    image_url_to_delete = post.image_url
    video_url_to_delete = post.video_url

    await session.delete(post)
    await session.commit()

    # Now that the post is deleted from the DB, delete files from ImageKit
    delete_tasks = []
    if image_url_to_delete:
        delete_tasks.append(delete_file_from_imagekit(image_url_to_delete))
    if video_url_to_delete:
        delete_tasks.append(delete_file_from_imagekit(video_url_to_delete))

    if delete_tasks:
        await asyncio.gather(*delete_tasks)

    return None


# === 👇 6. GET ALL COMMENTS FOR A POST (NEW ENDPOINT) ===
@router.get(
    "/{post_id}/comments/",
    response_model=List[CommentReadWithUser],
    tags=["Posts", "Comments"],  # Add "Comments" tag for organization
)
async def get_comments_for_post(
    post_id: int, session: AsyncSession = Depends(get_db_session)
):
    """
    Get all comments for a specific post. Public endpoint.
    """
    # First, check if the post exists to return a clear 404
    post_result = await session.execute(select(Post).where(Post.id == post_id))
    if post_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    # Now, get all comments for that post, eagerly loading the owner
    query = (
        select(Comment)
        .where(Comment.post_id == post_id)
        .options(selectinload(Comment.owner))
        .order_by(Comment.created_at.asc())  # Show oldest comments first
    )

    result = await session.execute(query)
    comments = result.scalars().all()

    return comments


# === 7. Create Comment (Verified Users) ===
@router.post(
    "/{post_id}/comments/",
    response_model=CommentReadWithUser,
    status_code=status.HTTP_201_CREATED,
    tags=["Posts", "Comments"],  # Added tag for organization
)
async def create_comment_for_post(
    post_id: int,
    comment: CommentCreate,
    user: User = Depends(current_active_verified_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new comment. The user must be authenticated AND VERIFIED.
    """
    # Check if post exists (you already had this, which is great)
    post_result = await session.execute(select(Post).where(Post.id == post_id))
    if post_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    new_comment = Comment(**comment.model_dump(), owner_id=user.id, post_id=post_id)
    session.add(new_comment)
    await session.commit()
    await session.refresh(new_comment)

    # We need to refresh the comment AND its relationships to return them
    result = await session.execute(
        select(Comment)
        .where(Comment.id == new_comment.id)
        .options(selectinload(Comment.owner))
    )
    new_comment_with_owner = result.scalar_one()

    return new_comment_with_owner
