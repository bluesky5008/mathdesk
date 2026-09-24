"""class schedule end time optional

Revision ID: 52183a89ef87
Revises: 492d52940879
Create Date: 2026-09-24 21:36:43.527509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52183a89ef87'
down_revision: Union[str, Sequence[str], None] = '492d52940879'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """시간표는 요일·시작 시각만 입력한다(FR-07, DCR-007). 기존 종료 시각은 그대로 둔다."""
    op.alter_column('class_schedule', 'end_time', existing_type=sa.Time(), nullable=True)


def downgrade() -> None:
    """비어 있는 종료 시각을 시작 시각으로 채운 뒤 필수로 되돌린다."""
    op.execute("UPDATE class_schedule SET end_time = start_time WHERE end_time IS NULL")
    op.alter_column('class_schedule', 'end_time', existing_type=sa.Time(), nullable=False)
