import re
from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED  # , STATUS_ACCOUNT_LOCKED
from decimal import Decimal
from app.utils import extract_decimal
import arrow

# TODO: add STATUS_ACCOUNT_LOCKED
# TODO: add negative transaction handling


class Cooperative(Miner):
    value_pattern = re.compile(r'<span class="wallet-x-value">([0-9.0-9]+)')
    points_pattern = re.compile(r'<span class="z-points-value">([0-9.0-9]+)')
    logged_in_pattern = re.compile(r'("invalid loginID or password")')

    def login(self, credentials):

        headers = {'Referer': 'https://membership.coop.co.uk/sign-in'}
        self.browser.open('https://cdns.gigya.com/gs/sso.htm?APIKey=3_150ZZS-BTm2rmX6o2Xe-hzYfRNzKJnG6pAWbx2LkAnJJifFq'
                          'R0lWrgWkvWvJbVKo&version=2', headers=headers)

        headers = {'Referer': 'https://cdns.gigya.com/gs/APIProxy.html',
                   'Origin': 'https://cdns.gigya.com',
                   'Host': 'accounts.eu1.gigya.com',
                   }

        data = {'APIKey': '3_XJlLuE7OQJeVauunSRoum1W2XurDGBT6d0qKeA_8T3pHSOhKC4GtFWU-46aAmlsX',
                'loginID': credentials['email'],
                'password': credentials['password'],
                'authMode': 'cookie',
                'callback': 'gigya._.apiAdapters.web.callback',
                'sessionExpiration': '14400',
                'targetEnv': 'jssdk',
                'includeUserInfo': 'true',
                'gmid': 's%2Bsy1iz%2FuNFBjguOSOuAJKDC0Nyztu8iG1AHFukZRfU%3Ducid:4Y3pB1JNeL1KyJA6mId3gA%3D%3D',
                'sdk': 'js_6.5.23',
                'format': 'jsonp',
                'context': 'R3835806672',
                'utf8': '%E2%9C%93',
                }

        self.browser.open('https://accounts.eu1.gigya.com/accounts.login?context=R3835806672&saveResponseID'
                          '=R3835806672', method='post', headers=headers, data=data)

        headers = {'APIKey': '3_XJlLuE7OQJeVauunSRoum1W2XurDGBT6d0qKeA_8T3pHSOhKC4GtFWU-46aAmlsX',
                   'Referer': 'https://cdns.gigya.com/gs/APIProxy.html',
                   'Host': 'accounts.eu1.gigya.com',
                   'Accept': '*/*',
                   }
        self.browser.open('https://accounts.eu1.gigya.com/socialize.getSavedResponse?APIKey=3_XJlLuE7OQJeVauunSRoum1W2X'
                          'urDGBT6d0qKeA_8T3pHSOhKC4GtFWU-46aAmlsX&saveResponseID=R3835806672&ucid=4Y3pB1JNeL1KyJA6mId3'
                          'gA%3D%3D&sdk=js_6.5.23&format=jsonp&callback=gigya._.apiAdapters.web.callback&context=R38358'
                          '06672', method='get', headers=headers)

        pretty_html = self.browser.parsed.prettify()
        try:
            login_fail = self.logged_in_pattern.findall(pretty_html)[0]
            if login_fail:
                raise LoginError(STATUS_LOGIN_FAILED)
        except IndexError:
            timestamp = re.compile(r'"signatureTimestamp":\s"(\d+)"').findall(pretty_html)[0]
            uid = re.compile(r'"UID":\s"(.+)"').findall(pretty_html)[0]
            uid_signature = re.compile(r'"UIDSignature":\s"(.+)"').findall(pretty_html)[0]
            self.open_url('https://membership.coop.co.uk/ajax-calls/validate-signature?UID=' +
                          uid + '&UIDSignature=' + uid_signature + '&signatureTimestamp=' + timestamp)

    def balance(self):
        self.open_url('https://membership.coop.co.uk/dashboard')
        value_html = self.browser.select('span.wallet-x-value')

        value_string = self.value_pattern.findall(str(value_html))[0]

        value = Decimal(value_string)

        return {
            'points': value,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        date = row.find_all("th")
        return {
            "date": arrow.get(date[0].contents[0].strip(), 'DD MMMM YYYY'),
            "description": '',
            "value": Decimal(items[0].contents[0].strip('£')),
            "points": extract_decimal(items[2].contents[0].strip()),
        }

    def scrape_transactions(self):
        transactions = []
        self.open_url("https://membership.coop.co.uk/transactions")
        list_all = self.browser.select(".transaction-row")
        for row in list_all:
            items = row.find_all("td")
            try:
                items[2].contents[0]
                transactions.append(row)
            except:
                pass
        return transactions
