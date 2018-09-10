import json

import requests

from app import AgentException
from app.analytics import raise_event
from app.encoding import JsonEncoder
from app.tasks.resend_consents import ConsentStatus
from app.utils import get_headers, SchemeAccountStatus
from settings import HERMES_URL


def update_pending_join_account(scheme_account_id, message, tid, identifier=None, intercom_data=None,
                                consent_ids=(), raise_exception=True):
    # for updating user ID credential you get for registering (e.g. getting issued a card number)
    headers = get_headers(tid)
    if identifier:
        requests.put('{}/schemes/accounts/{}/credentials'.format(HERMES_URL, scheme_account_id),
                     data=json.dumps(identifier, cls=JsonEncoder), headers=headers)
        return

    # error handling for pending scheme accounts waiting for join journey to complete
    data = {'status': SchemeAccountStatus.JOIN}
    requests.post("{}/schemes/accounts/{}/status".format(HERMES_URL, scheme_account_id),
                  data=json.dumps(data, cls=JsonEncoder), headers=headers)

    remove_pending_consents(consent_ids, headers)

    data = {'all': True}
    requests.delete('{}/schemes/accounts/{}/credentials'.format(HERMES_URL, scheme_account_id),
                    data=json.dumps(data, cls=JsonEncoder), headers=headers)

    metadata = intercom_data['metadata']
    raise_event('join-failed-event', intercom_data['user_id'], intercom_data['user_email'], metadata)

    if raise_exception:
        raise AgentException(message)


def update_pending_link_account(scheme_account_id, message, tid, intercom_data=None, raise_exception=True):
    # error handling for pending scheme accounts waiting for async link to complete
    headers = get_headers(tid)
    status_data = {'status': SchemeAccountStatus.WALLET_ONLY}
    requests.post('{}/schemes/accounts/{}/status'.format(HERMES_URL, scheme_account_id),
                  data=json.dumps(status_data, cls=JsonEncoder), headers=headers)

    question_data = {'property_list': ['link_questions']}
    requests.delete('{}/schemes/accounts/{}/credentials'.format(HERMES_URL, scheme_account_id),
                    data=json.dumps(question_data, cls=JsonEncoder), headers=headers)

    metadata = intercom_data['metadata']
    raise_event('async-link-failed-event', intercom_data['user_id'], intercom_data['user_email'], metadata)

    if raise_exception:
        raise AgentException(message)


def remove_pending_consents(consent_ids, headers):
    data = json.dumps({'status': ConsentStatus.FAILED}, cls=JsonEncoder)
    for consent_id in consent_ids:
        requests.put('{}/schemes/user_consent/{}'.format(HERMES_URL, consent_id), data=data, headers=headers)
