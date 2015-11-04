import arrow
from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal


class Avios(Miner):
    point_conversion_rate = Decimal('0.0068')

    def login(self, credentials):
        self.open_url("https://www.avios.com/gb/en_gb/")
        login_form = self.browser.get_form(action='https://www.avios.com/my-account/login-process')
        login_form['j_username'].value = credentials['email']
        login_form['j_password'].value = credentials['password']
        self.browser.submit_form(login_form)
        if self.browser.url != 'https://www.avios.com/gb/en_gb/':
            login_form = self.browser.get_form(action='/my-account/login-process')
            login_form['j_username'].value = credentials['email']
            login_form['j_password'].value = credentials['password']
            self.browser.submit_form(login_form)

        if self.browser.url != 'https://www.avios.com/gb/en_gb/':
            login_form = self.browser.get_form(action='/my-account/login-process')
            login_form['j_username'].value = credentials['email']
            login_form['j_password'].value = credentials['password']
            self.browser.submit_form(login_form)

        if self.browser.url != 'https://www.avios.com/gb/en_gb/':
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        points = extract_decimal(self.browser.find('div', {'id': 'acc-status'}).find('strong').text)
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        columns = row.select('td')
        positive_points = columns[2].text
        negative_points = columns[3].text

        if positive_points and negative_points:
            points = extract_decimal(positive_points) - extract_decimal(negative_points)
        elif positive_points:
            points = extract_decimal(positive_points)
        elif negative_points:
            points = extract_decimal('-{}'.format(negative_points))
        else:
            points = extract_decimal('')

        return {
            'date': arrow.get(columns[0].text, 'DD/MM/YYYY'),
            'description': columns[1].text,
            'points': points
        }

    def transactions(self):
        self.open_url("https://www.avios.com/gb/en_gb/my-account/your-avios-account?from=accNav")
        transactions = self.browser.find('div', {'id': 'transactions'}).select('table tbody tr')
        return [self.hashed_transaction(transaction) for transaction in transactions]
