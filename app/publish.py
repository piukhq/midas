from app.encoding import JsonEncoder
import json
from settings import HADES_URL, HERMES_URL, SERVICE_API_KEY
from concurrent.futures import ThreadPoolExecutor
from requests_futures.sessions import FuturesSession
import socket


thread_pool_executor = ThreadPoolExecutor(max_workers=3)


def log_errors(session, resp):
    # TODO: log the issue
    # if resp.status_code not in [200, 201]:
    pass


def post(url, data):
    headers = {'Content-type': 'application/json',
               'User-agent': 'Midas on {0}'.format(socket.gethostname()),
               'Authorization': 'Token ' + SERVICE_API_KEY}
    session = FuturesSession(executor=thread_pool_executor)
    session.post(url, data=json.dumps(data, cls=JsonEncoder), headers=headers,
                 background_callback=log_errors)


def transactions(transactions_items, scheme_account_id):
    for transaction_item in transactions_items:
        transaction_item['scheme_account_id'] = scheme_account_id
    post("{}/transactions".format(HADES_URL), transactions_items)
    return transactions_items


def balance(balance_item, scheme_account_id, user_id):
    balance_item['scheme_account_id'] = scheme_account_id
    balance_item['user_id'] = user_id
    post("{}/balance".format(HADES_URL), balance_item)
    return balance_item


def status(scheme_account_id, status):
    data = {"status": status}
    post("{}/schemes/accounts/{}/status".format(HERMES_URL, scheme_account_id), data)
    return status

