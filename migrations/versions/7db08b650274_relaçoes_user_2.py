"""Relaçoes user 2

Revision ID: 7db08b650274
Revises: 3b76654301d3
Create Date: 2024-10-14 09:01:01.560325

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '7db08b650274'
down_revision: Union[str, None] = '3b76654301d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mih', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'mih', 'user', ['user_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'mih', type_='foreignkey')
    op.drop_column('mih', 'user_id')
    # ### end Alembic commands ###
