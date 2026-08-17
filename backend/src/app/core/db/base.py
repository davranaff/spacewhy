"""Declarative base for future module-owned ORM models."""

from sqlalchemy.orm import DeclarativeBase

from app.core.db.metadata import metadata


class Base(DeclarativeBase):
    """Use the shared naming convention without creating a business table."""

    metadata = metadata
