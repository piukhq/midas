from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Decathlon(Miner):
    def login(self, credentials):
        #self.open_url('https://www.decathlon.co.uk/en/loginPage')

        selector = ''
        self.check_error('', ((selector, STATUS_LOGIN_FAILED, ''),))

    def balance(self):
        self.open_url('')

        point_holder = self.browser.select('')[0]
        return {
            'points': extract_decimal(point_holder.text)
        }

    @staticmethod
    def parse_transaction(row):
        raise NotImplementedError()

    def transactions(self):
        self.open_url('')
        rows = self.browser.select('')
        return [self.hashed_transaction(row) for row in rows]
