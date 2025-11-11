import uuid
from datetime import datetime
from typing import List

from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate
from pydantic import BaseModel, EmailStr

# ====================================================================
# User Schemas
# ====================================================================


class UserCreate(BaseUserCreate):
    """
    Schema for creating a new user.
    Inherits email and password fields from BaseUserCreate.
    """

    email: EmailStr
    password: str
    full_name: str | None = None


class UserUpdate(BaseUserUpdate):
    """
    Schema for updating user profile. All fields are optional.
    """

    full_name: str | None = None


class UserRead(BaseUser):
    """
    Schema for reading user data (what's returned from the API).
    Inherits fields from BaseUser.
    """

    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None

    class Config:
        from_attributes = True  # Tell Pydantic to read from ORM models


# ====================================================================
# Comment Schemas
# ====================================================================


class CommentBase(BaseModel):
    """Base schema for a comment, just the content."""

    content: str


class CommentCreate(CommentBase):
    """Schema for creating a new comment."""

    pass


# --- 👇 ADD THIS NEW SCHEMA ---
class CommentUpdate(BaseModel):
    """
    Schema for updating a comment. Content is optional.
    """

    content: str | None = None


class CommentRead(CommentBase):
    """Schema for reading a comment from the API."""

    id: int
    owner_id: uuid.UUID
    post_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentReadWithUser(CommentRead):
    """
    Schema for reading a comment, including the user who wrote it.
    This "nests" the UserRead schema inside.
    """

    owner: UserRead


# ====================================================================
# Post Schemas
# ====================================================================


class PostBase(BaseModel):
    """Base schema for a post, with common fields."""

    title: str
    content: str | None = None
    image_url: str | None = None
    video_url: str | None = None


class PostCreate(PostBase):
    """Schema for creating a new post."""

    pass


# --- ADD THIS NEW SCHEMA ---
class PostUpdate(BaseModel):
    """
    Schema for updating a post. All fields are optional.
    """

    title: str | None = None
    content: str | None = None
    image_url: str | None = None
    video_url: str | None = None


class PostRead(PostBase):
    """Schema for reading a post from the API (without details)."""

    id: int
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostReadWithDetails(PostRead):
    """
    Schema for reading a single post with all details:
    - The post owner's info (a nested UserRead schema)
    - A list of all comments (a nested list of CommentReadWithUser schemas)
    """

    owner: UserRead
    comments: List[CommentReadWithUser] = []
