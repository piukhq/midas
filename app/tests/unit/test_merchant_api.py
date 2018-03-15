import json

import flask

from app.agents.base import MerchantApi
from unittest import mock, TestCase


class TestMerchantApi(TestCase):
    def setUp(self):
        pass

    @mock.patch.object(MerchantApi, '_sync_outbound')
    def test_outbound_handler(self, mock_sync_outbound):
        m = MerchantApi(1, 1)
        mock_sync_outbound.return_value = flask.Response(json.dumps({"stuff": 'more stuff'}),
                                                         content_type="application/json")

        resp = m._outbound_handler({}, 1, 'update')

        self.assertEqual({"stuff": 'more stuff'}, resp)
