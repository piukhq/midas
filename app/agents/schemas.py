from decimal import Decimal
from typing import NamedTuple, Optional

from arrow.arrow import Arrow


class Transaction(NamedTuple):
    date: Arrow
    description: str
    points: Decimal
    location: Optional[str] = None
    value: Optional[Decimal] = None
    hash: Optional[str] = None


class Voucher(NamedTuple):
    state: str
    type: int
    issue_date: Optional[int] = None
    redeem_date: Optional[int] = None
    expiry_date: Optional[int] = None
    code: Optional[str] = None
    value: Optional[Decimal] = None
    target_value: Optional[Decimal] = None


class Balance(NamedTuple):
    points: Decimal
    value: Decimal
    value_label: str
    reward_tier: int = 0
    balance: Optional[Decimal] = None
    vouchers: Optional[list[Voucher]] = None


def _delete_null_key(item: dict, key: str) -> None:
    if key in item and item[key] is None:
        del item[key]


def voucher_tuple_to_dict(voucher: Voucher) -> dict:
    result = voucher._asdict()

    for field in ["issue_date", "redeem_date", "expiry_date", "code"]:
        _delete_null_key(result, field)

    return result


def balance_tuple_to_dict(balance: Balance) -> dict:
    result = balance._asdict()

    _delete_null_key(result, "balance")
    _delete_null_key(result, "vouchers")

    if result.get("vouchers"):
        result["vouchers"] = [voucher_tuple_to_dict(voucher) for voucher in result["vouchers"]]

    return result


def transaction_tuple_to_dict(transaction: Transaction) -> dict:
    result = transaction._asdict()

    _delete_null_key(result, "value")
    _delete_null_key(result, "location")

    return result
