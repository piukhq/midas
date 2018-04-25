from decimal import Decimal

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED


class Sparks(RoboBrowserMiner):
    is_login_successful = False
    auth_token = ''

    def _check_if_logged_in(self):
        cookies = self.browser.session.cookies

        if cookies.get('IS_LOYALTY_USER_COOKIE'):
                self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def get_auth_token(self):
        self.headers['Host'] = "www.marksandspencer.com"
        self.headers['Referer'] = "https://www.marksandspencer.com/" \
                                  "MSNorth?langId=-24&storeId=10151"
        self.browser.open("https://www.marksandspencer.com/"
                          "webapp/wcs/stores/servlet/MSAuthToken")

        self.auth_token = self.browser.response.json()['token']

    def balance_preparation(self):
        self.get_auth_token()

        self.headers['Host'] = "api.loyalty.marksandspencer.services"
        self.headers['Referer'] = "https://api.loyalty.marksandspencer.serv" \
                                  "ices/loyalty-service/static/proxy-cors.html"
        self.headers['Authorization'] = 'MNSAuthToken ' + self.auth_token

    def login(self, credentials):
        url = 'https://www.marksandspencer.com/MSLogon'
        data = {
            'storeId': '10151',
            'langId': '-24',
            'catalogId': '10051',
            'fromOrderId': '*',
            'toOrderId': '.',
            'deleteIfEmpty': '*',
            'createIfEmpty': '1',
            'calculationUsageId': '-1',
            'updatePrices': 0,
            'previousPage': 'logon',
            'forgotPasswordURL': 'MSResForgotPassword',
            'rememberMe': 'true',
            'resJSON': 'true',
            'reLogonURL': 'MSResLogin',
            'resetConfirmationViewName': 'MSPwdEmailConfirmModalView',
            'errorViewName': 'MSResLogin',
            'continueSignIn': '1',
            'migrateUserErrorMsg': 'MS_MIGRAT_HEADERERR_MSG',
            'returnPage': 'MSUserLoyaltyOptInView',
            'URL': 'webapp/wcs/stores/servlet/MSSecureOrdercalculate'
                   '?catalogId=10051&langId=-24&mergeStatus=&storeId='
                   '10151&URL=https://www.marksandspencer.com/webapp/'
                   'wcs/stores/servlet/TopCategoriesDisplayView?'
                   'storeId=10151&langId=-24&catalogId=10051&ddkey'
                   '=https%3ALogoff&page=ACCOUNT_LOGIN',
            'orderMove': "/webapp/wcs/stores/servlet/OrderItemMove?"
                         "calculationUsageIdentifier=MSLoginModalDisplay"
                         "_orderMove&catalogId=10051&langId=-24&mergeStatus"
                         "=&storeId=10151&toOrderId=.**.&URL=OrderCalculate?U"
                         "RL=https://www.marksandspencer.com/webapp/wcs/stores"
                         "/servlet/TopCategoriesDisplayView?storeId=10151&"
                         "langId=-24&catalogId=10051&ddkey=https%3ALogoff",
            'logonId': credentials['email'],
            'logonPassword': credentials['password']
        }

        self.browser.open(url, data=data, method='post')
        self._check_if_logged_in()

    def balance(self):
        self.balance_preparation()
        self.open_url('https://api.loyalty.marksandspencer.services'
                      '/loyalty-service/api/users/status')

        data = self.browser.response.json()

        return {
            'points': Decimal(data['balance']),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        # self.open_url('https://portal.prepaytec.com/chopinweb/scareMyStatement.do')
        # transaction_table = self.browser.select('table.txnHistory')
        return []
