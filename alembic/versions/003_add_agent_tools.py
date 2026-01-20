"""add_agent_tools_table

Revision ID: 003_add_agent_tools
Revises: 633edd42c760
Create Date: 2026-01-20 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_add_agent_tools"
down_revision = "633edd42c760"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create agent_tools table for linking agents to tools with integrations."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create agent_tools table - links agents to tools (defined in code) with specific integrations
    if "agent_tools" not in inspector.get_table_names():
        op.create_table(
            "agent_tools",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("agent_id", sa.UUID(), nullable=False),
            # Tool slug references static tool definitions in code (e.g., "product_search", "order_lookup")
            sa.Column("tool_slug", sa.String(length=100), nullable=False),
            # Integration slug references static integration classes (e.g., "wordpress", "shopify")
            sa.Column("integration_slug", sa.String(length=100), nullable=False),
            # Integration-specific configuration (API keys, URLs, etc.)
            sa.Column("integration_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            # Each agent can only have one configuration per tool
            sa.UniqueConstraint("agent_id", "tool_slug", name="uq_agent_tools_agent_tool"),
        )

    # Create indexes
    try:
        op.create_index("idx_agent_tools_agent_id", "agent_tools", ["agent_id"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("idx_agent_tools_tool_slug", "agent_tools", ["tool_slug"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("idx_agent_tools_is_enabled", "agent_tools", ["is_enabled"], unique=False)
    except Exception:
        pass


def downgrade() -> None:
    """Drop agent_tools table."""
    op.drop_index("idx_agent_tools_is_enabled", table_name="agent_tools")
    op.drop_index("idx_agent_tools_tool_slug", table_name="agent_tools")
    op.drop_index("idx_agent_tools_agent_id", table_name="agent_tools")
    op.drop_table("agent_tools")
