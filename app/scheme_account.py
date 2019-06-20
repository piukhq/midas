import json

import requests

from app import AgentException
from app.encoding import JsonEncoder
from app.tasks.resend_consents import ConsentStatus
from app.utils import get_headers, SchemeAccountStatus
from settings import HERMES_URL, logger


def update_pending_join_account(user_info, message, tid, identifier=None, scheme_slug=None,
                                consent_ids=(), raise_exception=True):

    scheme_account_id = user_info['scheme_account_id']
    # for updating user ID credential you get for registering (e.g. getting issued a card number)
    headers = get_headers(tid)
    if identifier:
        requests.put('{}/schemes/accounts/{}/credentials'.format(HERMES_URL, scheme_account_id),
                     data=json.dumps(identifier, cls=JsonEncoder), headers=headers)
        return

    logger.debug('join error: {}, updating scheme account: {}'.format(message, scheme_account_id))
    # error handling for pending scheme accounts waiting for join journey to complete

    status = SchemeAccountStatus.JOIN
    delete_data = {'all': True}

    if 'credentials' in user_info and 'card_number' in user_info['credentials']:
        status = SchemeAccountStatus.PRE_REGISTERED_CARD
        delete_data = {'keep_card_number': True}

    data = {
        'status': status,
        'event_name': 'join-failed-event',
        'metadata': {'scheme': scheme_slug},
        'user_info': user_info
    }
    requests.post("{}/schemes/accounts/{}/status".format(HERMES_URL, scheme_account_id),
                  data=json.dumps(data, cls=JsonEncoder), headers=headers)

    remove_pending_consents(consent_ids, headers)

    requests.delete('{}/schemes/accounts/{}/credentials'.format(HERMES_URL, scheme_account_id),
                    data=json.dumps(delete_data, cls=JsonEncoder), headers=headers)

    if raise_exception:
        raise AgentException(message)


def update_pending_link_account(user_info, message, tid, scheme_slug=None, raise_exception=True):

    scheme_account_id = user_info['scheme_account_id']
    # error handling for pending scheme accounts waiting for async link to complete
    headers = get_headers(tid)
    status_data = {'status': SchemeAccountStatus.WALLET_ONLY,
                   'event_name': 'async-link-failed-event',
                   'metadata': {'scheme': scheme_slug},
                   'user_info': user_info
                   }
    requests.post('{}/schemes/accounts/{}/status'.format(HERMES_URL, scheme_account_id),
                  data=json.dumps(status_data, cls=JsonEncoder), headers=headers)

    question_data = {'property_list': ['link_questions']}
    requests.delete('{}/schemes/accounts/{}/credentials'.format(HERMES_URL, scheme_account_id),
                    data=json.dumps(question_data, cls=JsonEncoder), headers=headers)

    if raise_exception:
        raise AgentException(message)


def remove_pending_consents(consent_ids, headers):
    data = json.dumps({'status': ConsentStatus.FAILED}, cls=JsonEncoder)
    for consent_id in consent_ids:
        requests.put('{}/schemes/user_consent/{}'.format(HERMES_URL, consent_id), data=data, headers=headers)


def delete_scheme_account(tid, scheme_account_id):
    headers = get_headers(tid)
    requests.delete("{}/schemes/accounts/{}".format(HERMES_URL, scheme_account_id), headers=headers)
