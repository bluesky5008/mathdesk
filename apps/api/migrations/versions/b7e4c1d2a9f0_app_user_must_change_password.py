"""app_user must_change_password

Revision ID: b7e4c1d2a9f0
Revises: 52183a89ef87
Create Date: 2026-09-24 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4c1d2a9f0'
down_revision: Union[str, Sequence[str], None] = '52183a89ef87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('app_user', sa.Column('must_change_password', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('app_user', 'must_change_password')
