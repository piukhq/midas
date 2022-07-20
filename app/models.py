from enum import Enum

import sqlalchemy as s
from sqlalchemy.sql import func

from app.db import Base


class RetryTaskStatuses(Enum):
    PENDING = "pending"
    RETRYING = "retrying"
    FAILED = "failed"
    SUCCESS = "success"


class RetryTask(Base):
    __tablename__ = "retry_task"
    id = s.Column(s.Integer, primary_key=True)
    time_created = s.Column(s.DateTime(timezone=True), server_default=func.now())
    time_updated = s.Column(s.DateTime(timezone=True), onupdate=func.now())
    attempts = s.Column(s.Integer, default=0, nullable=False)
    request_data = s.Column(s.JSON, nullable=False)
    journey_type = s.Column(s.String, nullable=False)
    message_uid = s.Column(s.String, nullable=False, unique=True)
    scheme_account_id = s.Column(s.Integer, nullable=False, unique=True)
    scheme_identifier = s.Column(s.String, nullable=False)
    next_attempt_time = s.Column(s.DateTime, nullable=True)
    status = s.Column(s.Enum(RetryTaskStatuses), nullable=False, default=RetryTaskStatuses.PENDING, index=True)
    callback_retries = s.Column(s.Integer, nullable=False, default=0)
    awaiting_callback = s.Column(s.Boolean, nullable=False, default=False)
    extra_data = s.Column(s.JSON, nullable=True, default={})
