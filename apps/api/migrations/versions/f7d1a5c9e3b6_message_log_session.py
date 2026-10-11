"""message_log session_id (DCR-023)

Revision ID: f7d1a5c9e3b6
Revises: e6c0a4b8d2f5
Create Date: 2026-10-11 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7d1a5c9e3b6'
down_revision: Union[str, Sequence[str], None] = 'e6c0a4b8d2f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('message_log', sa.Column('session_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'message_log_session_id_fkey', 'message_log', 'class_session', ['session_id'], ['id']
    )
    op.create_index('ix_message_log_session_id', 'message_log', ['session_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_message_log_session_id', table_name='message_log')
    op.drop_constraint('message_log_session_id_fkey', 'message_log', type_='foreignkey')
    op.drop_column('message_log', 'session_id')
