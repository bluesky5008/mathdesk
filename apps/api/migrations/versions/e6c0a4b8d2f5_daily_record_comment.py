"""student_daily_record comment (DCR-017)

Revision ID: e6c0a4b8d2f5
Revises: d5b9f3a7c2e4
Create Date: 2026-10-11 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6c0a4b8d2f5'
down_revision: Union[str, Sequence[str], None] = 'd5b9f3a7c2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('student_daily_record', sa.Column('comment', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('student_daily_record', 'comment')
