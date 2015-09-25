from app.encoding import JsonEncoder
import json
from requests_futures.sessions import FuturesSession
from settings import HADES_URL


class Publish:
    def __init__(self):
        self.session = FuturesSession()

    def post(self, url, data):
        headers = {'Content-type': 'application/json', }
        self.session.post(HADES_URL + url, data=json.dumps(data, cls=JsonEncoder), headers=headers)

    def balance(self, balance):
        self.post("/balance", balance)

    def transactions(self, transactions):
        self.post("/transactions", transactions)
