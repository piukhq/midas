from decimal import Decimal

from arrow.arrow import Arrow
from voluptuous import Optional, Required, Schema


transactions = Schema(
    [
        {
            Required("date"): Arrow,
            Required("description"): str,
            Required("points"): Decimal,
            Optional("value"): Decimal,
            Optional("location"): str,
            Required("hash"): str,
        }
    ]
)

balance = Schema(
    {
        Required("points"): Decimal,
        Required("value"): Decimal,
        Optional("balance"): Decimal,
        Required("value_label"): str,
        Optional("reward_tier"): int,
        Optional("vouchers"): Schema(
            [
                {
                    Optional("issue_date"): int,
                    Optional("redeem_date"): int,
                    Optional("expiry_date"): int,
                    Optional("code"): str,
                    Required("type"): int,
                    Optional("value"): Decimal,
                    Optional("target_value"): Decimal,
                }
            ]
        ),
    }
)

credentials = Schema({Required("user_name"): str, Required("password"): str, Optional("card_number"): str})
