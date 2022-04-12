import json
from uuid import uuid4

import olympus_messaging
import requests
from flask import make_response, request
from flask_restful import Resource, abort
from flask_restful.utils.cors import crossdomain
from werkzeug.exceptions import NotFound

import settings
from app import publish, retry
from app.agents.exceptions import AgentError, LoginError
from app.agents.schemas import transaction_tuple_to_dict, balance_tuple_to_dict
from app.encoding import JsonEncoder
from app.encryption import AESCipher, get_aes_key
from app.exceptions import AgentException, UnknownException
from app.journeys.common import agent_login, get_agent_class
from app.journeys.journey_manager import login_journey
from app.journeys.login import login
from app.journeys.view import async_get_balance_and_publish, get_balance_and_publish
from app.messaging import queue
from app.publish import thread_pool_executor
from app.reporting import get_logger
from app.scheme_account import SchemeAccountStatus

log = get_logger("journey_manager")


def get_hades_balance(scheme_account_id):
    resp = requests.get(
        settings.HADES_URL + "/balances/scheme_account/" + str(scheme_account_id),
        headers={"Authorization": "Token " + settings.SERVICE_API_KEY},
    )

    try:
        resp_json = resp.json()
    except (AttributeError, TypeError) as e:
        raise UnknownException(e)
    else:
        if resp_json:
            return resp_json
        raise UnknownException("Empty response getting previous balance")


def handle_async_balance(agent_class, scheme_slug, user_info, transaction_id):
    scheme_account_id = user_info["scheme_account_id"]
    if user_info["status"] == SchemeAccountStatus.WALLET_ONLY:
        prev_balance = publish.zero_balance(scheme_account_id, transaction_id, user_info["user_set"])
        publish.status(scheme_account_id, 0, transaction_id, user_info)
    else:
        prev_balance = get_hades_balance(scheme_account_id)

    user_info["pending"] = False
    if user_info["status"] in [
        SchemeAccountStatus.PENDING,
        SchemeAccountStatus.WALLET_ONLY,
    ]:
        user_info["pending"] = True
        prev_balance["pending"] = True

    thread_pool_executor.submit(async_get_balance_and_publish, agent_class, scheme_slug, user_info, transaction_id)
    # return previous balance from hades so front-end has something to display
    return prev_balance


def login_journey(scheme_slug, user_info, transaction_id):
    scheme_account_id = user_info["scheme_account_id"]
    user_set = user_info["user_set"]
    try:
        agent_class = get_agent_class(scheme_slug)
        if agent_class.is_async:
            return handle_async_balance(agent_class, scheme_slug, user_info, transaction_id)
    except NotFound as e:
        # Update the scheme status on hermes to WALLET_ONLY (10)
        thread_pool_executor.submit(publish.status, user_info["scheme_account_id"], 10, transaction_id, user_info)
        abort(e.code, message=e.data["message"])

    key = retry.get_key(agent_class.__name__, user_info["scheme_account_id"])
    retry_count = retry.get_count(key)
    agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug)

    status = SchemeAccountStatus.UNKNOWN_ERROR
    threads = []
    try:
        balance, transactions = login(agent_instance, scheme_slug, user_info, transaction_id)
        status = SchemeAccountStatus.ACTIVE
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
                    transaction_id,
                    user_info,
                    # Harvey Nicols appears to be the only agent that requires create_journey
                    # WHY is it necessary?
                    journey=agent_instance.create_journey,
                )
            )

    # Publish balance to hades
    balance = publish.balance(
        balance,
        scheme_account_id,
        user_info["user_set"],
        transaction_id,
    ) if balance else None, None, None

    # Publish transactions to Hades
    threads.append(
        thread_pool_executor.submit(
            publish.transactions,
            transactions,
            scheme_account_id,
            user_set,
            transaction_id,
        )
    )

    [thread.result() for thread in threads]

    return balance
