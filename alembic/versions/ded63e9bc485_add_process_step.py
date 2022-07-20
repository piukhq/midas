"""add_process_step

Revision ID: ded63e9bc485
Revises: c9e4d6c7c629
Create Date: 2022-07-20 17:34:17.842902+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ded63e9bc485"
down_revision = "c9e4d6c7c629"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("retry_task", sa.Column("process_step", sa.String(), nullable=True, server_default=None))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("retry_task", "process_step")
    # ### end Alembic commands ###
