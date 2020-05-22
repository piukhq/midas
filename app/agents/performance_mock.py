import random
from decimal import Decimal
from uuid import uuid4

import arrow

from app.agents.base import MockedMiner
from app.agents.ecrebo import VoucherType
from app.agents.exceptions import LoginError, PRE_REGISTERED_CARD

GHOST_CARD_PREFIX = "0"


class MockPerformance(MockedMiner):
    point_conversion_rate = Decimal("1")

    def login(self, credentials):
        if not credentials.get("card_number"):
            self.identifier = {
                "card_number": f"1{uuid4()}"
            }
            return

        if credentials["card_number"].startswith(GHOST_CARD_PREFIX):
            raise LoginError(PRE_REGISTERED_CARD)

        return

    def balance(self):
        points = Decimal(random.randint(1, 50))
        self.calculate_point_value(points)

        return {
            "points": points,
            "value": points,
            "value_label": "£{}".format(points),
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        transactions = []
        for count in range(5):
            transactions.append(
                {
                    "date": arrow.now().shift(days=-count).format("DD/MM/YYYY HH:mm:ss"),
                    "description": f"Test Transaction: {uuid4()}",
                    "points": Decimal(random.randint(1, 50)),
                }
            )

        return transactions

    def register(self, credentials):
        return {"message": "success"}


class MockPerformanceVoucher(MockedMiner):

    def login(self, credentials):
        if not credentials.get("card_number"):
            self.identifier = {
                "card_number": f"1{uuid4()}"
            }
            return

        if credentials.get("card_number", "").startswith(GHOST_CARD_PREFIX):
            raise LoginError(PRE_REGISTERED_CARD)

        return

    def balance(self):
        value = Decimal(random.randint(1, 50))
        vouchers = []
        for count in range(2):
            date = arrow.now().shift(days=-count)
            vouchers.append(
                {
                    "issue_date": date,
                    "redeem_date": date,
                    "expiry_date": date,
                    "code": str(uuid4()),
                    "type": VoucherType.ACCUMULATOR.value,
                    "value": Decimal(random.randint(1, 50))
                }
            )

        return {
            "points": value,
            "value": value,
            "value_label": "",
            "vouchers": vouchers
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []

    def register(self, credentials):
        return {"message": "success"}
