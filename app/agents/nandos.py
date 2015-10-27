from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, STATUS_ACCOUNT_LOCKED
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
        self.browser.open(query, method='post', data=data)

        self.check_error('/card/log-in', (('#content-header div h2', STATUS_LOGIN_FAILED, 'Status'),))

    def balance(self):
        reward_boxes = self.browser.select('.reward-box-value')
        points = sum(extract_decimal(x.text) for x in reward_boxes)
        return {
            'points': points
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