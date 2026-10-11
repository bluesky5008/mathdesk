"""portal accounts (DCR-024, ADR-014)

Revision ID: a1c3e5f7b9d2
Revises: f7d1a5c9e3b6
Create Date: 2026-10-11 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c3e5f7b9d2'
down_revision: Union[str, Sequence[str], None] = 'f7d1a5c9e3b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 역할 열거형은 VARCHAR(8)+검증(제약 없음)이라 값 추가는 스키마 변경이 필요 없다
    op.add_column('app_user', sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        'app_user_student',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('guardian_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name='app_user_student_user_id_fkey'),
        sa.ForeignKeyConstraint(['student_id'], ['student.id'], name='app_user_student_student_id_fkey'),
        sa.ForeignKeyConstraint(
            ['guardian_id'], ['guardian.id'], name='app_user_student_guardian_id_fkey', ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('user_id', 'student_id'),
    )
    op.create_index('ix_app_user_student_student_id', 'app_user_student', ['student_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_app_user_student_student_id', table_name='app_user_student')
    op.drop_table('app_user_student')
    # 포털 계정은 되돌린 스키마에서 의미가 없다 — 세션·캠퍼스 연결과 함께 지운다
    op.execute(
        "DELETE FROM user_session WHERE user_id IN (SELECT id FROM app_user WHERE role IN ('student', 'guardian'))"
    )
    op.execute(
        "DELETE FROM app_user_campus WHERE user_id IN (SELECT id FROM app_user WHERE role IN ('student', 'guardian'))"
    )
    op.execute(
        "UPDATE audit_log SET actor_id = NULL WHERE actor_id IN (SELECT id FROM app_user WHERE role IN ('student', 'guardian'))"
    )
    op.execute("DELETE FROM app_user WHERE role IN ('student', 'guardian')")
    op.drop_column('app_user', 'issued_at')
