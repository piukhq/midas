from app.encoding import JsonEncoder
import json

from app.utils import minify_number
from settings import HADES_URL, HERMES_URL, SERVICE_API_KEY, logger
from concurrent.futures import ThreadPoolExecutor
from requests_futures.sessions import FuturesSession
import socket


thread_pool_executor = ThreadPoolExecutor(max_workers=3)


def log_errors(session, resp):
    if not resp.ok:
        logger.error("Could not post to the url: {0}".format(resp.url))


def post(url, data, tid):
    headers = {'Content-type': 'application/json',
               'transaction': tid,
               'User-agent': 'Midas on {0}'.format(socket.gethostname()),
               'Authorization': 'Token ' + SERVICE_API_KEY}
    session = FuturesSession(executor=thread_pool_executor)
    session.post(url, data=json.dumps(data, cls=JsonEncoder), headers=headers,
                 background_callback=log_errors)


def transactions(transactions_items, scheme_account_id, user_id, tid):
    if not transactions_items:
        return None
    for transaction_item in transactions_items:
        transaction_item['scheme_account_id'] = scheme_account_id
        transaction_item['user_id'] = user_id
    post("{}/transactions".format(HADES_URL), transactions_items, tid)
    return transactions_items


def balance(balance_item, scheme_account_id, user_id, tid):
    balance_item['scheme_account_id'] = scheme_account_id
    balance_item['user_id'] = user_id
    balance_item['points_label'] = minify_number(balance_item['points'])
    post("{}/balance".format(HADES_URL), balance_item, tid)
    return balance_item


def status(scheme_account_id, status, tid):
    data = {"status": status}
    post("{}/schemes/accounts/{}/status".format(HERMES_URL, scheme_account_id), data, tid)
    return status
