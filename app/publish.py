from app.encoding import JsonEncoder
import json
from settings import HADES_URL
import requests


class Publish(object):
    def post(self, url, data):
        headers = {'Content-type': 'application/json', }

        request = requests.post(HADES_URL + url, data=json.dumps(data, cls=JsonEncoder), headers=headers)
        # this should be async but its currently only working 50% of the time

        # if request.status_code not in [200, 201]:
        #     # TODO: log the issue
        #     pass

    def balance(self, balance):
        self.post("/balance", balance)

    def transactions(self, transactions):
        self.post("/transactions", transactions)
