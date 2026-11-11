"""daily record extra fields (DCR-028)

Revision ID: a8e2b6d0f4c7
Revises: a1c3e5f7b9d2
Create Date: 2026-11-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a8e2b6d0f4c7'
down_revision: Union[str, Sequence[str], None] = 'a1c3e5f7b9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'student_daily_record',
        sa.Column('extra', postgresql.JSONB(), server_default='{}', nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('student_daily_record', 'extra')
