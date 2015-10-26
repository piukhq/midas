from app.agents.base import Miner
from app.agents.exceptions import STATUS_ACCOUNT_LOCKED, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
import arrow


class Boots(Miner):
    def login(self, credentials):
        query = 'https://www.boots.com/webapp/wcs/stores/servlet/LoginRequestDispatcher'
        data = {
            'storeId': '10052',
            'reLogonURL': 'LogonForm',
            'URL': ('/webapp/wcs/stores/servlet/ADCAccountSummary?catalogId=10552&langId=-1&storeId=10052'
                    '&krypto=KaymTKtLMpduxnlSzanOzfyb0aQbcMtqR8beC08WV1OdWxhhD3AETPwwqqGZ6TlP26fQ2DYU0OCSl'
                    'KDlRUUsufo4WJiFvxRcZjI8sg7APBilxu8YivmvRDC3s1z6GXiL'),
            'logonId': credentials['email'],
            'logonPassword': credentials['password'],
        }

        self.browser.open(query, method='post', data=data)

        selector = "#formErrorContainer > div > div > ul > li > a"
        self.check_error("/webapp/wcs/stores/servlet/LoginRequestDispatcher",
                         ((selector, STATUS_LOGIN_FAILED, "The email address and password you entered has not been"),
                          (selector, STATUS_ACCOUNT_LOCKED, "You have exceeded the maximum number of attempts")))

    def balance(self):
        return {
            "points": extract_decimal(self.browser.select(".pointsValue")[0].contents[0]),
            "value": extract_decimal(self.browser.select(".pointsValue")[1].contents[0])
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[0].contents[0], 'DD/MM/YYYY'),
            "description": items[1].contents[0],
            "points": extract_decimal(items[3].contents[0]),
        }

    def transactions(self):
        rows = self.browser.select(".transactionsList tr")[1:]
        return [self.hashed_transaction(row) for row in rows]
