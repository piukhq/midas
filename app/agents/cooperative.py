import re
from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, AgentError, UNKNOWN, INVALID_MFA_INFO, STATUS_ACCOUNT_LOCKED
from app.utils import extract_decimal
from decimal import Decimal
import arrow
from bs4 import BeautifulSoup

# TODO: add STATUS_ACCOUNT_LOCKED
# TODO: add negative transaction handling


class Cooperative(Miner):
    points_pattern = re.compile(r'<span class="wallet-x-value">([0-9.0-9]+)')
    logged_in_pattern = re.compile(r'("invalid loginID or password")')

    def login(self, credentials):

        headers = {'Referer':'https://membership.coop.co.uk/sign-in'}
        self.browser.open('https://cdns.gigya.com/gs/sso.htm?APIKey=3_150ZZS-BTm2rmX6o2Xe-hzYfRNzKJnG6pAWbx2LkAnJJifFqR0lWrgWkvWvJbVKo&version=2', headers=headers)

        headers = {'Referer': 'https://cdns.gigya.com/gs/APIProxy.html',
                   'Origin': 'https://cdns.gigya.com',
                   'Host': 'accounts.eu1.gigya.com',
                   }

        data = {'APIKey': '3_XJlLuE7OQJeVauunSRoum1W2XurDGBT6d0qKeA_8T3pHSOhKC4GtFWU-46aAmlsX',
                'loginID': credentials['email'],
                'password': credentials['password'],
                'authMode': 'cookie',
                'callback': 'gigya._.apiAdapters.web.callback',
                'sessionExpiration':'14400',
                'targetEnv':'jssdk',
                'includeUserInfo':'true',
                'gmid':'s%2Bsy1iz%2FuNFBjguOSOuAJKDC0Nyztu8iG1AHFukZRfU%3Ducid:4Y3pB1JNeL1KyJA6mId3gA%3D%3D',
                'sdk':'js_6.5.23',
                'format':'jsonp',
                'context':'R3835806672',
                'utf8': '%E2%9C%93',
                }

        self.browser.open('https://accounts.eu1.gigya.com/accounts.login?context=R3835806672&saveResponseID=R3835806672', method='post', headers=headers, data=data)

        headers = {'APIKey': '3_XJlLuE7OQJeVauunSRoum1W2XurDGBT6d0qKeA_8T3pHSOhKC4GtFWU-46aAmlsX',
                   'Referer': 'https://cdns.gigya.com/gs/APIProxy.html',
                   'Host': 'accounts.eu1.gigya.com',
                   'Accept': '*/*',
                   }
        self.browser.open('https://accounts.eu1.gigya.com/socialize.getSavedResponse?APIKey=3_XJlLuE7OQJeVauunSRoum1W2XurDGBT6d0qKeA_8T3pHSOhKC4GtFWU-46aAmlsX&saveResponseID=R3835806672&ucid=4Y3pB1JNeL1KyJA6mId3gA%3D%3D&sdk=js_6.5.23&format=jsonp&callback=gigya._.apiAdapters.web.callback&context=R3835806672', method='get', headers=headers)

        pretty_html = self.browser.parsed.prettify()
        try:
            login_fail = self.logged_in_pattern.findall(pretty_html)[0]
            if login_fail:
                raise LoginError(STATUS_LOGIN_FAILED)
        except IndexError:
            self.open_url('https://membership.coop.co.uk/ajax-calls/validate-signature?UID=cb710208dd084d37a94837d9c5fca0a1&UIDSignature=%2FzSnTuufeLxyzGnwr6w0kdzemhA%3D&signatureTimestamp=1482489324')

    def balance(self):
        self.open_url('https://membership.coop.co.uk/dashboard')
        points_html = self.browser.select('span.wallet-x-value')

        points_string = self.points_pattern.findall(str(points_html))[0]

        points = Decimal(points_string)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        # Commented for now since web page has changed and no transactions are available for us to test.
        # items = row.find_all("td")
        # return {
        #    "date": arrow.get(items[2].contents[0].strip(), 'DD MMMM YYYY'),
        #    "description": items[0].contents[0].strip(),
        #    "location": items[1].contents[0].strip(),
        #    "points": extract_decimal(items[3].contents[0].strip()),
        # }
        return None

    def scrape_transactions(self):
        self.open_url("https://www.membership.coop/transactions")
        return None # self.browser.select("#gridViewMemberTransactions tr")[1:]
