import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import rq
from sqlalchemy.orm.session import Session

from app.db import SessionMaker
from app.exceptions import (
    BaseError,
    EndSiteDownError,
    IPBlockedError,
    NotSentError,
    RetryLimitReachedError,
    ServiceConnectionError,
)
from app.models import CallbackStatuses, RetryTask, RetryTaskStatuses
from app.reporting import get_logger
from app.resources import decrypt_credentials
from app.retry_util import enqueue_retry_task_delay, get_task
from app.scheme_account import update_pending_join_account
from settings import MAX_CALLBACK_RETRY_COUNT, MAX_RETRY_COUNT, redis_raw

if TYPE_CHECKING:  # pragma: no cover
    from inspect import Traceback

logger = get_logger("retry-queue")


def handle_failed_join(retry_task, exc_value):
    consent_ids = None
    tid = retry_task.message_uid
    scheme_slug = retry_task.scheme_identifier
    user_info = json.loads(retry_task.request_data)
    user_info["credentials"] = decrypt_credentials(user_info["credentials"])
    consents = user_info["credentials"].get("consents", [])
    if consents:
        consent_ids = (consent["id"] for consent in consents)
    update_pending_join_account(
        user_info, tid, exc_value, scheme_slug=scheme_slug, consent_ids=consent_ids, raise_exception=False
    )


def retry_on_callback(db_session: Session, backoff_base: int, tid: str, error_code: str) -> RetryTask:
    response_audit: dict[str, Any] = {
        "error": str(error_code),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    retry_task = get_task(db_session, tid)

    if error_code != "JOIN_ERROR":
        retry_task.update_task(
            status=RetryTaskStatuses.FAILED, callback_status=CallbackStatuses.COMPLETE, response_audit=response_audit
        )
        return retry_task

    subject = retry_task.journey_type
    logger.debug(
        f"{subject} callback attempt {retry_task.attempts}"
        f" failed for task: {retry_task.retry_task_id}"
        f" merchant: {retry_task.scheme_identifier}"
    )
    next_attempt_time = pow(backoff_base, float(retry_task.callback_retries)) * 60
    if retry_task.callback_status not in [CallbackStatuses.RETRYING, CallbackStatuses.COMPLETE]:
        next_attempt_time = enqueue_retry_task_delay(
            connection=redis_raw, retry_task=retry_task, delay_seconds=next_attempt_time
        )
        retry_task.update_task(
            db_session=db_session,
            callback_status=CallbackStatuses.RETRYING,
            next_attempt_time=next_attempt_time,
            clear_attempts=True,
            response_audit=response_audit,
        )
        logger.debug(f"Next attempt time at {next_attempt_time}")
    elif retry_task.callback_retries < MAX_CALLBACK_RETRY_COUNT:
        retry_task.update_task(db_session=db_session, increase_callback_retries=True)
        enqueue_retry_task_delay(connection=redis_raw, retry_task=retry_task, delay_seconds=next_attempt_time)
        logger.debug(f"Next attempt time at {next_attempt_time}")
    elif retry_task.callback_retries == MAX_CALLBACK_RETRY_COUNT:
        retry_task.update_task(
            db_session=db_session,
            status=RetryTaskStatuses.FAILED,
            callback_status=CallbackStatuses.COMPLETE,
            response_audit=response_audit,
        )
        logger.warning("Max retries for callback task reached.")

    return retry_task


def _handle_request_exception(
    *,
    connection: Any,
    backoff_base: int,
    max_retries: int,
    retry_task: RetryTask,
    request_exception: BaseError,
    retryable_status_codes: list[int],
) -> tuple[dict, RetryTaskStatuses | None, datetime | None]:
    status = None
    next_attempt_time = None
    subject = retry_task.journey_type
    terminal = False
    response_audit: dict[str, Any] = {
        "error": str(request_exception),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }

    resp = request_exception.generic_message

    response_audit["response"] = {
        "status": request_exception.code,
        "body": resp,
    }

    logger.debug(
        f"{subject} attempt {retry_task.attempts}"
        f" failed for task: {retry_task.retry_task_id}"
        f" merchant: {retry_task.scheme_identifier}"
    )

    if retry_task.attempts < max_retries:
        if resp is None or 500 <= request_exception.code < 600 or request_exception.code in retryable_status_codes:
            next_attempt_time = enqueue_retry_task_delay(
                connection=connection,
                retry_task=retry_task,
                delay_seconds=pow(backoff_base, float(retry_task.attempts)) * 60,
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

    return response_audit, status, next_attempt_time


def handle_request_exception(
    db_session: Session,
    *,
    connection: Any,
    backoff_base: int,
    max_retries: int,
    job: rq.job.Job,
    exc_value: BaseError,
    retryable_exceptions: list[BaseError],
):

    response_audit = None
    next_attempt_time = None
    retry_task = get_task(db_session, job.args[0])
    retryable_status_codes = [exception.code for exception in retryable_exceptions]

    if type(exc_value) in retryable_exceptions:
        response_audit, status, next_attempt_time = _handle_request_exception(
            connection=connection,
            backoff_base=backoff_base,
            max_retries=max_retries,
            retry_task=retry_task,
            request_exception=exc_value,
            retryable_status_codes=retryable_status_codes or [],
        )
    else:  # otherwise report to sentry and fail the task
        status = RetryTaskStatuses.FAILED

    retry_task.update_task(
        db_session,
        next_attempt_time=next_attempt_time,
        response_audit=response_audit,
        status=status,
        clear_next_attempt_time=True,
        increase_attempts=True,
    )

    if status == RetryTaskStatuses.FAILED:
        if retry_task.journey_type == "attempt-join":
            handle_failed_join(retry_task, exc_value)


def handle_retry_task_request_error(
    job: rq.job.Job, exc_type: type, exc_value: Exception, traceback: "Traceback"
) -> Any:

    # max retry exception from immediate retries bubbles up to key error and that's how it'll reach
    # this stage, hence no retries will be scheduled until exception handling is implemented or fixed
    with SessionMaker() as db_session:
        handle_request_exception(  # pragma: no cover
            db_session=db_session,
            backoff_base=3,
            max_retries=MAX_RETRY_COUNT,
            job=job,
            exc_value=exc_value,
            connection=redis_raw,
            retryable_exceptions=[
                EndSiteDownError,  # type: ignore
                ServiceConnectionError,  # type: ignore
                RetryLimitReachedError,  # type: ignore
                NotSentError,  # type: ignore
                IPBlockedError,  # type: ignore
            ],
        )
