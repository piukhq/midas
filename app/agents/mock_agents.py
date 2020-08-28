import random
import uuid
from decimal import Decimal
from time import sleep

import arrow
from app.agents.base import MockedMiner
from app.agents.ecrebo import Ecrebo, VoucherType
from app.agents.exceptions import (
    CARD_NUMBER_ERROR, END_SITE_DOWN, STATUS_LOGIN_FAILED, STATUS_REGISTRATION_FAILED, UNKNOWN,
    LoginError, RegistrationError)
from app.mocks import card_numbers
from app.mocks.ecrebo.card_numbers import WHSMITH as whsmith_card_numbers
from app.mocks.ecrebo.users import USER_STORE as ecrebo_user_store
from app.mocks.users import USER_STORE, transactions

JOIN_FAIL_POSTCODES = ['fail', 'fa1 1fa']


class MockAgentHN(MockedMiner):
    add_error_credentials = {
        'email': {
            'endsitedown@testbink.com': END_SITE_DOWN,
        },
    }
    existing_card_numbers = card_numbers.HARVEY_NICHOLS
    join_fields = {'email', 'password', 'title', 'first_name', 'last_name'}
    join_prefix = '911'
    titles = ['Mr', 'Mrs', 'Miss', 'Ms', 'Dame', 'Sir', 'Doctor', 'Professor', 'Lord', 'Lady']

    def login(self, credentials):
        self.check_and_raise_error_credentials(credentials)

        # if join request, assign new user rather than check credentials
        if self.join_fields.issubset(credentials.keys()):
            self.user_info = USER_STORE['000000']
            card_suffix = random.randint(0, 9999999999)
            self.identifier = {
                'card_number': f'{self.join_prefix}{card_suffix:010d}'
            }
            return

        card_number = credentials.get('card_number')
        # if created from join, dont check credentials on balance updates
        if card_number and card_number.startswith(self.join_prefix):
            self.user_info = USER_STORE['000000']
            return

        # if none of the above, do the normal login checks
        login_credentials = (credentials['email'].lower(), credentials['password'])
        for user, info in USER_STORE.items():
            try:
                auth_check = (info['credentials']['email'], info['credentials']['password'])
            except KeyError:
                continue

            if login_credentials == auth_check:
                self.user_info = info
                user_id = user
                break

        else:
            raise LoginError(STATUS_LOGIN_FAILED)

        self.customer_number = card_numbers.HARVEY_NICHOLS[user_id]
        if credentials.get('card_number') != self.customer_number:
            self.identifier = {'card_number': self.customer_number}

        return

    def balance(self):
        return {
            'points': self.user_info['points'],
            'value': Decimal(0),
            'value_label': '',
            'reward_tier': 1
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]

    def register(self, credentials):
        self._validate_join_credentials(credentials)
        return {"message": "success"}

    def _validate_join_credentials(self, data):
        if len(data['password']) < 6:
            raise RegistrationError(STATUS_REGISTRATION_FAILED)

        return super()._validate_join_credentials(data)


