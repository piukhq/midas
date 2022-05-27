"""Add retry tables

Revision ID: 4b2f1f50633c
Revises: 
Create Date: 2022-05-09 12:28:18.931977+00:00

"""
from collections import namedtuple

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "4b2f1f50633c"
down_revision = None
branch_labels = None
depends_on = None

QUEUE_NAME = "midas-retry"

TaskTypeKeyData = namedtuple("TaskTypeKeyData", ["name", "type"])
TaskTypeData = namedtuple("TaskTypeData", ["name", "path", "error_handler_path", "keys"])
task_type_data = [
    TaskTypeData(
        name="attempt-join",
        path="app.journeys.join.attempt_join",
        error_handler_path="app.error_handler.handle_retry_task_request_error",
        keys=[
            TaskTypeKeyData(name="user_info", type="STRING"),
            TaskTypeKeyData(name="tid", type="STRING"),
            TaskTypeKeyData(name="scheme_slug", type="STRING"),
        ],
    )
]


def add_task_data(conn: sa.engine.Connection, metadata: sa.MetaData) -> None:
    TaskType = sa.Table("task_type", metadata, autoload_with=conn)
    TaskTypeKey = sa.Table("task_type_key", metadata, autoload_with=conn)
    for data in task_type_data:
        inserted_obj = conn.execute(
            TaskType.insert().values(
                name=data.name,
                path=data.path,
                error_handler_path=data.error_handler_path,
                queue_name=QUEUE_NAME,
            )
        )
        task_type_id = inserted_obj.inserted_primary_key[0]
        for key in data.keys:
            conn.execute(TaskTypeKey.insert().values(name=key.name, type=key.type, task_type_id=task_type_id))


def upgrade():
    metadata = sa.MetaData()
    conn = op.get_bind()
    op.create_table(
        "task_type",
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column("task_type_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("error_handler_path", sa.String(), nullable=False),
        sa.Column("queue_name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("task_type_id"),
    )
    op.create_index(op.f("ix_task_type_name"), "task_type", ["name"], unique=True)
    op.create_table(
        "retry_task",
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column("retry_task_id", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("audit_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("next_attempt_time", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "FAILED",
                "SUCCESS",
                "WAITING",
                "CANCELLED",
                "REQUEUED",
                name="retrytaskstatuses",
            ),
            nullable=False,
        ),
        sa.Column("task_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["task_type_id"], ["task_type.task_type_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("retry_task_id"),
    )
    op.create_table(
        "task_type_key",
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column("task_type_key_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "type", sa.Enum("STRING", "INTEGER", "FLOAT", "DATE", "DATETIME", name="taskparamskeytypes"), nullable=False
        ),
        sa.Column("task_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["task_type_id"], ["task_type.task_type_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_type_key_id"),
        sa.UniqueConstraint("name", "task_type_id", name="name_task_type_id_unq"),
    )
    op.create_table(
        "task_type_key_value",
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column("value", sa.String(), nullable=True),
        sa.Column("retry_task_id", sa.Integer(), nullable=False),
        sa.Column("task_type_key_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["retry_task_id"], ["retry_task.retry_task_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_type_key_id"], ["task_type_key.task_type_key_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("retry_task_id", "task_type_key_id"),
    )
    add_task_data(conn, metadata)


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("task_type_key_value")
    op.drop_table("task_type_key")
    op.drop_table("retry_task")
    op.drop_index(op.f("ix_task_type_name"), table_name="task_type")
    op.drop_table("task_type")
    # ### end Alembic commands ###
