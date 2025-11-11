import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context

# Third-party imports
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# --- FIX PYTHON PATH ---
# Add the parent directory (backend/) to sys.path so we can import app
current_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_path, ".."))
# -----------------------

# Local application imports
# We add noqa: E402 to tell Ruff to ignore this specific error,
# as this is the standard way to handle Alembic's env.py
# We add noqa: F401 because these imports ARE required for
# Base.metadata to be populated, even if they look unused.
from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402, F401
from app.models import Comment, Post, User  # noqa: E402, F401

# Alembic Config object
config = context.config

# Set DATABASE_URL from your settings
settings = get_settings()
if settings.DATABASE_URL:
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
else:
    raise ValueError("DATABASE_URL is not set in your .env file")


# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async support."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
