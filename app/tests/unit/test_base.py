from app.agents.base import Miner, format_plural_label
from app.agents.exceptions import AgentError, LoginError
from decimal import Decimal
import arrow
import httpretty
import re
from unittest import mock, TestCase


class TestBase(TestCase):
    @mock.patch.object(Miner, 'parse_transaction')
    def test_hashed_transaction(self, mocked_parse_transaction):
        transaction = {
            "date": arrow.get('2013-09-30T15:34:00.000-07:00'),
            "description": "Clothes purchase",
            "points": 44
        }
        mocked_parse_transaction.return_value = transaction
        m = Miner(1, 2)
        transaction = m.hashed_transaction(transaction)

        self.assertEqual(transaction["hash"], "b7f2ce62c8b9007008d8034e8d39a87d")

    def test_attempt_login_exception(self):
        m = Miner(3, 2)
        with self.assertRaises(AgentError) as e:
            m.attempt_login(credentials={})
        self.assertEqual(e.exception.name, "RETRY_LIMIT_REACHED")

    @mock.patch.object(Miner, 'login')
    def test_attempt_login(self, mocked_login):
        m = Miner(2, 2)

        m.attempt_login(credentials={})
        self.assertTrue(mocked_login.called)

    def test_check_error(self):
        mock_instance = mock.create_autospec(Miner)
        browser = mock.MagicMock()
        browser.url = "http://www.test.com/test.aspx?sdf=34"
        mock_instance.browser = browser

        # the method should do nothing when called
        Miner.check_error(mock_instance, "/HomeSecurityLayer.aspx", ())

    def test_path_check_error_exception(self):
        mock_instance = mock.create_autospec(Miner)
        browser = mock.MagicMock()
        browser.url = "http://www.test.com/HomeSecurityLayer.aspx"
        mock_instance.browser = browser

        with self.assertRaises(LoginError):
            Miner.check_error(mock_instance, "/HomeSecurityLayer.aspx",
                              (("", "INVALID_MFA_INFO", "The details"), ))

    def test_default_point_conversion(self):
        m = Miner(1, 1)
        value = m.calculate_point_value(Decimal('100'))
        self.assertEqual(Decimal('0'), value)

    def test_point_conversion(self):
        m = Miner(1, 1)
        m.point_conversion_rate = Decimal('0.5')
        value = m.calculate_point_value(Decimal('25'))
        self.assertEqual(Decimal('12.50'), value)

    def test_format_plural_label(self):
        self.assertEqual('0 vouchers', format_plural_label(0, 'voucher', 'vouchers'))
        self.assertEqual('1 voucher', format_plural_label(1, 'voucher', 'vouchers'))
        self.assertEqual('2 vouchers', format_plural_label(2, 'voucher', 'vouchers'))


class TestOpenURL(TestCase):
    @httpretty.activate
    def test_open_url_error_status(self):
        httpretty.register_uri(httpretty.GET, "http://foo-api.com/", status=500)
        m_cls = Miner
        m_cls.proxy = False

        m = m_cls(2, 2)
        m.proxy = False
        with self.assertRaises(AgentError):
            m.open_url("http://foo-api.com/")