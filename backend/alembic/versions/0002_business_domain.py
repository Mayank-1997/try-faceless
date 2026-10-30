"""Add business domain tables (projects, workflows, research, scripts, storyboards, scenes, assets, generation_jobs, prompt_executions, cost_records, token_usage_records)

Revision ID: 0002_business_domain
Revises: None
Create Date: 2026-07-19 16:40:00.000000

Creates all Phase 3 business domain tables for the AI Video Studio.
Depends on the auth tables (users) from the initial migration.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_business_domain"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("language", sa.String(10), server_default="en", nullable=False),
        sa.Column("audience", sa.Text(), server_default="", nullable=False),
        sa.Column("content_type", sa.String(50), server_default="youtube_video", nullable=False),
        sa.Column("video_style", sa.String(50), server_default="mixed", nullable=False),
        sa.Column("target_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("current_step", sa.String(50), server_default="initialization", nullable=False),
        sa.Column("tags", sa.Text(), server_default="", nullable=False),
        sa.Column("metadata", sa.Text(), server_default="{}", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_content_type", "projects", ["content_type"])
    op.create_index("ix_projects_current_step", "projects", ["current_step"])
    op.create_index("ix_projects_created_at", "projects", ["created_at"])

    # --- workflows ---
    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("current_step", sa.String(50), server_default="initialization", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_time_seconds", sa.Float(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("checkpoint_ref", sa.String(500), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflows_project_id", "workflows", ["project_id"])
    op.create_index("ix_workflows_status", "workflows", ["status"])
    op.create_index("ix_workflows_current_step", "workflows", ["current_step"])

    # --- research ---
    op.create_table(
        "research",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("timeline", sa.Text(), server_default="", nullable=False),
        sa.Column("interesting_facts", sa.Text(), server_default="", nullable=False),
        sa.Column("sources", sa.Text(), server_default="", nullable=False),
        sa.Column("keywords", sa.Text(), server_default="", nullable=False),
        sa.Column("references", sa.Text(), server_default="", nullable=False),
        sa.Column("statistics", sa.Text(), server_default="{}", nullable=False),
        sa.Column("audience_pain_points", sa.Text(), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_project_id", "research", ["project_id"])
    op.create_index("ix_research_version", "research", ["version"])
    op.create_index("ix_research_status", "research", ["status"])

    # --- scripts ---
    op.create_table(
        "scripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("hook", sa.Text(), server_default="", nullable=False),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("cta", sa.Text(), server_default="", nullable=False),
        sa.Column("word_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_duration_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("language", sa.String(10), server_default="en", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scripts_project_id", "scripts", ["project_id"])
    op.create_index("ix_scripts_version", "scripts", ["version"])
    op.create_index("ix_scripts_status", "scripts", ["status"])

    # --- storyboards ---
    op.create_table(
        "storyboards",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("scene_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_duration_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("style", sa.String(50), server_default="mixed", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("narrative_structure", sa.Text(), server_default="", nullable=False),
        sa.Column("pacing_notes", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_storyboards_project_id", "storyboards", ["project_id"])
    op.create_index("ix_storyboards_version", "storyboards", ["version"])
    op.create_index("ix_storyboards_status", "storyboards", ["status"])

    # --- scenes ---
    op.create_table(
        "scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storyboard_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storyboards.id", ondelete="SET NULL"), nullable=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scene_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), server_default="", nullable=False),
        sa.Column("duration_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("narration", sa.Text(), server_default="", nullable=False),
        sa.Column("importance_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("emotion", sa.String(50), server_default="", nullable=False),
        sa.Column("visual_type", sa.String(30), server_default="image", nullable=False),
        sa.Column("camera_angle", sa.String(30), nullable=True),
        sa.Column("camera_motion", sa.String(30), nullable=True),
        sa.Column("lens", sa.String(100), nullable=True),
        sa.Column("lighting", sa.String(200), nullable=True),
        sa.Column("composition", sa.String(200), nullable=True),
        sa.Column("transition", sa.String(30), nullable=True),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("voice_timing", sa.Text(), server_default="{}", nullable=False),
        sa.Column("background_music", sa.String(200), nullable=True),
        sa.Column("sound_effects", sa.Text(), server_default="", nullable=False),
        sa.Column("generation_status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("review_status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenes_project_id", "scenes", ["project_id"])
    op.create_index("ix_scenes_storyboard_id", "scenes", ["storyboard_id"])
    op.create_index("ix_scenes_scene_number", "scenes", ["scene_number"])
    op.create_index("ix_scenes_generation_status", "scenes", ["generation_status"])
    op.create_index("ix_scenes_review_status", "scenes", ["review_status"])

    # --- assets (single-table inheritance) ---
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_type", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(50), server_default="", nullable=False),
        sa.Column("prompt_version", sa.String(50), server_default="", nullable=False),
        sa.Column("generation_cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("generation_time_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("generation_status", sa.String(30), server_default="planned", nullable=False),
        sa.Column("storage_type", sa.String(20), server_default="local", nullable=False),
        sa.Column("storage_ref", sa.Text(), server_default="", nullable=False),
        sa.Column("metadata", sa.Text(), server_default="{}", nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Asset-specific columns (nullable, used by subclasses via single-table inheritance)
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(10), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("fps", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("voice_name", sa.String(100), nullable=True),
        sa.Column("speaking_rate", sa.Float(), nullable=True),
        sa.Column("pitch", sa.Float(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_project_id", "assets", ["project_id"])
    op.create_index("ix_assets_scene_id", "assets", ["scene_id"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])
    op.create_index("ix_assets_generation_status", "assets", ["generation_status"])
    op.create_index("ix_assets_created_at", "assets", ["created_at"])

    # --- generation_jobs ---
    op.create_table(
        "generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("priority", sa.String(20), server_default="normal", nullable=False),
        sa.Column("payload", sa.Text(), server_default="{}", nullable=False),
        sa.Column("result", sa.Text(), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_time_seconds", sa.Float(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generation_jobs_project_id", "generation_jobs", ["project_id"])
    op.create_index("ix_generation_jobs_workflow_id", "generation_jobs", ["workflow_id"])
    op.create_index("ix_generation_jobs_scene_id", "generation_jobs", ["scene_id"])
    op.create_index("ix_generation_jobs_job_type", "generation_jobs", ["job_type"])
    op.create_index("ix_generation_jobs_status", "generation_jobs", ["status"])
    op.create_index("ix_generation_jobs_priority", "generation_jobs", ["priority"])
    op.create_index("ix_generation_jobs_queued_at", "generation_jobs", ["queued_at"])

    # --- prompt_executions ---
    op.create_table(
        "prompt_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_type", sa.String(50), server_default="", nullable=False),
        sa.Column("prompt_template", sa.String(200), server_default="", nullable=False),
        sa.Column("prompt_variables", sa.Text(), server_default="{}", nullable=False),
        sa.Column("rendered_prompt", sa.Text(), server_default="", nullable=False),
        sa.Column("provider", sa.String(50), server_default="", nullable=False),
        sa.Column("model", sa.String(100), server_default="", nullable=False),
        sa.Column("temperature", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("response", sa.Text(), server_default="", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cached_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_executions_project_id", "prompt_executions", ["project_id"])
    op.create_index("ix_prompt_executions_workflow_id", "prompt_executions", ["workflow_id"])
    op.create_index("ix_prompt_executions_scene_id", "prompt_executions", ["scene_id"])
    op.create_index("ix_prompt_executions_provider", "prompt_executions", ["provider"])
    op.create_index("ix_prompt_executions_status", "prompt_executions", ["status"])
    op.create_index("ix_prompt_executions_created_at", "prompt_executions", ["created_at"])

    # --- cost_records ---
    op.create_table(
        "cost_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(50), server_default="", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("cost_category", sa.String(30), server_default="llm", nullable=False),
        sa.Column("period", sa.String(20), server_default="daily", nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.Text(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cost_records_user_id", "cost_records", ["user_id"])
    op.create_index("ix_cost_records_project_id", "cost_records", ["project_id"])
    op.create_index("ix_cost_records_workflow_id", "cost_records", ["workflow_id"])
    op.create_index("ix_cost_records_job_id", "cost_records", ["job_id"])
    op.create_index("ix_cost_records_scene_id", "cost_records", ["scene_id"])
    op.create_index("ix_cost_records_asset_id", "cost_records", ["asset_id"])
    op.create_index("ix_cost_records_provider", "cost_records", ["provider"])
    op.create_index("ix_cost_records_cost_category", "cost_records", ["cost_category"])
    op.create_index("ix_cost_records_period", "cost_records", ["period"])
    op.create_index("ix_cost_records_created_at", "cost_records", ["created_at"])

    # --- token_usage_records ---
    op.create_table(
        "token_usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(50), server_default="", nullable=False),
        sa.Column("agent_type", sa.String(50), server_default="", nullable=False),
        sa.Column("model", sa.String(100), server_default="", nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cached_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata", sa.Text(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_token_usage_user_id", "token_usage_records", ["user_id"])
    op.create_index("ix_token_usage_project_id", "token_usage_records", ["project_id"])
    op.create_index("ix_token_usage_workflow_id", "token_usage_records", ["workflow_id"])
    op.create_index("ix_token_usage_provider", "token_usage_records", ["provider"])
    op.create_index("ix_token_usage_agent_type", "token_usage_records", ["agent_type"])
    op.create_index("ix_token_usage_created_at", "token_usage_records", ["created_at"])


def downgrade() -> None:
    op.drop_table("token_usage_records")
    op.drop_table("cost_records")
    op.drop_table("prompt_executions")
    op.drop_table("generation_jobs")
    op.drop_table("assets")
    op.drop_table("scenes")
    op.drop_table("storyboards")
    op.drop_table("scripts")
    op.drop_table("research")
    op.drop_table("workflows")
    op.drop_table("projects")
