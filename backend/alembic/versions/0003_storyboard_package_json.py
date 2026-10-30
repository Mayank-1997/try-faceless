"""Add package_json to storyboards.

Revision ID: 0003_storyboard_package_json
Revises: 0002_business_domain
Create Date: 2026-08-06 00:00:00.000000

Stores the full StoryboardPackage JSON produced by the
StoryboardWorkflowGraph so the complete agent outputs are available
in the database and can be returned by the download endpoint.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_storyboard_package_json"
down_revision: Union[str, None] = "0002_business_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add package_json column to storyboards table."""
    op.add_column(
        "storyboards",
        sa.Column("package_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop package_json column from storyboards table."""
    op.drop_column("storyboards", "package_json")
