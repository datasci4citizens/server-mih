"""APIS junta

Revision ID: 8564f51fecb8
Revises: 
Create Date: 2024-11-23 10:03:17.625137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8564f51fecb8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column('user', sa.Column('role', sa.Enum('responsible', 'specialist', name='userrole'), nullable=True))

def downgrade():
    op.drop_column('user', 'role')
