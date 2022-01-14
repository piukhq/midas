import random
from copy import deepcopy
from decimal import Decimal
from time import sleep
from typing import Optional

import arrow

from app.agents.base import MockedMiner
from app.agents.exceptions import (
    END_SITE_DOWN,
    STATUS_LOGIN_FAILED,
    STATUS_REGISTRATION_FAILED,
    UNKNOWN,
    JoinError,
    LoginError,
)
from app.agents.schemas import Balance, Transaction
from app.mocks import card_numbers
from app.mocks.users import USER_STORE, transactions

JOIN_FAIL_POSTCODES = ["fail", "fa1 1fa"]


class MockAgentHN(MockedMiner):
    add_error_credentials = {
        "email": {
            "endsitedown@testbink.com": END_SITE_DOWN,
        },
    }
    existing_card_numbers = card_numbers.HARVEY_NICHOLS
    join_fields = {"email", "password", "title", "first_name", "last_name"}
    join_prefix = "911"
    titles = [
        "Mr",
        "Mrs",
        "Miss",
        "Ms",
        "Dame",
        "Sir",
        "Doctor",
        "Professor",
        "Lord",
        "Lady",
    ]

    def login(self, credentials):
        self.check_and_raise_error_credentials(credentials)

        # if join request, assign new user rather than check credentials
        if self.join_fields.issubset(credentials.keys()):
            self.user_info = USER_STORE["000000"]
            card_suffix = random.randint(0, 9999999999)
            self.identifier = {"card_number": f"{self.join_prefix}{card_suffix:010d}"}
            return

        card_number = credentials.get("card_number")
        # if created from join, dont check credentials on balance updates
        if card_number and card_number.startswith(self.join_prefix):
            self.user_info = USER_STORE["000000"]
            return

        # if none of the above, do the normal login checks
        login_credentials = (credentials["email"].lower(), credentials["password"])
        for user, info in USER_STORE.items():
            try:
                auth_check = (
                    info["credentials"]["email"],
                    info["credentials"]["password"],
                )
            except KeyError:
                continue

            if login_credentials == auth_check:
                self.user_info = info
                user_id = user
                break

        else:
            raise LoginError(STATUS_LOGIN_FAILED)

        self.customer_number = card_numbers.HARVEY_NICHOLS[user_id]
        if credentials.get("card_number") != self.customer_number:
            self.identifier = {"card_number": self.customer_number}

        return

    def balance(self) -> Optional[Balance]:
        return Balance(
            points=self.user_info["points"],
            value=Decimal(0),
            value_label="",
            reward_tier=1,
        )

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception as ex:
            return []

    def parse_transaction(self, row: dict) -> Optional[Transaction]:
        return Transaction(
            date=row["date"],
            description=row["description"],
            points=row["points"],
        )

    def transaction_history(self) -> list[Transaction]:
        max_transactions = self.user_info["len_transactions"]
        # MER-824: If the user is five@testbink.com, ensure the date associated with transactions all occur
        # after the 25th October 2020
        if self.user_info["credentials"]["email"] == "five@testbink.com":
            transactions_copy = deepcopy(transactions)
            for transaction_copy in transactions_copy:
                transaction_copy["date"] = arrow.get("26/10/2020 14:24:15", "DD/MM/YYYY HH:mm:ss")

            transactions_list = [
                parsed_tx for raw_tx in transactions_copy if (parsed_tx := self.parse_transaction(raw_tx))
            ]

            return transactions_list[:max_transactions]
        elif self.user_info["credentials"]["email"] == "onetransaction@testbink.com":
            # MER-939: if the user is "onetransaction@testbink.com", we will need a single
            # transaction with a value of 0 and timestamp of 1612876767
            transactions_single = [
                {
                    "date": arrow.get(1612876767),
                    "description": "Test transaction: 1 item",
                    "points": Decimal("0"),
                },
            ]
            transactions_list = [
                parsed_tx for raw_tx in transactions_single if (parsed_tx := self.parse_transaction(raw_tx))
            ]
            return transactions_single
        else:
            transactions_list = [
                parsed_tx for raw_tx in transactions if (parsed_tx := self.parse_transaction(raw_tx))
            ]

        return transactions[:max_transactions]

    def join(self, credentials):
        self._validate_join_credentials(credentials)
        return {"message": "success"}

    def _validate_join_credentials(self, data):
        if len(data["password"]) < 6:
            raise JoinError(STATUS_REGISTRATION_FAILED)

        return super()._validate_join_credentials(data)


