import typing as t
import uuid
from typing import TYPE_CHECKING, Any

import rq
from sqlalchemy.orm.session import Session

from app import db
from app.db import redis_raw
from app.exceptions import (
    BaseError,
    EndSiteDownError,
    IPBlockedError,
    NotSentError,
    RetryLimitReachedError,
    ServiceConnectionError,
    StatusLoginFailedError,
    UnknownError,
)
from app.models import RetryTask, RetryTaskStatuses
from app.reporting import get_logger
from app.resources import decrypt_credentials
from app.retry_util import (
    create_task_with_delay,
    delete_task,
    enqueue_retry_task_delay,
    enqueue_retry_login_task_delay,
    fail_callback_task,
    get_task,
    reset_task_for_callback_attempt,
    update_callback_attempt,
    update_task_for_retry,
)
from app.scheme_account import update_pending_join_account
from settings import MAX_CALLBACK_RETRY_COUNT, MAX_RETRY_COUNT, RETRY_BACKOFF_BASE

if TYPE_CHECKING:  # pragma: no cover
    from inspect import Traceback

logger = get_logger("retry-queue")


def handle_failed_join(db_session, retry_task, exc_value):
    consent_ids = None
    tid = retry_task.message_uid
    scheme_slug = retry_task.scheme_identifier
    user_info = retry_task.request_data
    user_info["credentials"] = decrypt_credentials(user_info["credentials"])
    consents = user_info["credentials"].get("consents", [])
    if consents:
        consent_ids = (consent["id"] for consent in consents)
    delete_task(db_session, retry_task)
    update_pending_join_account(
        user_info, tid, exc_value, scheme_slug=scheme_slug, consent_ids=consent_ids, raise_exception=False
    )


def handle_failed_login(self):
    try:
        with db.session_scope() as session:
            if self.retry_count > 0:
                task = get_task(session, scheme_account_id=self.user_info["scheme_account_id"])
                handle_request_exception(  # pragma: no cover
                    db_session=session,
                    backoff_base=RETRY_BACKOFF_BASE,
                    max_retries=MAX_RETRY_COUNT,
                    job=None,
                    exc_value=StatusLoginFailedError(),
                    connection=redis_raw,
                    retryable_exceptions=[
                        StatusLoginFailedError,  # type: ignore
                    ],
                    scheme_account_id=self.user_info["scheme_account_id"],
                )
                # if self.retry_count > MAX_RETRY_COUNT:
                #     task.status = RetryTaskStatuses.FAILED
            else:
                task = create_task_with_delay(
                    db_session=session,
                    user_info=self.user_info,
                    journey_type="attempt-login",
                    message_uid=str(uuid.uuid1()),
                    scheme_identifier="slim-chickens",
                    scheme_account_id=self.user_info["scheme_account_id"],
                )
                enqueue_retry_login_task_delay(
                    connection=redis_raw,
                    retry_task=task,
                    delay_seconds=60,
                    call_function = "app.journeys.join.login_and_publish_status"
                )
                session.commit()
    except BaseError as e:
        raise e


def retry_on_callback(db_session: Session, retry_task: RetryTask, error_code: list):
    subject = retry_task.journey_type
    attempts = retry_task.callback_retries + 1
    logger.debug(
        f"{subject} callback attempt {attempts}"
        f" failed for task: {retry_task.id}"
        f" merchant: {retry_task.scheme_identifier}"
    )
    if retry_task.callback_retries == 0:
        next_attempt_time = enqueue_retry_task_delay(
            connection=redis_raw,
            retry_task=retry_task,
            delay_seconds=pow(RETRY_BACKOFF_BASE, float(attempts)) * 60,
            call_function="app.journeys.join.attempt_join"
        )
        reset_task_for_callback_attempt(
            db_session=db_session,
            retry_task=retry_task,
            retry_status=t.cast(str, RetryTaskStatuses.RETRYING),
            next_attempt_time=next_attempt_time,
        )
        logger.debug(f"Next attempt time at {next_attempt_time}")
    elif attempts < MAX_CALLBACK_RETRY_COUNT:
        next_attempt_time = enqueue_retry_task_delay(
            connection=redis_raw, retry_task=retry_task, delay_seconds=pow(RETRY_BACKOFF_BASE, float(attempts)) * 60,
            call_function="app.journeys.join.attempt_join"
        )
        update_callback_attempt(
            db_session=db_session,
            retry_task=retry_task,
            next_attempt_time=next_attempt_time,
        )
        logger.debug(f"Next attempt time at {next_attempt_time}")
    elif attempts == MAX_CALLBACK_RETRY_COUNT:
        fail_callback_task(db_session=db_session, retry_task=retry_task)
        logger.warning("Max retries for callback task reached.")


