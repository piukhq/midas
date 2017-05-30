from decimal import Decimal

from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, STATUS_ACCOUNT_LOCKED, LoginError
from app.utils import extract_decimal


class Debenhams(Miner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        self.open_url('https://www.debenhams.com'
                      '/webapp/wcs/stores/servlet/BeautyClubDashboard'
                      '?langId=-1&storeId=10701&catalogId=10001&headerLink=true&showLoginOnly=true')

        url = 'https://www.debenhams.com/webapp/wcs/stores/servlet/Logon'
        data = {
            'isUserSupplied': 'Y',
            'reLogonURL': ('https://www.debenhams.com'
                           '/webapp/wcs/stores/servlet/BeautyClubDashboard'
                           '?catalogId=10001&showLoginOnly=true&langId=-1&storeId=10701'),
            'URL': ('OrderItemMove'
                    '?page=account&URL=OrderCalculate%3FURL%3DBeautyClubSetupCustomer'
                    '&calculationUsageId=-1&calculationUsageId=-2&calculationUsageId=-7&bcLogin=true'),
            'logonId': credentials['email'],
            'logonPassword': credentials['password'],
        }
        self.open_url(url, method='post', data=data)

        # can't use check_error because the url path is the same regardless of login failure or success.
        error = self.browser.select('.error')
        if error and error[0].get_text().strip().startswith("We can't find an account"):
            raise LoginError(STATUS_LOGIN_FAILED)

        elif error and error[0].get_text().strip().startswith('Account locked'):
            raise LoginError(STATUS_ACCOUNT_LOCKED)


        error = self.browser.select('.error-message')
        if error and error[0].get_text().strip().startswith('Password incorrect'):
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        self.open_url('https://www.debenhams.com/wcs/resources/store/10701/person/@self/BCReg/card')
        json = self.browser.response.json()

        points = Decimal(json['pointsBalance'])
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
            'balance': extract_decimal(json['availableToSpend']),
        }

    @staticmethod
    def parse_transaction(row):
        return None

    def scrape_transactions(self):
        # we need some transactions in the test account before we can see the format of 'transactionHistory'.
        #
        # self.open_url('https://www.debenhams.com'
        #               '/wcs/resources/store/10701/person/@self/BCReg/card/history/wallet/points')
        # json = self.browser.response.json()
        # transactions = json['transactionHistory']
        return None
