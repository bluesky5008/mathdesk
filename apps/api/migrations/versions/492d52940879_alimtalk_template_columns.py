"""alimtalk template columns

Revision ID: 492d52940879
Revises: 980c6aafb97c
Create Date: 2026-09-24 12:30:29.080484

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '492d52940879'
down_revision: Union[str, Sequence[str], None] = '980c6aafb97c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """알림톡 템플릿 코드와 변수 매핑(FR-37). 기존 행에는 영향이 없는 nullable 추가다."""
    op.add_column('message_template', sa.Column('code', sa.String(length=50), nullable=True))
    op.add_column('message_template', sa.Column('variables', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('message_template', 'variables')
    op.drop_column('message_template', 'code')
