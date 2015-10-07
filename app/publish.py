from app.encoding import JsonEncoder
import json
import grequests
from settings import HADES_URL


class Publish(object):
    def post(self, url, data):
        headers = {'Content-type': 'application/json', }
        request = grequests.post(HADES_URL + url, data=json.dumps(data, cls=JsonEncoder), headers=headers)

        # if request.status_code not in [200, 201]:
        #     # TODO: log the issue
        #     pass

    def balance(self, balance):
        self.post("/balance", balance)

    def transactions(self, transactions):
        self.post("/transactions", transactions)
