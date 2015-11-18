from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, STATUS_ACCOUNT_LOCKED, INVALID_MFA_INFO
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Starwood(Miner):
    def login(self, credentials):
        self.open_url('https://www.starwoodhotels.com/preferredguest/account/starpoints/index.html')

        login_form = self.browser.get_form('loginForm')
        login_form['login'].value = credentials['email']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        self.check_error('/preferredguest/account/sign_in.html',
                         (('#genericBEError', STATUS_LOGIN_FAILED, 'Correct any errors'),
                          ('#genericBEError', STATUS_ACCOUNT_LOCKED, 'Your account is locked'), ))

        # Refreshing does not give you a new question. Putting in the wrong answer does.
        for x in range(0, 3):
            mfa_form = self.browser.get_form('securityQForm')
            mfa_form['securityAnswer'].value = credentials['favourite_place']
            self.browser.submit_form(mfa_form)

            if self.browser.url != 'https://www.starwoodhotels.com/preferredguest/account/answerSecurityQuestion.html':
                break
        else:
            raise LoginError(INVALID_MFA_INFO)

    def balance(self):
        points = extract_decimal(self.browser.select('#primary1 > h1 > span')[0].text.strip())

        reward = self.calculate_tiered_reward(points, [
            (14000, '$150 amazon gift card'),
            (9500, '$100 amazon gift card'),
            (5000, '$50 amazon gift card'),
        ])

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': reward,
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