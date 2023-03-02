import enum

import arrow


@enum.unique
class VoucherState(enum.Enum):
    ISSUED = 0
    IN_PROGRESS = 1
    EXPIRED = 2
    REDEEMED = 3
    CANCELLED = 4
    PENDING = 5


voucher_state_names = {
    VoucherState.ISSUED: "issued",
    VoucherState.IN_PROGRESS: "inprogress",
    VoucherState.EXPIRED: "expired",
    VoucherState.REDEEMED: "redeemed",
    VoucherState.CANCELLED: "cancelled",
    VoucherState.PENDING: "pending"
}


def generate_pending_voucher_code(timestamp):
    dt = arrow.Arrow.fromtimestamp(timestamp)
    formatted = dt.format("DoMMM YYYY")
    if dt.day < 10:
        return f"Due: {formatted}"
    return f"Due:{formatted}"
