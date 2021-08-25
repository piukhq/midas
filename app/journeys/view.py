import json

import requests

import settings
from app import publish
from app.agents.base import MerchantApi
from app.agents.exceptions import SCHEME_REQUESTED_DELETE, AgentError, LoginError, errors
from app.agents.schemas import balance_tuple_to_dict
from app.encoding import JsonEncoder
from app.exceptions import AgentException, UnknownException
from app.http_request import get_headers
from app.journeys.common import agent_login, publish_transactions
from app.publish import PENDING_BALANCE, create_balance_object, thread_pool_executor
from app.reporting import get_logger
from app.scheme_account import (
    JourneyTypes,
    SchemeAccountStatus,
    delete_scheme_account,
    update_pending_join_account,
    update_pending_link_account,
)

log = get_logger("view-journey")


def get_balance_and_publish(agent_class, scheme_slug, user_info, tid):
    scheme_account_id = user_info["scheme_account_id"]
    threads = []
    create_journey = None

    status = SchemeAccountStatus.UNKNOWN_ERROR
    try:
        balance, status, create_journey = request_balance(
            agent_class, user_info, scheme_account_id, scheme_slug, tid, threads
        )
        return balance
    except (LoginError, AgentError) as e:
        status = e.code
        raise AgentException(e)
    except AgentException as e:
        status = e.status_code
        raise
    except Exception as e:
        status = SchemeAccountStatus.UNKNOWN_ERROR
        raise UnknownException(e)
    finally:
        if user_info.get("pending") and not status == SchemeAccountStatus.ACTIVE:
            pass
        elif status is None:
            pass
        else:
            threads.append(
                thread_pool_executor.submit(
                    publish.status,
                    scheme_account_id,
                    status,
                    tid,
                    user_info,
                    journey=create_journey,
                )
            )

        [thread.result() for thread in threads]
        if status == errors[SCHEME_REQUESTED_DELETE]["code"]:
            log.debug(
                f"Received deleted request from scheme: {scheme_slug}. Deleting scheme account: {scheme_account_id}"
            )
            delete_scheme_account(tid, scheme_account_id)


def request_balance(agent_class, user_info, scheme_account_id, scheme_slug, tid, threads):
    create_journey = None
    # Pending scheme account using the merchant api framework expects a callback so should not call balance unless
    # the call is an async Link.
    is_merchant_api_agent = issubclass(agent_class, MerchantApi)
    check_status = user_info["status"]
    is_pending = check_status in [
        SchemeAccountStatus.PENDING,
        SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,
    ]
    if is_merchant_api_agent and is_pending and user_info["journey_type"] != JourneyTypes.LINK:
        user_info["pending"] = True
        status = check_status
        balance = create_balance_object(PENDING_BALANCE, scheme_account_id, user_info["user_set"])
    else:
        if scheme_slug == "iceland-bonus-card" and settings.ENABLE_ICELAND_VALIDATE:
            if user_info["status"] != SchemeAccountStatus.ACTIVE:
                user_info["journey_type"] = JourneyTypes.LINK.value

        agent_instance = agent_login(agent_class, user_info, scheme_slug=scheme_slug)

        # Send identifier (e.g membership id) to hermes if it's not already stored.
        if agent_instance.identifier:
            update_pending_join_account(user_info, "success", tid, identifier=agent_instance.identifier)

        balance_result = agent_instance.balance()
        if not balance_result:
            return None, None, None

        balance = publish.balance(
            balance_tuple_to_dict(balance_result),
            scheme_account_id,
            user_info["user_set"],
            tid,
        )

        # Asynchronously get the transactions for the a user
        threads.append(
            thread_pool_executor.submit(
                publish_transactions,
                agent_instance,
                scheme_account_id,
                user_info["user_set"],
                tid,
            )
        )
        status = SchemeAccountStatus.ACTIVE
        create_journey = agent_instance.create_journey

    return balance, status, create_journey


def async_get_balance_and_publish(agent_class, scheme_slug, user_info, tid):
    scheme_account_id = user_info["scheme_account_id"]
    try:
        balance = get_balance_and_publish(agent_class, scheme_slug, user_info, tid)
        return balance

    except (AgentException, UnknownException) as e:
        if user_info.get("pending"):
            message = f"Error with async linking. Scheme: {scheme_slug}, Error: {repr(e)}"
            update_pending_link_account(user_info, message, tid, scheme_slug=scheme_slug)
        else:
            status = e.status_code
            requests.post(
                f"{settings.HERMES_URL}/schemes/accounts/{scheme_account_id}/status",
                data=json.dumps({"status": status, "user_info": user_info}, cls=JsonEncoder),
                headers=get_headers(tid),
            )

        raise e
