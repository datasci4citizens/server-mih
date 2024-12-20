
"""teste

Revision ID: ac20da2c0384
Revises: 
Create Date: 2024-11-28 16:25:26.431987

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'ac20da2c0384'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False))
    op.drop_column('user', 'personInCharge')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('personInCharge', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('user', 'name')
    # ### end Alembic commands ###
