from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from http.cookiejar import Cookie
from decimal import Decimal


class GourmetBurgerKitchen(Miner):
    def login(self, credentials):
        self.headers = {
            'X-Requested-With': 'XMLHttpRequest',
        }

        self.open_url('http://www.gbk.co.uk/a/bootstrap', method='post', data={
            'deviceToken': '9e7c56ef47aed4f7296f43a1ac005d0e',
            'platform': 'web',
            'platformVersion':
                '5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.75 Safari/537.36',
            'appId': '5',
            'model': 'Linux x86_64',
            'frameworkVersion': '1',
            'appVersion': '1',
        })

        response = self.browser.response.json()

        c = self.browser.session.cookies._cookies['www.gbk.co.uk']['/']['laravel_session']
        self.browser.session.cookies.set_cookie(Cookie(
            c.version, 'accessToken', response['accessToken'], c.port, c.port_specified, c.domain, c.domain_specified,
            c.domain_initial_dot, c.path, c.path_specified, c.secure, c.expires, c.discard, c.comment, c.comment_url,
            None, c.rfc2109))

        self.open_url('http://www.gbk.co.uk/a/login', method='post', data={
            'credentialsType': 'email',
            'email': credentials['email'],
            'pinCode': credentials['pin'],
        })

        response = self.browser.response.json()

        if 'error' in response:
            message = response['message']
            if message == 'User account not found.':
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)

    def balance(self):
        self.open_url('http://www.gbk.co.uk/profile')
        stamp_list_items = self.browser.select('#myGBKTab > div.col-xs-12.col-md-8 > div.userProfile-visits > ul li')
        stamped_count = len([stamp for stamp in stamp_list_items if 'stamped' in stamp['class']])
        return {
            'points': Decimal(stamped_count),
            'value': Decimal('0'),
            'value_label': self.calculate_tiered_reward(stamped_count, [
                (5, 'Free burger'),
                (3, 'Free milkshake'),
                (1, 'Free side'),
            ])
        }

    def parse_transaction(row):
        raise NotImplementedError

    def scrape_transactions(self):
        raise NotImplementedError
