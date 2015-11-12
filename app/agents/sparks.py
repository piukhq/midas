from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal


class Sparks(Miner):
    def login(self, credentials):
        self.open_url('https://www.marksandspencer.com/MSLogon')

        login_form = self.browser.get_form('Logon')
        login_form['logonId'] = credentials['email']
        login_form['logonPassword'] = credentials['password']
        self.browser.submit_form(login_form)

        self.open_url('https://www.marksandspencer.com/webapp/wcs/stores/servlet/MSAuthToken')

        self.check_error('/webapp/wcs/stores/servlet/LogonErrorView',
                         (('.messaging > ul > li'), STATUS_LOGIN_FAILED, "We're sorry but we don't recognise"))

        # The above isn't always enough to check for an error, sometimes we're just given an empty json response.
        if self.browser.response.text == '{}':
            raise LoginError(STATUS_LOGIN_FAILED)

        cookies = self.browser.session.cookies._cookies['www.marksandspencer.com']['/']
        auth_cookie = next(v for k, v in cookies.items() if k.startswith('MS_AUTH_TOKEN_'))

        self.headers['Authorization'] = 'MNSAuthToken {}'.format(auth_cookie.value)

    def balance(self):
        self.open_url('https://api.loyalty.marksandspencer.services/loyalty-service/api/users/status')
        data = self.browser.response.json()
        return {
            'points': Decimal(data['balance']),
            'value': Decimal('0'),
            'value_label': '',
        }
