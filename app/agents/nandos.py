from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, IP_BLOCKED, TRIPPED_CAPTCHA
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Nandos(Miner):
    def login(self, credentials):
        query = 'https://www.nandos.co.uk/card/log-in?nocache=9232253217205040'
        data = {
            'email': credentials['email'],
            'password': credentials['password'],
            'op': 'Submit',
            'form_build_id': 'form-ZarY-CxUl0Q6yXiN1JYGdlQF1XLr20CFsayv9lotek8',
            'form_id': 'nandoscard_ui_log_in_form',
        }
        self.open_url(query, method='post', data=data)

        self.check_error('/card/log-in', (
            ('#content-header div h2', STATUS_LOGIN_FAILED, 'Status'),
            ('.messages', TRIPPED_CAPTCHA, "Error message\nOops, that wasn't the correct code"),
            ('.messages', IP_BLOCKED, "Error message\nOops, we've detected too many login attempts"),
            ('body > div > div.rc-anchor-content > div > div > div', STATUS_LOGIN_FAILED, 'ERROR'), ))

    def calculate_label(self, points):
        return self.calculate_tiered_reward(points, [
            (10, 'Red Reward'),
            (6, 'Orange Reward'),
            (3, 'Green Reward'),
        ])

    def balance(self):
        chili_wheel = self.browser.select('div.chilli-wheel-big')[0]
        points = extract_decimal(chili_wheel['class'][1][-2:])

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.calculate_label(points),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
