import enum
from decimal import Decimal

from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.agents.base import ApiMiner


@enum.unique
class VoucherType(enum.Enum):
    JOIN = 0
    ACCUMULATOR = 1


class Ecrebo(ApiMiner):
    def register(self, credentials):
        pass

    def login(self, credentials):
        if credentials["card_number"] != "1234567890":
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        return {
            "points": Decimal(123),
            "value": Decimal(246),
            "value_label": "246 points",
            "vouchers": [
                {
                    "issue_date": 1568883184,
                    "code": "abc123",
                    "type": VoucherType.ACCUMULATOR.value,
                    "value": Decimal(30),
                    "target_value": Decimal(100),
                },
                {
                    "issue_date": 1569228000,
                    "redeem_date": 1569228230,
                    "type": VoucherType.JOIN.value,
                    "value": Decimal(60),
                    "target_value": Decimal(80),
                },
            ],
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
