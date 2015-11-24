from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class PriorityGuestRewards(Miner):
    def login(self, credentials):
        url = 'https://www.priorityguestrewards.com.au/account/acc/loginTrans.php'
        data = {
            'accountType': 'PA',
            'userID': credentials['username'],
            'loginpass': credentials['password'],
        }

        self.browser.open(url, method='post', data=data)

        self.check_error('/login/',
                         (('div.alert.alert-danger', STATUS_LOGIN_FAILED, '×\r\n        We are having trouble'), ))

    def balance(self):
        points = extract_decimal(self.browser.select('#member-account-status-box > div > div > span.bold')[2].text)

        reward = self.calculate_tiered_reward(points, [
            (150, 'Free room'),
            (80, '$50 gift card'),
            (40, 'Free main meal'),
            (30, 'Free breakfast'),
            (20, 'Two standard drinks'),
        ])

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': reward,
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('td')

        return {
            'date': arrow.get(data[1].text.strip(), 'DD/MM/YYYY'),
            'description': data[2].text.strip(),
            'points': extract_decimal(data[3].text.strip()),
            'location': data[0].text.strip(),
        }

    def transactions(self):
        rows = self.browser.select('#dashboard-activities-box > div > div > table > tbody > tr')
        return [self.hashed_transaction(row) for row in rows]
