"""Novas definições user

Revision ID: 6b56377088e6
Revises: 884ab1ed8a4d
Create Date: 2024-10-04 16:28:06.698606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6b56377088e6'
down_revision: Union[str, None] = '884ab1ed8a4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'birthday')
    op.drop_column('user', 'email')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('email', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('birthday', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
