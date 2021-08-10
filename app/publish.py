import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from requests_futures.sessions import FuturesSession

from app.encoding import JsonEncoder
from app.http_request import get_headers
from app.reporting import get_logger
from settings import HADES_URL, HERMES_URL, MAX_VALUE_LABEL_LENGTH

thread_pool_executor = ThreadPoolExecutor(max_workers=3)
units = ["k", "M", "B", "T"]
PENDING_BALANCE = {"points": Decimal(0), "value": Decimal(0), "value_label": "Pending"}


log = get_logger("publisher")


def log_errors(resp, *args, **kwargs):
    if not resp.ok:
        log.warning(f"Request to {resp.url} failed: {resp.status_code} {resp.reason}")


def post(url, data, tid):
    session = FuturesSession(executor=thread_pool_executor)
    session.post(url, data=json.dumps(data, cls=JsonEncoder), headers=get_headers(tid), hooks={"response": log_errors})


def put(url, data, tid):
    session = FuturesSession(executor=thread_pool_executor)
    session.put(url, data=json.dumps(data, cls=JsonEncoder), headers=get_headers(tid), hooks={"response": log_errors})


def _delete_null_key(item: dict, key: str) -> None:
    if key in item and item[key] is None:
        del item[key]


def transactions(transactions_items, scheme_account_id, user_set, tid):
    if not transactions_items:
        return None

    for transaction_item in transactions_items:
        transaction_item["scheme_account_id"] = scheme_account_id
        transaction_item["user_set"] = user_set

        # remove parts from transaction_item that hades cannot handle.
        _delete_null_key(transaction_item, "value")
        _delete_null_key(transaction_item, "location")

    post("{}/transactions".format(HADES_URL), transactions_items, tid)
    return transactions_items


def balance(balance_item, scheme_account_id, user_set, tid):
    balance_item = create_balance_object(balance_item, scheme_account_id, user_set)

    # remove parts from balance_item that hades cannot handle.
    _delete_null_key(balance_item, "balance")
    _delete_null_key(balance_item, "reward_tier")
    if "vouchers" in balance_item:
        del balance_item["vouchers"]

    # we remove vouchers as hades cannot handle them
    post("{}/balance".format(HADES_URL), balance_item, tid)

    return balance_item


def status(scheme_account_id, status, tid, user_info, journey=None):
    data = {"status": status, "journey": journey, "user_info": user_info}
    post("{}/schemes/accounts/{}/status".format(HERMES_URL, scheme_account_id), data, tid)
    return status


def zero_balance(scheme_account_id, user_id, tid):
    return balance(PENDING_BALANCE, scheme_account_id, user_id, tid)


def create_balance_object(balance_item, scheme_account_id, user_set):
    balance_item["scheme_account_id"] = scheme_account_id
    balance_item["user_set"] = user_set
    balance_item["points_label"] = minify_number(balance_item["points"])

    if "reward_tier" not in balance_item:
        balance_item["reward_tier"] = 0

    if len(balance_item["value_label"]) > MAX_VALUE_LABEL_LENGTH:
        balance_item["value_label"] = "Reward"

    return balance_item


def minify_number(n):
    n = int(n)

    if n < 10000:
        return str(n)

    count = 0
    total = n
    while True:
        if total / 1000 > 1:
            total //= 1000
            count += 1
        else:
            break

    return "{0}{1}".format(total, units[count - 1])
