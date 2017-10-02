from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal


class GourmetBurgerKitchen(Miner):
    is_login_successful = False

    def login(self, credentials):
        self.headers['X-Requested-With'] = 'XMLHttpRequest'
        self.headers['Host'] = 'order.gbk.co.uk'
        self.headers['Origin'] = 'https://order.gbk.co.uk'
        self.headers['Referer'] = 'https://order.gbk.co.uk/login'

        data = {
            'email': credentials['email'],
            'passcode': credentials['pin']
        }
        self.browser.open('https://order.gbk.co.uk/a/login', method='post', data=data)

        response = self.browser.response.json()

        if response['requestInfo']['accessTokenStatus'] == 'anonymous':
            raise LoginError(STATUS_LOGIN_FAILED)
        elif response['requestInfo']['accessTokenStatus'] == 'authenticated':
            self.is_login_successful = True

    def balance(self):
        self.open_url('https://order.gbk.co.uk/profile')
        csrf_token = self.browser.select('meta[name=csrf-token]')[0]['content']
        self.headers['X-CSRF-Token'] = csrf_token
        self.open_url('https://order.gbk.co.uk/a/loyalty')
        current_stamps_filled = self.browser.response.json()['stampCard']['currentProgress']
        return {
            'points': Decimal(current_stamps_filled),
            'value': Decimal('0'),
            'value_label': self.calculate_tiered_reward(current_stamps_filled, [
                (5, 'Free burger'),
                (3, 'Free milkshake'),
                (1, 'Free side'),
            ])
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
