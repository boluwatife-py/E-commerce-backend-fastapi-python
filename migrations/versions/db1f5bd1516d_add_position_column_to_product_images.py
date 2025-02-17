"""add position column to product_images

Revision ID: db1f5bd1516d
Revises: 0727b62f964a
Create Date: 2025-02-15 12:50:16.886407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db1f5bd1516d'
down_revision: Union[str, None] = '0727b62f964a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('product_images', sa.Column('position', sa.Integer(), nullable=False))
    op.create_unique_constraint('unique_product_image_position', 'product_images', ['product_id', 'position'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('unique_product_image_position', 'product_images', type_='unique')
    op.drop_column('product_images', 'position')
    # ### end Alembic commands ###
