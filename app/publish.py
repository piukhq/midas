import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from requests_futures.sessions import FuturesSession

from app.encoding import JsonEncoder
from app.utils import get_headers, minify_number
from settings import HADES_URL, HERMES_URL, MAX_VALUE_LABEL_LENGTH, logger

thread_pool_executor = ThreadPoolExecutor(max_workers=6)
PENDING_BALANCE = {
    'points': Decimal(0),
    'value': Decimal(0),
    'value_label': 'Pending',
}


def log_errors(session, resp):
    if not resp.ok:
        logger.error("Could not request to the url: {0}".format(resp.url))


def post(url, data, tid):
    session = FuturesSession(executor=thread_pool_executor)
    session.post(url, data=json.dumps(data, cls=JsonEncoder), headers=get_headers(tid),
                 background_callback=log_errors)


def put(url, data, tid):
    session = FuturesSession(executor=thread_pool_executor)
    session.put(url, data=json.dumps(data, cls=JsonEncoder), headers=get_headers(tid),
                background_callback=log_errors)


def transactions(transactions_items, scheme_account_id, user_set, tid):
    if not transactions_items:
        return None
    for transaction_item in transactions_items:
        transaction_item['scheme_account_id'] = scheme_account_id
        transaction_item['user_set'] = user_set
    post("{}/transactions".format(HADES_URL), transactions_items, tid)
    return transactions_items


def balance(balance_item, scheme_account_id, user_set, tid):
    balance_item = create_balance_object(balance_item, scheme_account_id, user_set)

    post("{}/balance".format(HADES_URL), balance_item, tid)
    return balance_item


def status(scheme_account_id, status, tid):
    data = {"status": status}
    post("{}/schemes/accounts/{}/status".format(HERMES_URL, scheme_account_id), data, tid)
    return status


def zero_balance(scheme_account_id, user_id, tid):
    return balance(PENDING_BALANCE, scheme_account_id, user_id, tid)


def create_balance_object(balance_item, scheme_account_id, user_set):
    balance_item['scheme_account_id'] = scheme_account_id
    balance_item['user_set'] = user_set
    balance_item['points_label'] = minify_number(balance_item['points'])

    if 'reward_tier' not in balance_item:
        balance_item['reward_tier'] = 0

    if len(balance_item['value_label']) > MAX_VALUE_LABEL_LENGTH:
        balance_item['value_label'] = 'Reward'

    return balance_item
