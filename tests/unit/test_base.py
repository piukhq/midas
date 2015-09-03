from app.agents.base import Miner
from app.agents.exceptions import MinerError, LoginError
import arrow
import httpretty
from unittest import mock, TestCase


class TestBase(TestCase):
    @mock.patch.object(Miner, 'parse_transaction')
    def test_hashed_transaction(self, mocked_parse_transaction):
        transaction = {
            "date": arrow.get('2013-09-30T15:34:00.000-07:00'),
            "title": "Clothes purchase",
            "points": 44
        }
        mocked_parse_transaction.return_value = transaction
        m = Miner(1)
        transaction = m.hashed_transaction(transaction)

        self.assertEqual(transaction["hash"], "d9d7b6f57cd5354bb69432165c1c2969")

    def test_attempt_login_exception(self):
        m = Miner(3)
        with self.assertRaises(MinerError) as e:
            m.attempt_login(credentials={})
        self.assertEqual(e.exception.name, "RETRY_LIMIT_REACHED")

    @mock.patch.object(Miner, 'login')
    def test_attempt_login(self, mocked_login):
        m = Miner(2)

        m.attempt_login(credentials={})
        self.assertTrue(mocked_login.called)

    def test_check_error(self):
        mock_instance = mock.create_autospec(Miner)
        browser = mock.MagicMock()
        browser.url = "http://www.test.com/test.aspx?sdf=34"
        mock_instance.browser = browser

        # the method should do nothing when called
        Miner.check_error(mock_instance, "/HomeSecurityLayer.aspx", "", ())

    def test_path_check_error_exception(self):
        mock_instance = mock.create_autospec(Miner)
        browser = mock.MagicMock()
        browser.url = "http://www.test.com/HomeSecurityLayer.aspx"
        mock_instance.browser = browser

        with self.assertRaises(LoginError):
            Miner.check_error(mock_instance, "/HomeSecurityLayer.aspx",
                              "", (("INVALID_MFA_INFO", "The details"), ))


class TestOpenURL(TestCase):
    @httpretty.activate
    def test_open_url_error_status(self):
        httpretty.register_uri(httpretty.GET, "http://foo-api.com/", status=500)

        m = Miner(2)
        with self.assertRaises(MinerError):
            m.open_url("http://foo-api.com/")