class MockAgentIce(MockedMiner):
    existing_card_numbers = card_numbers.ICELAND
    ghost_card_prefix = '633204123123123'
    join_fields = {'title', 'first_name', 'last_name', 'phone', 'email', 'date_of_birth', 'postcode', 'county',
                   'town_city', 'address_1', 'address_2'}
    point_conversion_rate = Decimal('1')
    retry_limit = None

    def login(self, credentials):
        card_number = credentials.get('card_number') or credentials.get('barcode')
        # if join request, assign new user rather than check credentials
        if self.join_fields.issubset(credentials.keys()):
            self.user_info = USER_STORE['000000']
            if not card_number:
                card_suffix = random.randint(0, 999999999999999)
                card_number = f'9000{card_suffix:015d}'

            self.identifier['card_number'] = card_number
            self.identifier['barcode'] = card_number
            self.identifier['merchant_identifier'] = 'testregister'
            return

        # if created from join, dont check credentials on balance updates
        if credentials.get('merchant_identifier') == 'testregister':
            self.user_info = USER_STORE['000000']
            return

        # if none of the above, do the normal login checks
        self.check_and_raise_error_credentials(credentials)
        try:
            user_id = card_numbers.ICELAND[card_number]
        except (KeyError, TypeError):
            raise LoginError(STATUS_LOGIN_FAILED)

        if user_id == '999000':
            sleep(20)

        self.user_info = USER_STORE[user_id]
        login_credentials = (credentials['last_name'].lower(), credentials['postcode'].lower())
        auth_check = (self.user_info['credentials']['last_name'], self.user_info['credentials']['postcode'])

        if login_credentials != auth_check:
            raise LoginError(STATUS_LOGIN_FAILED)

        self.add_missing_credentials(credentials, card_number)
        return

    def balance(self):
        points = self.user_info['points']
        value = self.calculate_point_value(points)

        return {
            'points': self.user_info['points'],
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]

    def register(self, credentials, inbound=False):
        return self._validate_join_credentials(credentials)

    def _validate_join_credentials(self, data):
        if data['postcode'].lower() in JOIN_FAIL_POSTCODES:
            raise RegistrationError(UNKNOWN)

        return super()._validate_join_credentials(data)

    def add_missing_credentials(self, credentials, card_number):
        if not credentials.get('merchant_identifier'):
            self.identifier['merchant_identifier'] = '2900001'
        if not credentials.get('card_number'):
            self.identifier['card_number'] = card_number
        if not credentials.get('barcode'):
            self.identifier['barcode'] = card_number


