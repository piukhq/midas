import arrow
from app.agents.base import Miner
from app.utils import extract_decimal


class Avios(Miner):
    def login(self, credentials):
        self.open_url("http://www.avios.com/gb/en_gb/")
        login_form = self.browser.get_form(action='https://www.avios.com/my-account/login-process')
        login_form['j_username'].value = credentials['username']
        login_form['j_password'].value = credentials['password']
        self.browser.submit_form(login_form)
        print(True)
        login_form = self.browser.get_form(action='/my-account/login-process')
        login_form['j_username'].value = credentials['username']
        login_form['j_password'].value = credentials['password']
        self.browser.submit_form(login_form)
        print(True)
        login_form = self.browser.get_form(action='/my-account/login-process')
        login_form['j_username'].value = credentials['username']
        login_form['j_password'].value = credentials['password']
        self.browser.submit_form(login_form)
        print(True)

    def balance(self):
        points = self.browser.find('div', {'id': 'acc-status'}).find('strong').text
        return {
            "amount": extract_decimal(points)
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
