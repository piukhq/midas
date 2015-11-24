from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal
import arrow


class MyMail(Miner):
    def login(self, credentials):
        # AngularJS sets this header as cross-site request forgery protection. Without it, we can't log in.
        # The cookie is obtained by visiting the login page.
        self.open_url('https://www.mymail.co.uk/login')
        self.headers = {
            'X-XSRF-TOKEN': self.browser.session.cookies._cookies['www.mymail.co.uk']['/']['XSRF-TOKEN'].value
        }

        # The login request itself contains json data and is sent by AngularJS.
        data = {
            'rememberMe': True,
            'username': credentials['email'],
            'password': credentials['password'],
        }
        self.open_url('https://www.mymail.co.uk/login', method='post', json=data)

        # We have to request account data to tell if we were successfully logged in or not.
        self.open_url('https://www.mymail.co.uk/defaultMember')

        if self.browser.url == 'https://www.mymail.co.uk/login':
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        # Sometimes the request to /defaultMember seems to fail.
        if self.browser.url.startswith('https://www.mymail.co.uk/home'):
            self.open_url('https://www.mymail.co.uk/defaultMember')

        data = self.browser.response.json()

        points = Decimal(data['points'])
        reward = self.calculate_tiered_reward(points, [
            (9500, '£25 Gift Card'),
            (5800, '£15 Gift Card'),
            (3900, '£10 Gift Card'),
            (2000, '£5 Gift Card'),
            (1000, '£2.50 Gift Card'),
        ])

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': reward,
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['bankedDate'], 'DD / MMM / YYYY'),
            'description': row['description'],
            'points': Decimal(row['availablePoints']),
        }

    def transactions(self):
        self.open_url('https://www.mymail.co.uk/my-account/points-history/0/10')
        data = self.browser.response.json()

        return [self.hashed_transaction(row) for row in data['paginatedEarnedMailRewards']]
