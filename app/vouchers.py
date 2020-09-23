import enum

import arrow


@enum.unique
class VoucherType(enum.Enum):
    JOIN = 0
    ACCUMULATOR = 1
    STAMPS = 2


@enum.unique
class VoucherState(enum.Enum):
    ISSUED = 0
    IN_PROGRESS = 1
    EXPIRED = 2
    REDEEMED = 3
    CANCELLED = 4


voucher_state_names = {
    VoucherState.ISSUED: "issued",
    VoucherState.IN_PROGRESS: "inprogress",
    VoucherState.EXPIRED: "expired",
    VoucherState.REDEEMED: "redeemed",
    VoucherState.CANCELLED: "cancelled",
}


def get_voucher_state(issue_date, redeem_date, expiry_date):
    if redeem_date is not None:
        state = VoucherState.REDEEMED
    elif issue_date is not None:
        if expiry_date <= arrow.utcnow():
            state = VoucherState.EXPIRED
        else:
            state = VoucherState.ISSUED
    else:
        state = VoucherState.IN_PROGRESS

    return state
