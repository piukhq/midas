from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal


class ClubIndividual(RoboBrowserMiner):
    is_login_successful = False

    def _check_if_logged_in(self):
        try:
            check_selector = self.browser.select('td')[0].text
            if check_selector.startswith('Cardholder'):
                self.is_login_successful = True
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception

    def login(self, credentials):
        try:
            self.browser.open('http://statement.club'
                              '-individual.co.uk/points.aspx?id=' + credentials['card_number'])
        except Exception:
            LoginError(UNKNOWN)

        self._check_if_logged_in()

    def balance(self):
        points = self.browser.select('td')[5].text
        points = extract_decimal(points)
        value = self.browser.select('td')[7].text
        value = extract_decimal(value)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