class MockAgentIce(MockedMiner):
    existing_card_numbers = card_numbers.ICELAND
    ghost_card_prefix = "633204003123123"
    join_fields = {
        "title",
        "first_name",
        "last_name",
        "phone",
        "email",
        "date_of_birth",
        "postcode",
        "county",
        "town_city",
        "address_1",
        "address_2",
    }
    point_conversion_rate = Decimal("1")
    retry_limit = None

    def login(self, credentials):
        card_number = credentials.get("card_number") or credentials.get("barcode")
        # if join request, assign new user rather than check credentials
        if self.join_fields.issubset(credentials.keys()):
            self.user_info = USER_STORE["000000"]
            if not card_number:
                card_suffix = random.randint(0, 999999999999999)
                card_number = f"9000{card_suffix:015d}"

            self.identifier["card_number"] = card_number
            self.identifier["barcode"] = card_number
            self.identifier["merchant_identifier"] = "testjoin"
            return

        # if created from join, dont check credentials on balance updates
        if credentials.get("merchant_identifier") == "testjoin":
            self.user_info = USER_STORE["000000"]
            return

        # if none of the above, do the normal login checks
        self.check_and_raise_error_credentials(credentials)
        try:
            user_id = card_numbers.ICELAND[card_number]
        except (KeyError, TypeError):
            raise LoginError(STATUS_LOGIN_FAILED)

        if user_id == "999000":
            sleep(20)

        self.user_info = USER_STORE[user_id]
        login_credentials = (
            credentials["last_name"].lower(),
            credentials["postcode"].lower(),
        )
        auth_check = (
            self.user_info["credentials"]["last_name"],
            self.user_info["credentials"]["postcode"],
        )

        if login_credentials != auth_check:
            raise LoginError(STATUS_LOGIN_FAILED)

        self.add_missing_credentials(credentials, card_number)
        return

    def balance(self) -> Optional[Balance]:
        points = self.user_info["points"]
        value = self.calculate_point_value(points)

        return Balance(
            points=self.user_info["points"],
            value=value,
            value_label="£{}".format(value),
        )

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception as ex:
            return []

    def parse_transaction(self, row: dict) -> Optional[Transaction]:
        return Transaction(
            date=row["date"],
            description=row["description"],
            points=row["points"],
        )

    def transaction_history(self) -> list[Transaction]:
        max_transactions = self.user_info["len_transactions"]
        # MER-825: If the user is the 'five' test user, ensure the date associated with transactions all occur
        # after the 25th October 2020
        if (
            self.user_info["credentials"]["last_name"] == "five"
            and self.user_info["credentials"]["postcode"] == "rg5 5aa"
            and self.user_info["credentials"]["email"] == "five@testbink.com"
        ):
            transactions_copy = deepcopy(transactions)
            for transaction_copy in transactions_copy:
                transaction_copy["date"] = arrow.get("26/10/2020 14:24:15", "DD/MM/YYYY HH:mm:ss")
            transactions_list = [
                parsed_tx for raw_tx in transactions_copy if (parsed_tx := self.parse_transaction(raw_tx))
            ]

            return transactions_list[:max_transactions]
        else:
            transactions_list = [
                parsed_tx for raw_tx in transactions if (parsed_tx := self.parse_transaction(raw_tx))
            ]

        return transactions_list[:max_transactions]

    def join(self, credentials, inbound=False):
        return self._validate_join_credentials(credentials)

    def _validate_join_credentials(self, data):
        if data["postcode"].lower() in JOIN_FAIL_POSTCODES:
            raise JoinError(UNKNOWN)

        return super()._validate_join_credentials(data)

    def add_missing_credentials(self, credentials, card_number):
        if not credentials.get("merchant_identifier"):
            self.identifier["merchant_identifier"] = "2900001"
        if not credentials.get("card_number"):
            self.identifier["card_number"] = card_number
        if not credentials.get("barcode"):
            self.identifier["barcode"] = card_number
