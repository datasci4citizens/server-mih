"""Novas colunas

Revision ID: 884ab1ed8a4d
Revises: bef7fcc9d17d
Create Date: 2024-10-04 15:19:48.116651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '884ab1ed8a4d'
down_revision: Union[str, None] = 'bef7fcc9d17d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('patients', sa.Column('highFever', sa.Boolean(), nullable=True))
    op.add_column('patients', sa.Column('premature', sa.Boolean(), nullable=True))
    op.add_column('patients', sa.Column('deliveryProblems', sa.Boolean(), nullable=True))
    op.add_column('patients', sa.Column('lowWeight', sa.Boolean(), nullable=True))
    op.add_column('patients', sa.Column('deliveryType', sa.Integer(), nullable=True))
    op.add_column('patients', sa.Column('brothersNumber', sa.Integer(), nullable=True))
    op.add_column('patients', sa.Column('consultDentist', sa.Boolean(), nullable=True))
    op.add_column('patients', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'patients', 'user', ['user_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'patients', type_='foreignkey')
    op.drop_column('patients', 'user_id')
    op.drop_column('patients', 'consultDentist')
    op.drop_column('patients', 'brothersNumber')
    op.drop_column('patients', 'deliveryType')
    op.drop_column('patients', 'lowWeight')
    op.drop_column('patients', 'deliveryProblems')
    op.drop_column('patients', 'premature')
    op.drop_column('patients', 'highFever')
    # ### end Alembic commands ###
