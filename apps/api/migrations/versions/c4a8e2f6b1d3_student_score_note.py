"""student score_note (DCR-014)

Revision ID: c4a8e2f6b1d3
Revises: b7e4c1d2a9f0
Create Date: 2026-10-11 13:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4a8e2f6b1d3'
down_revision: Union[str, Sequence[str], None] = 'b7e4c1d2a9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('student', sa.Column('score_note', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('student', 'score_note')
