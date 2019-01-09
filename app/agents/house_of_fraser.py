from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal
import re
import json


class HouseOfFraser(SeleniumMiner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        form = 'https://www.houseoffraser.co.uk/account/validatelogin'
        self.open_url(
            form,
            method='post',
            json={
                'Email': credentials['email'],
                'Password': credentials['password']
            })

    def balance(self):
        self.open_url('https://www.houseoffraser.co.uk/recognition/recognitionsummary')
        match = re.search(
            r"^\s*recognitionsummary: new hof\.models\.RecognitionSummaryViewModel\((.*)\),.*$",
            self.browser.response.text,
            re.MULTILINE
        )
        data = json.loads(match.groups()[0])
        value = Decimal(data['RewardsBalance'])
        return {
            'points': Decimal(data['PointBalance']),
            'value': value,
            'value_label': '£{}'.format(value),
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []

    def _raise_agent_exception(self, exc):
        if exc.response.status_code == 422:
            raise LoginError(STATUS_LOGIN_FAILED)
        super()._raise_agent_exception(exc)
