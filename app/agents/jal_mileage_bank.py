import re

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class JalMileageBank(RoboBrowserMiner):
    is_login_successful = False
    login_url_reg_ex = re.compile(r"https\:.+getTopJSON_en\.do[^\"]+")
    points_reg_ex = re.compile(r"flyonPoint(.*?,)")
    balance_reg_ex = re.compile(r"mileBalance(.*?,)")

    def check_if_logged_in(self):
        try:
            login_cookie = self.browser.session.cookies['LOGIN']

            if login_cookie == "YES":
                self.is_login_successful = True
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception

    def _login(self, credentials):
        url = "https://www121.jal.co.jp/JmbWeb/ER/JMBmemberTop_en.do"
        data = {
            "country": "uk",
            "language": "en",
            "member_no": credentials['card_number'],
            "access_cd": credentials['pin'],
        }

        self.browser.open(url, method="post", data=data)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        source_txt = self.browser.parsed.prettify()
        account_url = self.login_url_reg_ex.findall(source_txt)[0]
        account_url = account_url.replace('amp;', '')

        self.browser.open(account_url)

        response_text = self.browser.parsed.text
        points = self.points_reg_ex.findall(response_text)[0]
        points = extract_decimal(points)
        value = self.balance_reg_ex.findall(response_text)[0]
        value = extract_decimal(value)

        return {
            'points': points,
            'value': value,
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
