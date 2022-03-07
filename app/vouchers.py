import pendulum


def generate_pending_voucher_code(timestamp):
    dt = pendulum.from_timestamp(timestamp)
    formatted = dt.format("DoMMM YYYY")
    if dt.day < 10:
        return f"Due {formatted}"
    return f"Due{formatted}"
