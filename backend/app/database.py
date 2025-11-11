from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from .config import get_settings

# Get the database URL from our settings
DATABASE_URL = get_settings().DATABASE_URL

# Create the async engine
# 'echo=True' is great for development, it logs all SQL queries
engine = create_async_engine(DATABASE_URL, echo=True)

# Create the session factory
# This is what we'll use to create new sessions
async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

# This is the base class all your models will inherit from
Base = declarative_base()


# This is the dependency we will use in our routes
async def get_db_session():
    """
    Dependency function to get an async database session.
    This ensures the session is always closed, even if an error occurs.
    """

    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
