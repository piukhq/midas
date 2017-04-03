from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, AgentModifiedError
from app.utils import extract_decimal
from decimal import Decimal
from urllib.parse import urlsplit
import time
import re


class Hyatt(Miner):

    def get_csrf(self):
        import re
        import json
        self.open_url("https://hyatt.com/bin/atgProfile?_=" + str(
            int(time.time())))
        res = str(self.browser.state.parsed)
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', res)
        obj = json.loads(cleantext)

        return obj["csrf"]
    # def get_csrf(self)

    def is_login_failed(self):
        parts = urlsplit(self.browser.url)
        error_url = "/content/gp/en/signin-error.html"
        return error_url == parts.path
    # def is_login_failed(self)

    def login(self, credentials):
        self.browser.open("https://hyatt.com/atg-api/auth/", method="POST", data={
            "csrf": self.get_csrf(),
            "username": credentials["username"],
            "password": credentials["password"]
        }, headers={
            "origin": "https://www.hyatt.com",
            "Referer": "https://www.hyatt.com/",
        })

        if self.is_login_failed():
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        # data is in the header
        selector = '.admin-row .dd-menu .pc2 > dl.definition-table'
        pointsTable = self.browser.select(selector)

        if (len(pointsTable) != 2):
            raise AgentModifiedError("End-site has been modified")

        dataTable = str(pointsTable[1]).replace("\n", "")
        expr = '<dt>Current\sPoints:</dt><dd>(\d+)</dd>'
        searched = re.search(expr, dataTable, re.IGNORECASE)

        if len(searched.groups()) != 1:
            raise AgentModifiedError("End-site has been modified")

        points = searched.group(1)  # matched points data

        return {
            'points': extract_decimal(points),
            'value': Decimal('0'),
            'value_label': '',
        }

    def scrape_transactions(self):
        return None
