import json

from flask_testing import TestCase
from app import create_app
from unittest import mock


data = json.dumps({"UUID": "7e54d768-033e-40fa-999a-76c21bdd9c42",
                        "email": "ncostaa@bink.com",
                        "account_number": 56789,
                        "third_party_identifier": "8v5zjgey0xd7k618x43wmpo2139lq4r8"
                        })

headers = {'Content-type': 'application/json',
           'transaction': "success",
           'Authorization': 'Bearer ' + "sgadadiuaHOAHSOOAH"}


class TestBplCallback(TestCase):

    def create_app(self):
        return create_app(self, )

    @mock.patch('app.bpl_callback.requires_auth', return_value=True)
    def test_post(self, mock_flask_oidc):

        url = "join/bpl/bpl-trenette"
        response = self.client.post(url, data=data, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'message': 'success'})
