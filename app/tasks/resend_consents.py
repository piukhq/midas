import importlib
import json
from enum import IntEnum

import requests

from app import sentry
from app.encoding import JsonEncoder
from app.utils import get_headers
from settings import HERMES_URL, logger
from .resend import ReTryTaskStore


class ConsentStatus(IntEnum):
    PENDING = 0
    SUCCESS = 1
    FAILED = 2


class ConsentSendState(IntEnum):
    SEND_TO_AGENT = 0
    SEND_TO_HERMES_RESULT = 1
    DONE = 2


def send_consents(consents_data):
    consents_data["state"] = ConsentSendState.SEND_TO_AGENT        # set to first state  send agent consents
    consents_data["status"] = ConsentStatus.PENDING
    consents_data["retries"] = consents_data["agent_tries"] - 1
    done, message = try_consents(consents_data)

    if not done:
        logger.debug(message)
        task = ReTryTaskStore()
        task.set_task("app.tasks.resend_consents", "try_consents", consents_data)


def try_consents(consents_data):
    """ This function  requires a consents data to be set.

    It is called for 1st attempt and then form background task if retries are required,

    The routine should manage state of process so that only when complete of fatal error will it return true
    It is therefore possible to continue retries if an internal log status message fails
    :param consents_data:
    :return:  Tuple:
                continue_status: True to terminate any retries, False to continue to rety
                response_list:  list of logged errors (successful one will not be wriiten to redis)
    """
    try:
        if consents_data['state'] == ConsentSendState.SEND_TO_AGENT:
            done, message = try_agent_send(consents_data)
            if not done:
                return False, message
        return try_hermes_confirm(consents_data)

    except requests.RequestException as e:
        # other exceptions will abort retries and exception will be monitored by sentry
        sentry.captureException()
        return False, f"{consents_data.get('identifier','')} {consents_data['state']}: IO error {str(e)}"


def try_agent_send(consents_data):
    resp = requests.post(consents_data['url'], data=consents_data['message'],
                         timeout=10, headers=consents_data['headers'])
    done = False
    message_prefix = f"{consents_data.get('id','')} sending to agent: "
    message = ''
    if resp.status_code in (200, 201, 202, 204):
        consents_data["status"] = ConsentStatus.SUCCESS
        done = True
        if consents_data.get('callback'):
            module = importlib.import_module(consents_data['callback'])
            func = getattr(module, consents_data.get('callback_function', 'agent_consent_response'))
            agent_sent, message = func(resp)
            if not agent_sent:
                consents_data["status"] = ConsentStatus.FAILED
                done = False
                message = f"{message_prefix}{message}"
    else:
        consents_data["status"] = ConsentStatus.FAILED
        message = f"{message_prefix}Error Code {resp.status_code}"

    if consents_data["status"] == ConsentStatus.FAILED and consents_data["retries"] == 0:
        done = True

    if done:
        consents_data['state'] = ConsentSendState.SEND_TO_HERMES_RESULT

    return done, message


def try_hermes_confirm(consents_data):
    send_errors = []
    consents_data['retries'] = 0
    message_prefix = f"{consents_data.get('id','')} sending to hermes: "
    for user_consent_id, retry_confirm in consents_data['confirm_tries'].items():
        if retry_confirm > 0:
            resp = requests.put(f'{HERMES_URL}/schemes/user_consent/{user_consent_id}', timeout=10,
                                data=json.dumps({"status": consents_data["status"]}, cls=JsonEncoder),
                                headers=get_headers(0))
            if resp.status_code == 200:
                consents_data['confirm_tries'][user_consent_id] = 0  # no more tries for this message
            else:
                consents_data['confirm_tries'][user_consent_id] -= 1
                send_errors.append(f' User consent id {user_consent_id} status code {resp.status_code}')
        consents_data['retries'] += consents_data['confirm_tries'][user_consent_id]

    if consents_data['retries'] <= 0:
        consents_data["state"] = ConsentSendState.DONE
        return True, "done"
    else:
        return False, f"{message_prefix} Hermes confirm errors  {''.join(send_errors)}"


def send_consent_status(consents_data):
    done, message = try_hermes_confirm(consents_data)

    if not done:
        logger.error(message)
        task = ReTryTaskStore()
        task.set_task("app.tasks.resend_consents", "try_hermes_confirm", consents_data)
