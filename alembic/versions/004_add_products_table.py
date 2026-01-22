"""add_products_table

Revision ID: 004_add_products
Revises: 003_add_agent_tools
Create Date: 2026-01-21 07:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_add_products"
down_revision = "003_add_agent_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create products table for caching e-commerce products."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "products" not in inspector.get_table_names():
        op.create_table(
            "products",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("agent_tool_id", sa.UUID(), nullable=False),
            sa.Column("external_id", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("long_description", sa.Text(), nullable=True),
            sa.Column("price", sa.String(length=50), nullable=True),
            sa.Column("currency", sa.String(length=10), nullable=True),
            sa.Column("category", sa.String(length=255), nullable=True),
            sa.Column("sku", sa.String(length=100), nullable=True),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("image_url", sa.Text(), nullable=True),
            sa.Column("in_stock", sa.Boolean(), nullable=True, server_default="true"),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("rag_indexed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("rag_indexed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("qdrant_point_id", sa.String(length=100), nullable=True),
            sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["agent_tool_id"], ["agent_tools.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    # Create indexes
    try:
        op.create_index("idx_products_agent_tool_id", "products", ["agent_tool_id"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("idx_products_external_id", "products", ["agent_tool_id", "external_id"], unique=True)
    except Exception:
        pass

    try:
        op.create_index("idx_products_rag_indexed", "products", ["rag_indexed"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("idx_products_content_hash", "products", ["content_hash"], unique=False)
    except Exception:
        pass

    try:
        op.create_index("idx_products_updated_at", "products", ["updated_at"], unique=False)
    except Exception:
        pass


def downgrade() -> None:
    """Drop products table."""
    op.drop_index("idx_products_updated_at", table_name="products")
    op.drop_index("idx_products_content_hash", table_name="products")
    op.drop_index("idx_products_rag_indexed", table_name="products")
    op.drop_index("idx_products_external_id", table_name="products")
    op.drop_index("idx_products_agent_tool_id", table_name="products")
    op.drop_table("products")
