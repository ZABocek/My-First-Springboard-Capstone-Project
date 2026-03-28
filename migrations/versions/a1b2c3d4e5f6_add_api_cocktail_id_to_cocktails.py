"""add api_cocktail_id to cocktails

Revision ID: a1b2c3d4e5f6
Revises: 62f8c79f73d7
Create Date: 2026-03-28 00:00:00.000000

Adds the ``api_cocktail_id`` column to the ``cocktails`` table so that
shared API rows can be deduplicated using the stable ``idDrink`` value
from TheCocktailDB instead of relying on the drink name.

An index on ``api_cocktail_id`` is also created to keep the look-up fast.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '62f8c79f73d7'
branch_labels = None
depends_on = None


def upgrade():
    # Add the new column; nullable so existing rows are not broken.
    op.add_column(
        'cocktails',
        sa.Column('api_cocktail_id', sa.String(), nullable=True),
    )
    # Index speeds up the deduplication query in process_and_store_new_cocktail.
    op.create_index(
        'ix_cocktails_api_cocktail_id',
        'cocktails',
        ['api_cocktail_id'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_cocktails_api_cocktail_id', table_name='cocktails')
    op.drop_column('cocktails', 'api_cocktail_id')
