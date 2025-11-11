# app/dependencies.py
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db_session
from .models import User


async def get_user_db(session: AsyncSession = Depends(get_db_session)):
    """
    Dependency to get the SQLAlchemyUserDatabase adapter.
    """
    yield SQLAlchemyUserDatabase(session, User)
