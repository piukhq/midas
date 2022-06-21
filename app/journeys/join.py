import json

from flask_restful import abort
from retry_tasks_lib.db.models import RetryTask
from retry_tasks_lib.enums import RetryTaskStatuses
from retry_tasks_lib.utils.synchronous import retryable_task
from werkzeug.exceptions import NotFound

from app import publish
from app.agents.schemas import balance_tuple_to_dict
from app.db import SessionMaker
from app.exceptions import AccountAlreadyExistsError, BaseError, UnknownError
from app.journeys.common import agent_login, get_agent_class, publish_transactions
from app.reporting import get_logger
from app.resources import decrypt_credentials
from app.scheme_account import SchemeAccountStatus, update_pending_join_account

log = get_logger("join-journey")


def agent_join(agent_class, user_info, tid, scheme_slug=None):
    agent_instance = agent_class(0, user_info, scheme_slug=scheme_slug)
    error = None
    try:
        agent_instance.attempt_join()
    except BaseError as e:
        raise e

    return {"agent": agent_instance, "error": error}


def login_and_publish_status(agent_class, user_info, scheme_slug, join_result, tid):
    try:
        if join_result["agent"].expecting_callback:
            return True
        agent_instance = agent_login(agent_class, user_info, scheme_slug=scheme_slug, from_join=True)
        if agent_instance.identifier:
            update_pending_join_account(user_info, tid, identifier=agent_instance.identifier)
        elif join_result["agent"].identifier:
            update_pending_join_account(
                user_info,
                tid,
                identifier=join_result["agent"].identifier,
            )
    except BaseError as e:
        if join_result["error"] == AccountAlreadyExistsError:
            consents = user_info["credentials"].get("consents", [])
            consent_ids = (consent["id"] for consent in consents)
            update_pending_join_account(
                user_info,
                tid,
                error=e,
                scheme_slug=scheme_slug,
                consent_ids=consent_ids,
            )
        else:
            publish.zero_balance(user_info["scheme_account_id"], user_info["user_set"], tid)
        return True

    status = SchemeAccountStatus.ACTIVE
    try:
        publish.balance(
            balance_tuple_to_dict(agent_instance.balance()),
            user_info["scheme_account_id"],
            user_info["user_set"],
            tid,
        )
        publish_transactions(agent_instance, user_info["scheme_account_id"], user_info["user_set"], tid)
    except Exception as e:
        status = SchemeAccountStatus.UNKNOWN_ERROR
        raise UnknownError(exception=e) from e
    finally:
        publish.status(user_info["scheme_account_id"], status, tid, user_info, journey="join")
        return True


@retryable_task(db_session_factory=SessionMaker)
def attempt_join(retry_task: RetryTask, db_session: "Session"):
    join_data = retry_task.get_params()
    tid = join_data["tid"]
    scheme_slug = join_data["scheme_slug"]
    user_info = json.loads(join_data["user_info"])
    user_info["credentials"] = decrypt_credentials(user_info["credentials"])
    try:
        agent_class = get_agent_class(scheme_slug)
    except NotFound as e:
        # Update the scheme status on hermes to JOIN(900)
        publish.status(user_info["scheme_account_id"], 900, user_info["tid"], user_info)
        abort(e.code, message=e.data["message"])

    join_result = agent_join(agent_class, user_info, tid, scheme_slug=scheme_slug)

    retry_task.update_task(
        db_session, response_audit={}, status=RetryTaskStatuses.SUCCESS, clear_next_attempt_time=True
    )

    login_and_publish_status(agent_class, user_info, scheme_slug, join_result, tid)