def _handle_request_exception(
    *,
    connection: Any,
    backoff_base: int,
    max_retries: int,
    retry_task: RetryTask,
    request_exception: BaseError,
    retryable_status_codes: list[int],
    from_login: bool = False,
) -> t.Tuple[t.Optional[RetryTaskStatuses], t.Optional[Any]]:
    status = None
    next_attempt_time = None
    subject = retry_task.journey_type
    terminal = False
    resp = request_exception.generic_message
    attempts = retry_task.attempts + 1

    logger.debug(
        f"{subject} attempt {attempts}"
        f" failed for task: {retry_task.id}"
        f" merchant: {retry_task.scheme_identifier}"
    )

    if attempts <= max_retries:
        if from_login:
            call_function = "app.journeys.join.login_and_publish_status"
        else:
            call_function = "app.journeys.join.attempt_join"
        if (
            from_login
            or resp is None
            or 500 <= request_exception.code < 600
            or request_exception.code in retryable_status_codes
        ):
            next_attempt_time = enqueue_retry_task_delay(
                connection=connection,
                retry_task=retry_task,
                delay_seconds=pow(backoff_base, float(attempts)) * 60,
                call_function="app.journeys.join.attempt_join"
            )
            status = RetryTaskStatuses.RETRYING
            logger.debug(f"Next attempt time at {next_attempt_time}")
        else:
            terminal = True
            logger.debug(f"Received unhandlable error {resp}.  Stopping.")
    else:
        terminal = True
        logger.warning(f"No further retries. Setting status to {RetryTaskStatuses.FAILED}.")

    if terminal:
        status = RetryTaskStatuses.FAILED

    return status, next_attempt_time


def handle_request_exception(
    db_session: Session,
    *,
    connection: Any,
    backoff_base: int,
    max_retries: int,
    job: rq.job.Job | None,
    exc_value: BaseError,
    retryable_exceptions: list[BaseError],
    scheme_account_id: int | None = None,
):
    next_attempt_time = None
    if scheme_account_id:
        retry_task = get_task(db_session, scheme_account_id)
    else:
        retry_task = get_task(db_session, job.args[0])
    if retry_task.journey_type == "attempt-login":
        from_login = True

    retryable_status_codes = [exception.code for exception in retryable_exceptions]
    if from_login or type(exc_value) in retryable_exceptions:
        status, next_attempt_time = _handle_request_exception(
            connection=connection,
            backoff_base=backoff_base,
            max_retries=max_retries,
            retry_task=retry_task,
            request_exception=exc_value,
            retryable_status_codes=retryable_status_codes or [],
            from_login=from_login,
        )
    else:  # otherwise report to sentry and fail the task
        status = RetryTaskStatuses.FAILED

    try:
        update_task_for_retry(
            db_session=db_session,
            retry_task=retry_task,
            retry_status=t.cast(str, status),
            next_attempt_time=next_attempt_time,
        )
    except Exception as e:
        print(e)

    if status == RetryTaskStatuses.FAILED:
        if retry_task.journey_type == "attempt-join":
            handle_failed_join(db_session, retry_task, exc_value)


def handle_retry_task_request_error(
    job: rq.job.Job | None, exc_type: type, exc_value: BaseError, traceback: "Traceback"
) -> None:
    # max retry exception from immediate retries bubbles up to key error and that's how it'll reach
    # this stage, hence no retries will be scheduled until exception handling is implemented or fixed
    with db.session_scope() as session:
        handle_request_exception(  # pragma: no cover
            db_session=session,
            backoff_base=RETRY_BACKOFF_BASE,
            max_retries=MAX_RETRY_COUNT,
            job=job,
            exc_value=exc_value,  # type: ignore
            connection=redis_raw,
            retryable_exceptions=[
                EndSiteDownError,  # type: ignore
                ServiceConnectionError,  # type: ignore
                RetryLimitReachedError,  # type: ignore
                NotSentError,  # type: ignore
                IPBlockedError,  # type: ignore
                UnknownError,  # type: ignore
            ],
        )
