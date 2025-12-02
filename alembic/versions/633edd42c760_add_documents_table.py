"""add_documents_table

Revision ID: 633edd42c760
Revises: 962e5b26ffd2
Create Date: 2025-12-02 15:32:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '633edd42c760'
down_revision = '962e5b26ffd2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create documents table for tracking ingested documents."""
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rag_config_id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False),
        sa.Column('chunk_ids', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('namespace', sa.String(length=255), nullable=True),
        sa.Column('doc_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['rag_config_id'], ['rag_configs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_documents_rag_config', 'documents', ['rag_config_id'], unique=False)
    op.create_index('idx_documents_created_at', 'documents', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop documents table."""
    op.drop_index('idx_documents_created_at', table_name='documents')
    op.drop_index('idx_documents_rag_config', table_name='documents')
    op.drop_table('documents')