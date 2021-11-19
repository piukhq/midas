import json
from decimal import Decimal
from enum import IntEnum

import requests

import settings
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    NO_SUCH_RECORD,
    SERVICE_CONNECTION_ERROR,
    UNKNOWN,
    JoinError,
    LoginError,
)
from app.encoding import JsonEncoder
from app.exceptions import AgentException
from app.http_request import get_headers
from app.reporting import get_logger
from app.tasks.resend_consents import ConsentStatus

TWO_PLACES = Decimal(10) ** -2

log = get_logger("scheme-account")


class SchemeAccountStatus:
    PENDING = 0
    ACTIVE = 1
    INVALID_CREDENTIALS = 403
    INVALID_MFA = 432
    END_SITE_DOWN = 530
    IP_BLOCKED = 531
    TRIPPED_CAPTCHA = 532
    INCOMPLETE = 5
    LOCKED_BY_ENDSITE = 434
    RETRY_LIMIT_REACHED = 429
    RESOURCE_LIMIT_REACHED = 503
    UNKNOWN_ERROR = 520
    MIDAS_UNREACHABLE = 9
    AGENT_NOT_FOUND = 404
    WALLET_ONLY = 10
    PASSWORD_EXPIRED = 533
    JOIN = 900
    NO_SUCH_RECORD = 444
    JOIN_IN_PROGRESS = 441
    JOIN_ERROR = 538
    GENERAL_ERROR = 439
    CARD_NUMBER_ERROR = 436
    CARD_NOT_REGISTERED = 438
    LINK_LIMIT_EXCEEDED = 437
    JOIN_ASYNC_IN_PROGRESS = 442
    PRE_REGISTERED_CARD = 406
    ENROL_FAILED = 901
    REGISTRATION_FAILED = 902
    ACCOUNT_ALREADY_EXISTS = 445
    SERVICE_CONNECTION_ERROR = 537


class JourneyTypes(IntEnum):
    JOIN = 0
    LINK = 1
    ADD = 2
    UPDATE = 3


def _get_status_and_delete_data(message, card_number=None):
    delete_data = {"all": True}
    if message == ACCOUNT_ALREADY_EXISTS:
        return SchemeAccountStatus.ACCOUNT_ALREADY_EXISTS, delete_data
    elif message == SERVICE_CONNECTION_ERROR:
        return SchemeAccountStatus.SERVICE_CONNECTION_ERROR, delete_data
    elif message == UNKNOWN:
        return SchemeAccountStatus.UNKNOWN_ERROR, delete_data
    elif message == NO_SUCH_RECORD:
        return SchemeAccountStatus.NO_SUCH_RECORD, delete_data
    elif card_number:
        return SchemeAccountStatus.REGISTRATION_FAILED, {"keep_card_number": True}
    else:
        return SchemeAccountStatus.ENROL_FAILED, delete_data


def update_pending_join_account(
    user_info, message, tid, identifier=None, scheme_slug=None, consent_ids=(), raise_exception=True
):
    scheme_account_id = user_info["scheme_account_id"]
    # for updating user ID credential you get for joining (e.g. getting issued a card number)
    headers = get_headers(tid)
    if identifier:
        try:
            data = json.dumps(identifier, cls=JsonEncoder)
        except Exception as e:
            log.exception(repr(e))
            raise
        else:
            requests.put(
                f"{settings.HERMES_URL}/schemes/accounts/{scheme_account_id}/credentials", data=data, headers=headers
            )
            return

    log.debug(f"Join error: {message}, updating scheme account: {scheme_account_id}")
    # error handling for pending scheme accounts waiting for join journey to complete
    credentials = user_info.get("credentials")
    card_number = None
    if credentials:
        card_number = credentials.get("card_number") or credentials.get("barcode")

    status, delete_data = _get_status_and_delete_data(message, card_number=card_number)

    data = {
        "status": status,
        "event_name": "join-failed-event",
        "metadata": {"scheme": scheme_slug},
        "user_info": user_info,
    }
    response = requests.post(
        "{}/schemes/accounts/{}/status".format(settings.HERMES_URL, scheme_account_id),
        data=json.dumps(data, cls=JsonEncoder),
        headers=headers,
    )
    log.debug(f"Hermes status update response: {response.json()}")

    remove_pending_consents(consent_ids, headers)

    requests.delete(
        "{}/schemes/accounts/{}/credentials".format(settings.HERMES_URL, scheme_account_id),
        data=json.dumps(delete_data, cls=JsonEncoder),
        headers=headers,
    )

    if raise_exception:
        raise AgentException(JoinError(message))


def update_pending_link_account(user_info, message, tid, scheme_slug=None, raise_exception=True):

    scheme_account_id = user_info["scheme_account_id"]
    # error handling for pending scheme accounts waiting for async link to complete
    headers = get_headers(tid)
    status_data = {
        "status": SchemeAccountStatus.WALLET_ONLY,
        "event_name": "async-link-failed-event",
        "metadata": {"scheme": scheme_slug},
        "user_info": user_info,
    }
    requests.post(
        "{}/schemes/accounts/{}/status".format(settings.HERMES_URL, scheme_account_id),
        data=json.dumps(status_data, cls=JsonEncoder),
        headers=headers,
    )

    question_data = {"property_list": ["link_questions"]}
    requests.delete(
        "{}/schemes/accounts/{}/credentials".format(settings.HERMES_URL, scheme_account_id),
        data=json.dumps(question_data, cls=JsonEncoder),
        headers=headers,
    )

    if raise_exception:
        raise AgentException(LoginError(message))


def remove_pending_consents(consent_ids, headers):
    data = json.dumps({"status": ConsentStatus.FAILED}, cls=JsonEncoder)
    for consent_id in consent_ids:
        requests.put("{}/schemes/user_consent/{}".format(settings.HERMES_URL, consent_id), data=data, headers=headers)


def delete_scheme_account(tid, scheme_account_id):
    headers = get_headers(tid)
    requests.delete("{}/schemes/accounts/{}".format(settings.HERMES_URL, scheme_account_id), headers=headers)
