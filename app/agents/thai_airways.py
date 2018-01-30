from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, STATUS_ACCOUNT_LOCKED
from app.utils import extract_decimal
from decimal import Decimal
import base64


class ThaiAirways(RoboBrowserMiner):
    token = None
    member_id = None

    def is_login_successful(self):
        return self.browser.response.json()['success']

    def check_errors_in_login_ajax(self):
        data = self.browser.response.json()["data"]

        if "mwerror:ErrDesc" in data.keys():
            member_not_exist = "Member does not exists" in data["mwerror:ErrDesc"]
        else:
            member_not_exist = False

        if "ns0:Message" in data.keys():
            bad_pin = "Incorrect Pin Number" in data["ns0:Message"]
            locked_account = "Account is locked" in data["ns0:Message"]
        else:
            bad_pin = False
            locked_account = False

        if locked_account:
            raise LoginError(STATUS_ACCOUNT_LOCKED)

        if member_not_exist or bad_pin:
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self, credentials):
        url = 'https://www.thaiairways.com/app/rop/web/check_pin'
        data = {
            'member_id': credentials['username'],
            'member_pin': base64.b64encode(bytes(credentials['password'], 'utf-8')),
        }
        self.member_id = credentials['username']

        self.headers["Accept"] = "application/json"
        self.headers["Content - Type"] = "application/x-www-form-urlencoded"
        self.headers["Host"] = "www.thaiairways.com"
        self.headers["Origin"] = "https://www.thaiairways.com"
        self.headers["Referer"] = "https://www.thaiairways.com/en_TH/rop/index.page"
        self.headers["X-Requested-With"] = "XMLHttpRequest"

        self.open_url(url, method='post', data=data, read_timeout=10)

        if "token" in self.browser.response.json().keys():
            self.token = self.browser.response.json()['token']

        self.check_errors_in_login_ajax()

    def balance(self):
        url = "https://www.thaiairways.com/app/rop/web/get_current_mileage"
        data = {
            "member_id": self.member_id,
            "token": self.token
        }
        self.open_url(url, method="post", data=data)

        points = extract_decimal(self.browser.response.json()["data"]["CurrentMileageRS"]["CurrentMileage"])
        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        '''
        url = 'http://www.thaiair.com/AIP_ROP/MileageStatement'
        data = {
            "mfwdType": "servlet",
            "mfwdLink": "AIP_ROP%2FMileageStatement",
            "period": "-11",
            "stmLanguagePref": "en",
        }
        '''
        return []
