from sqladmin import ModelView

from .models import Comment, Post, User


class UserAdmin(ModelView, model=User):
    """
    Configuration for the User model in the admin panel.
    """

    column_list = [User.id, User.email, User.full_name, User.is_superuser]
    column_searchable_list = [User.email, User.full_name]

    # Format fields in the detail view
    column_details_formatters = {
        User.id: lambda m, a: f"UUID: {str(m.id)[:8]}...",  # Show truncated UUID
        User.is_superuser: lambda m, a: "✅ Yes" if m.is_superuser else "❌ No",
        User.is_active: lambda m, a: "🟢 Active" if m.is_active else "🔴 Inactive",
    }

    icon = "fa-solid fa-user"


class PostAdmin(ModelView, model=Post):
    """
    Configuration for the Post model in the admin panel.
    """

    column_list = [Post.id, Post.title, Post.owner, Post.created_at]
    column_searchable_list = [Post.title, Post.content]

    # Format in list view
    column_formatters = {
        Post.owner: lambda m, a: m.owner.email if m.owner else "No owner",
    }

    # Format in detail view
    column_details_formatters = {
        Post.content: lambda m, a: (
            m.content[:100] + "..." if m.content and len(m.content) > 100 else m.content
        ),
        Post.owner: lambda m, a: (
            f"{m.owner.email} ({m.owner.full_name})" if m.owner else "No owner"
        ),
        Post.created_at: lambda m, a: m.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }

    icon = "fa-solid fa-file-lines"


class CommentAdmin(ModelView, model=Comment):
    """
    Configuration for the Comment model in the admin panel.
    """

    column_list = [Comment.id, Comment.post_id, Comment.owner, Comment.created_at]

    column_formatters = {
        Comment.owner: lambda m, a: m.owner.email if m.owner else "",
    }

    # Format in detail view
    column_details_formatters = {
        Comment.owner: lambda m, a: f"👤 {m.owner.email}" if m.owner else "Unknown",
        Comment.post: lambda m, a: f"📝 {m.post.title}" if m.post else "No post",
    }

    icon = "fa-solid fa-comment"
