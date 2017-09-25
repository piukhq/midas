from decimal import Decimal

import arrow

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class PriorityGuestRewards(RoboBrowserMiner):
    is_login_successful = False

    def check_if_logged_in(self):
        account_url = "https://www.priorityguestrewards.com/account/profile.php"

        try:
            self.open_url(account_url)
            account_info = self.browser.select('.info-row b')[0].text
            if account_info:
                self.is_login_successful = True
        except:
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self, credentials):
        url = 'https://bookings.priorityguestrewards.com/plugin/loginTrans'
        data = {
            'userID': credentials['username'],
            'loginpass': credentials['password'],
        }

        self.open_url(url, method='post', data=data)
        self.check_if_logged_in()

    def balance(self):
        points = self.browser.select('.info-row b')[0].text
        points = extract_decimal(points)

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

    def scrape_transactions(self):
        return self.browser.select('table tbody tr')
