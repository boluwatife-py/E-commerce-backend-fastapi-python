"""changed user profile to user data

Revision ID: 0392a8e4f015
Revises: a772392040ef
Create Date: 2025-02-19 09:44:09.162277

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0392a8e4f015'
down_revision: Union[str, None] = 'a772392040ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_data',
    sa.Column('profile_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('city', sa.String(length=50), nullable=True),
    sa.Column('state', sa.String(length=50), nullable=True),
    sa.Column('zip_code', sa.String(length=10), nullable=True),
    sa.Column('country', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('profile_id'),
    sa.UniqueConstraint('phone'),
    sa.UniqueConstraint('user_id')
    )
    op.drop_table('user_profiles')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_profiles',
    sa.Column('profile_id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('phone', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('address', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('city', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('state', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('zip_code', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
    sa.Column('country', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name='user_profiles_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('profile_id', name='user_profiles_pkey'),
    sa.UniqueConstraint('phone', name='user_profiles_phone_key'),
    sa.UniqueConstraint('user_id', name='user_profiles_user_id_key')
    )
    op.drop_table('user_data')
    # ### end Alembic commands ###
