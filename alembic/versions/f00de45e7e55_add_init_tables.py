"""add init tables

Revision ID: f00de45e7e55
Revises: 
Create Date: 2022-07-12 15:04:06.544859+00:00

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "f00de45e7e55"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "retry_task",
        sa.Column("retry_task_id", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("request_data", sa.String(), nullable=False),
        sa.Column("journey_type", sa.String(), nullable=False),
        sa.Column("message_uid", sa.String(), nullable=False),
        sa.Column("scheme_account_id", sa.Integer(), nullable=False),
        sa.Column("scheme_identifier", sa.String(), nullable=False),
        sa.Column("next_attempt_time", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "RETRYING",
                "FAILED",
                "SUCCESS",
                "WAITING",
                "CANCELLED",
                "REQUEUED",
                name="retrytaskstatuses",
            ),
            nullable=False,
        ),
        sa.Column("callback_retries", sa.Integer(), nullable=False),
        sa.Column(
            "callback_status",
            sa.Enum("NO_CALLBACK", "COMPLETE", "RETRYING", "PENDING", "FAILED", name="callbackstatuses"),
            nullable=False,
        ),
        sa.Column("audit_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("retry_task_id"),
        sa.UniqueConstraint("message_uid"),
        sa.UniqueConstraint("scheme_account_id"),
    )
    op.create_index(op.f("ix_retry_task_callback_status"), "retry_task", ["callback_status"], unique=False)
    op.create_index(op.f("ix_retry_task_status"), "retry_task", ["status"], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_retry_task_status"), table_name="retry_task")
    op.drop_index(op.f("ix_retry_task_callback_status"), table_name="retry_task")
    op.drop_table("retry_task")
    # ### end Alembic commands ###
