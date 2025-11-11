import uuid
from datetime import datetime

from app.database import Base
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"  # Explicit table name for clarity
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # --- Add Relationships ---
    # One user can have many posts
    posts: Mapped[list["Post"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    # One user can have many comments
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


# --- New Post Model ---
class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Foreign Key to User
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    # Relationship back to User
    owner: Mapped["User"] = relationship(back_populates="posts")

    # Relationship to Comments
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


# --- New Comment Model ---
class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Foreign Key to User (who wrote the comment)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # Foreign Key to Post (which post it's on)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"))

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="comments")
    post: Mapped["Post"] = relationship(back_populates="comments")
