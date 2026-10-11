"""school table and student.school_id (DCR-015)

Revision ID: d5b9f3a7c2e4
Revises: c4a8e2f6b1d3
Create Date: 2026-10-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5b9f3a7c2e4'
down_revision: Union[str, Sequence[str], None] = 'c4a8e2f6b1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'school',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campus_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['campus_id'], ['campus.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campus_id', 'name'),
    )
    op.create_index(op.f('ix_school_campus_id'), 'school', ['campus_id'], unique=False)
    op.add_column('student', sa.Column('school_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_student_school_id'), 'student', ['school_id'], unique=False)
    op.create_foreign_key(
        'student_school_id_fkey', 'student', 'school', ['school_id'], ['id'], ondelete='SET NULL'
    )
    # 기존 학교 텍스트를 캠퍼스별 학교로 옮긴다 — 앞뒤 공백을 지우고 빈 값은 비운다
    op.execute(
        "INSERT INTO school (campus_id, name) "
        "SELECT DISTINCT campus_id, btrim(school) FROM student WHERE btrim(school) <> ''"
    )
    op.execute(
        "UPDATE student SET school_id = school.id FROM school "
        "WHERE school.campus_id = student.campus_id AND school.name = btrim(student.school)"
    )
    op.drop_column('student', 'school')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('student', sa.Column('school', sa.String(length=100), nullable=True))
    op.execute("UPDATE student SET school = school.name FROM school WHERE school.id = student.school_id")
    op.drop_constraint('student_school_id_fkey', 'student', type_='foreignkey')
    op.drop_index(op.f('ix_student_school_id'), table_name='student')
    op.drop_column('student', 'school_id')
    op.drop_index(op.f('ix_school_campus_id'), table_name='school')
    op.drop_table('school')
