import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import rq
from retry_tasks_lib.db.models import RetryTask
from retry_tasks_lib.enums import RetryTaskStatuses
from retry_tasks_lib.utils.synchronous import enqueue_retry_task_delay, get_retry_task
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
from app.reporting import get_logger
from app.retry_worker import redis_raw
from app.scheme_account import update_pending_join_account

if TYPE_CHECKING:  # pragma: no cover
    from inspect import Traceback

logger = get_logger("retry-queue")


def handle_failed_join(task_data, exc_value):
    consent_ids = None
    tid = task_data["tid"]
    scheme_slug = task_data["scheme_slug"]
    user_info = json.loads(task_data["user_info"])
    consents = user_info["credentials"].get("consents", [])
    if consents:
        consent_ids = (consent["id"] for consent in consents)
    update_pending_join_account(
        user_info, tid, exc_value, scheme_slug=scheme_slug, consent_ids=consent_ids, raise_exception=False
    )


def _handle_request_exception(
    *,
    connection: Any,
    backoff_base: int,
    max_retries: int,
    retry_task: RetryTask,
    request_exception: BaseError,
    extra_status_codes_to_retry: list[int],
) -> tuple[dict, RetryTaskStatuses | None, datetime | None]:
    status = None
    next_attempt_time = None
    subject = retry_task.task_type.name
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
        f" merchant: {retry_task.get_params()['scheme_slug']}"
    )

    if retry_task.attempts < max_retries:
        if resp is None or 500 <= request_exception.code < 600 or request_exception.code in extra_status_codes_to_retry:
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
    extra_status_codes_to_retry: list[int] | None = None,
    retryable_exceptions: list[BaseError],
):

    response_audit = None
    next_attempt_time = None

    retry_task = get_retry_task(db_session, job.kwargs["retry_task_id"])

    if type(exc_value) in retryable_exceptions:
        response_audit, status, next_attempt_time = _handle_request_exception(
            connection=connection,
            backoff_base=backoff_base,
            max_retries=max_retries,
            retry_task=retry_task,
            request_exception=exc_value,
            extra_status_codes_to_retry=extra_status_codes_to_retry or [],
        )
    else:  # otherwise report to sentry and fail the task
        status = RetryTaskStatuses.FAILED

    retry_task.update_task(
        db_session,
        next_attempt_time=next_attempt_time,
        response_audit=response_audit,
        status=status,
        clear_next_attempt_time=True,
    )

    if status == RetryTaskStatuses.FAILED:
        task_data = retry_task.get_params()
        if retry_task.task_type == "attempt-join":
            handle_failed_join(task_data, exc_value)


def handle_retry_task_request_error(
    job: rq.job.Job, exc_type: type, exc_value: BaseError, traceback: "Traceback"
) -> Any:

    # max retry exception from immediate retries bubbles up to key error and that's how it'll reach
    # this stage, hence no retries will be scheduled until exception handling is implemented or fixed
    with SessionMaker() as db_session:
        handle_request_exception(  # pragma: no cover
            db_session=db_session,
            backoff_base=3,
            max_retries=3,
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
