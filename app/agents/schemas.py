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