class MockAgentCoop(MockedMiner):
    existing_card_numbers = card_numbers.COOP
    ghost_card_prefix = '63317492123123'
    join_fields = {'title', 'first_name', 'last_name', 'email', 'date_of_birth', 'postcode', 'town_city', 'address_1'}
    retry_limit = None
    titles = ['Mr', 'Mrs', 'Miss', 'Ms', 'Mx', 'Dr', 'Doctor', 'Prefer not to say']
    point_conversion_rate = Decimal('1')

    def login(self, credentials):
        card_number = credentials.get('card_number') or credentials.get('barcode')
        # if join request, assign new user rather than check credentials
        if self.join_fields.issubset(credentials.keys()):
            self.user_info = USER_STORE['000000']
            if not card_number:
                card_suffix = random.randint(0, 9999999999)
                card_number = f'63317491{card_suffix:010d}'

            self.identifier['card_number'] = card_number
            self.identifier['merchant_identifier'] = 'testregister'
            return

        # if created from join, dont check credentials on balance updates
        if credentials.get('merchant_identifier') == 'testregister':
            self.user_info = USER_STORE['000000']
            return

        # if none of the above, do the normal login checks
        self.check_and_raise_error_credentials(credentials)
        card_number = credentials.get('card_number')
        try:
            user_id = card_numbers.COOP[card_number]
        except (KeyError, TypeError):
            raise LoginError(CARD_NUMBER_ERROR)

        self.user_info = USER_STORE[user_id]
        login_credentials = (credentials['postcode'].lower(), credentials['date_of_birth'])
        auth_check = (self.user_info['credentials']['postcode'], self.user_info['credentials']['date_of_birth'])

        if login_credentials != auth_check:
            raise LoginError(STATUS_LOGIN_FAILED)

        self.add_missing_credentials(credentials, card_number)
        return

    def balance(self):
        points = self.user_info['points']
        value = self.calculate_point_value(points)

        return {
            'points': self.user_info['points'],
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        max_transactions = self.user_info['len_transactions']
        return transactions[:max_transactions]

    def register(self, credentials, inbound=False):
        return self._validate_join_credentials(credentials)

    def _validate_join_credentials(self, data):
        if data['postcode'].lower() in JOIN_FAIL_POSTCODES:
            raise RegistrationError(UNKNOWN)

        return super()._validate_join_credentials(data)

    def add_missing_credentials(self, credentials, card_number):
        if not credentials.get('merchant_identifier'):
            self.identifier['merchant_identifier'] = '4000000000001'
        if not credentials.get('card_number'):
            self.identifier['card_number'] = card_number


class MockAgentWHS(MockedMiner, Ecrebo):
    existing_card_numbers = whsmith_card_numbers
    join_fields = {
        "email",
        "title",
        "first_name",
        "last_name",
        "phone",
        "address_1",
        "town_city",
        "postcode",
    }

    titles = ['Mr', 'Mrs', 'Miss', 'Ms', 'Mx', 'Dr', 'Prefer not to say']

    def login(self, credentials):
        self.check_and_raise_error_credentials(credentials)

        # if join request, assign new user with zero balance and no vouchers
        if self.join_fields.issubset(credentials.keys()):
            merchant_identifier = str(uuid.uuid4())
            self.user_info = ecrebo_user_store["whsmith"]['0000001']
            self.identifier = {
                "card_number": self.user_info["card_number"],
                "merchant_identifier": merchant_identifier
            }
            self.user_info["credentials"].update(self.identifier)
        else:
            # Assume we're on an add journey from here on
            card_number = credentials.get('card_number')
            # Validation: does the incoming card match one of our test ones?
            try:
                user_id = whsmith_card_numbers[card_number]
            except (KeyError, TypeError):
                raise LoginError(STATUS_LOGIN_FAILED)

            self.user_info = ecrebo_user_store["whsmith"][user_id]
            merchant_identifier = credentials.get("merchant_identifier") or str(uuid.uuid4())
            self.identifier = {
                "card_number": credentials["card_number"],
                "merchant_identifier": merchant_identifier
            }
            self.user_info["credentials"].update(self.identifier)

        return

    def balance(self):
        """
        For each voucher in the mock user store, a mock voucher dict must be created.
        Each dict must have: "issued" (use today's date - 2 days), "code" and "expiry_date", which come from
        the mock user store for each of the voucher states i.e. earned, expired and redeemed.
        Redeemed vouchers (in order to be seen as such by Hermes) must also have a "redeem date"
        (just make this yesterday).
        Pass this list of voucher dicts to _make_balance_response as 'issued_vouchers' to mock ecrebo's real
        balance() method
        """
        issued_vouchers = []
        issued = arrow.now().shift(days=-2).format("YYYY-MM-DD")  # e.g. "2020-08-23"
        redeemed = arrow.now().shift(days=-1).format("YYYY-MM-DD")  # e.g. "2020-08-24"
        for earned_voucher in self.user_info["earned_vouchers"]:
            mock_voucher = self._make_mock_voucher(code=earned_voucher[0], expiry_date=earned_voucher[1],
                                                   issued=issued)
            issued_vouchers.append(mock_voucher)

        for expired_voucher in self.user_info["expired_vouchers"]:
            mock_voucher = self._make_mock_voucher(code=expired_voucher[0], expiry_date=expired_voucher[1],
                                                   issued=issued)
            issued_vouchers.append(mock_voucher)

        for redeemed_voucher in self.user_info["redeemed_vouchers"]:
            mock_voucher = self._make_mock_voucher(code=redeemed_voucher[0], expiry_date=redeemed_voucher[1],
                                                   issued=issued)
            mock_voucher["redeemed"] = redeemed
            issued_vouchers.append(mock_voucher)

        balance_response = self._make_balance_response(voucher_type=VoucherType.STAMPS, value=self.user_info['points'],
                                                       target_value=Decimal('5'), issued_vouchers=issued_vouchers)

        return balance_response

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []

    def register(self, credentials):
        self._validate_join_credentials(data=credentials)
        return {"message": "success"}

    @staticmethod
    def _make_mock_voucher(code: str, expiry_date: str, issued: str):
        mock_voucher = {
            "code": code,
            "expiry_date": expiry_date,
            "issued": issued,
        }

        return mock_voucher
