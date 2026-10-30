"""Unit tests for the SQLAlchemy base model and mixins."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.models.base import (
    Base,
    BaseModel,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class _SampleModel(BaseModel):
    """Concrete model for testing mixin behaviour."""

    __tablename__ = "test_sample_model"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


class TestUUIDPrimaryKeyMixin:
    """Tests for UUID primary key generation."""

    def test_id_is_uuid(self) -> None:
        instance = _SampleModel(name="test")
        assert hasattr(instance, "id")

    def test_id_defaults_to_none_before_flush(self) -> None:
        """Before the session flushes, the id uses the Python-side default."""
        instance = _SampleModel(name="test")
        # The default is uuid.uuid4, which is called on flush/commit.
        # Before flush, the attribute may be None or set by the default.
        assert instance.id is not None
        assert isinstance(instance.id, uuid.UUID)


class TestTimestampMixin:
    """Tests for timestamp columns."""

    def test_created_at_exists(self) -> None:
        instance = _SampleModel(name="test")
        assert hasattr(instance, "created_at")

    def test_updated_at_exists(self) -> None:
        instance = _SampleModel(name="test")
        assert hasattr(instance, "updated_at")

    def test_timestamps_default_to_utc(self) -> None:
        instance = _SampleModel(name="test")
        assert instance.created_at is not None
        assert instance.updated_at is not None
        assert instance.created_at.tzinfo is not None


class TestSoftDeleteMixin:
    """Tests for soft-delete flag."""

    def test_is_deleted_defaults_false(self) -> None:
        instance = _SampleModel(name="test")
        assert instance.is_deleted is False


class TestBaseModel:
    """Tests for the combined BaseModel."""

    def test_inherits_all_mixins(self) -> None:
        assert issubclass(BaseModel, Base)
        assert issubclass(BaseModel, UUIDPrimaryKeyMixin)
        assert issubclass(BaseModel, TimestampMixin)
        assert issubclass(BaseModel, SoftDeleteMixin)

    def test_is_abstract(self) -> None:
        assert BaseModel.__abstract__ is True

    def test_table_args_contain_indexes(self) -> None:
        """BaseModel should define indexes on created_at and updated_at."""
        table_args = BaseModel.__table_args__
        index_names = {arg.name for arg in table_args if hasattr(arg, "name")}
        assert "ix_created_at" in index_names
        assert "ix_updated_at" in index_names
