import typing as t
from datetime import datetime, timedelta, timezone
from functools import wraps

import rq
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from app import db
from app.models import RetryTask, RetryTaskStatuses
from settings import DEFAULT_FAILURE_TTL


def create_task(
    db_session: Session,
    user_info: dict,
    journey_type: str,
    message_uid: str,
    scheme_identifier: str,
    scheme_account_id: str,
) -> RetryTask:
    retry_task = RetryTask(
        request_data=user_info,
        journey_type=journey_type,
        message_uid=message_uid,
        scheme_identifier=scheme_identifier,
        scheme_account_id=scheme_account_id,
    )
    db_session.add(retry_task)
    db_session.flush()
    return retry_task


def get_task(db_session: Session, scheme_account_id: str) -> RetryTask:
    return (
        db_session.execute(select(RetryTask).where(RetryTask.scheme_account_id == scheme_account_id))
        .unique()
        .scalar_one()
    )


def delete_task(db_session: Session, retry_task: RetryTask):
    db_session.delete(retry_task)
    db_session.commit()


def update_task_for_retry(
    db_session: Session,
    retry_task: RetryTask,
    retry_status: str,
    next_attempt_time: t.Optional[datetime],
):
    retry_task.attempts += 1
    retry_task.status = retry_status
    retry_task.next_attempt_time = next_attempt_time  # type: ignore
    db_session.flush()
    db_session.commit()


def reset_task_for_callback_attempt(
    db_session: Session,
    retry_task: RetryTask,
    retry_status: str,
    next_attempt_time: datetime,
):
    retry_task.callback_retries += 1
    retry_task.attempts = 0
    retry_task.status = retry_status
    retry_task.next_attempt_time = (next_attempt_time,)  # type: ignore
    db_session.add(retry_task)
    db_session.commit()
    return retry_task


def update_callback_attempt(db_session: Session, retry_task: RetryTask, next_attempt_time: datetime):
    retry_task.callback_retries += 1
    retry_task.next_attempt_time = next_attempt_time
    db_session.add(retry_task)
    db_session.commit()
    return retry_task


def fail_callback_task(db_session: Session, retry_task: RetryTask):
    retry_task.status = t.cast(str, RetryTaskStatuses.FAILED)
    db_session.add(retry_task)
    db_session.commit()
    return retry_task


def enqueue_retry_task_delay(*, connection: t.Any, retry_task: RetryTask, delay_seconds: float):
    q = rq.Queue("midas-retry", connection=connection)
    next_attempt_time = datetime.now(tz=timezone.utc) + timedelta(seconds=delay_seconds)
    q.enqueue_at(
        next_attempt_time,
        "app.journeys.join.attempt_join",
        args=[
            retry_task.scheme_account_id,
            retry_task.message_uid,
            retry_task.scheme_identifier,
            retry_task.request_data,
        ],
        failure_ttl=DEFAULT_FAILURE_TTL,
        at_front=False,
    )
    return next_attempt_time


# this one
def enqueue_retry_task(*, connection: t.Any, function_path: str, args: list) -> rq.job.Job:
    q = rq.Queue("midas-retry", connection=connection)
    job = q.enqueue(
        function_path,
        args=args,
        failure_ttl=DEFAULT_FAILURE_TTL,
        at_front=False,
    )
    return job


def view_session(f: t.Callable) -> t.Callable:
    """A flask view decorator that creates a database session for use by the wrapped view."""

    @wraps(f)
    def create_view_session(*args, **kwargs):
        with db.session_scope() as session:
            return f(*args, session=session, **kwargs)

    return create_view_session
