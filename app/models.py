from datetime import datetime
from enum import Enum

import sqlalchemy as s
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import String

from app.db import Base


class CallbackStatuses(Enum):
    NO_CALLBACK = "no_callback"
    COMPLETE = "complete"
    RETRYING = "retrying"
    PENDING = "pending"
    FAILED = "failed"


class RetryTaskStatuses(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RETRYING = "retrying"
    FAILED = "failed"
    SUCCESS = "success"
    WAITING = "waiting"
    CANCELLED = "cancelled"
    REQUEUED = "requeued"


class RetryTask(Base):
    __tablename__ = "retry_task"
    retry_task_id = s.Column(s.Integer, primary_key=True)
    attempts = s.Column(s.Integer, default=0, nullable=False)
    request_data = s.Column(String, nullable=False)
    journey_type = s.Column(String, nullable=False)
    message_uid = s.Column(String, nullable=False, unique=True)
    scheme_account_id = s.Column(s.Integer, nullable=False, unique=True)
    scheme_identifier = s.Column(String, nullable=False)
    next_attempt_time = s.Column(s.DateTime, nullable=True)
    status = s.Column(s.Enum(RetryTaskStatuses), nullable=False, default=RetryTaskStatuses.PENDING, index=True)
    callback_retries = s.Column(s.Integer, nullable=False, default=0)
    callback_status = s.Column(
        s.Enum(CallbackStatuses), nullable=False, default=CallbackStatuses.NO_CALLBACK, index=True
    )
    audit_data = s.Column(MutableList.as_mutable(JSONB), nullable=False, default=s.text("'[]'::jsonb"))

    def update_task(
        self,
        db_session: Session,
        response_audit: dict = None,
        status: RetryTaskStatuses = None,
        next_attempt_time: datetime = None,
        increase_attempts: bool = None,
        clear_next_attempt_time: bool = False,
        clear_attempts: bool = None,
        increase_callback_retries: bool = None,
        callback_status: CallbackStatuses = None,
    ):
        if response_audit:
            self.audit_data.append(response_audit)

        if status:
            self.status = status

        if increase_attempts:
            self.attempts += 1

        if clear_attempts:
            self.attempts = 0

        if clear_next_attempt_time or next_attempt_time is not None:
            self.next_attempt_time = next_attempt_time

        if increase_callback_retries:
            self.callback_retries += 1

        if callback_status:
            self.callback_status = callback_status

        db_session.commit()
