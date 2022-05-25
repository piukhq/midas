import json
import time
from decimal import Decimal
from typing import Optional
from unittest import mock
from unittest.mock import MagicMock

import arrow
import httpretty
from flask_testing import TestCase

from app import publish
from app.agents.base import BaseAgent
from app.agents.harvey_nichols import HarveyNichols
from app.agents.schemas import Balance, Transaction, Voucher, balance_tuple_to_dict, transaction_tuple_to_dict
from app.api import create_app
from app.encryption import AESCipher
from app.exceptions import (
    AccountAlreadyExistsError,
    BaseError,
    NoSuchRecordError,
    StatusLoginFailedError,
    StatusRegistrationFailedError,
    UnknownError,
)
from app.http_request import get_headers
from app.journeys.common import agent_login
from app.journeys.join import agent_join, attempt_join
from app.journeys.view import async_get_balance_and_publish, get_balance_and_publish
from app.publish import thread_pool_executor
from app.resources import get_hades_balance
from app.scheme_account import JourneyTypes, SchemeAccountStatus
from app.vouchers import VoucherState, VoucherType, voucher_state_names
from settings import HADES_URL, HERMES_URL

local_aes_key = "testing1234567898765432345674562"


def encrypted_credentials():
    aes = AESCipher(local_aes_key.encode())
    return aes.encrypt(json.dumps({})).decode()


def mocked_hn_configuration(*args, **kwargs):
    conf = MagicMock()
    return conf


class TestResources(TestCase):
    TESTING = True
    user_info = {
        "user_set": 1,
        "credentials": {"credentials": "test", "email": "test@email.com"},
        "status": SchemeAccountStatus.WALLET_ONLY,
        "journey_type": JourneyTypes.LINK.value,
        "scheme_account_id": 123,
        "pending": True,
        "channel": "com.bink.wallet",
    }

    def test_get_headers(self):
        headers = get_headers("success")

        self.assertEqual(headers["transaction"], "success")

    def test_balance_tuple_to_dict(self):
        balance_tuple = Balance(
            points=Decimal("12.34"),
            value=Decimal("24.72"),
            value_label="gbp",
            vouchers=[
                Voucher(
                    state=voucher_state_names[VoucherState.IN_PROGRESS],
                    type=VoucherType.STAMPS.value,
                    value=Decimal("10.10"),
                    target_value=Decimal("20.20"),
                ),
                Voucher(
                    state=voucher_state_names[VoucherState.EXPIRED],
                    type=VoucherType.STAMPS.value,
                    issue_date=1234567895,
                    code="test-voucher-2",
                    value=Decimal("20.20"),
                    target_value=Decimal("20.20"),
                ),
            ],
        )

        expected = {
            "points": Decimal("12.34"),
            "value": Decimal("24.72"),
            "value_label": "gbp",
            "reward_tier": 0,
            "vouchers": [
                {
                    "state": voucher_state_names[VoucherState.IN_PROGRESS],
                    "type": VoucherType.STAMPS.value,
                    "value": Decimal("10.10"),
                    "target_value": Decimal("20.20"),
                },
                {
                    "state": voucher_state_names[VoucherState.EXPIRED],
                    "type": VoucherType.STAMPS.value,
                    "issue_date": 1234567895,
                    "code": "test-voucher-2",
                    "value": Decimal("20.20"),
                    "target_value": Decimal("20.20"),
                },
            ],
        }

        balance_dict = balance_tuple_to_dict(balance_tuple)

        self.assertEqual(balance_dict, expected)

    def test_transaction_tuple_to_dict(self):
        date = arrow.now()
        transaction_tuple = Transaction(
            date=date,
            description="test transaction",
            points=Decimal("12.34"),
            hash="test-hash-1",
        )

        expected = {
            "date": date,
            "description": "test transaction",
            "points": Decimal("12.34"),
            "hash": "test-hash-1",
        }

        transaction_dict = transaction_tuple_to_dict(transaction_tuple)

        self.assertEqual(transaction_dict, expected)

    class Agent(BaseAgent):
        def __init__(self, identifier):
            self.identifier = identifier

        @staticmethod
        def balance() -> Optional[Balance]:
            return Balance(points=Decimal(1), value=Decimal(1), value_label="")

    # for async processes which might have a delay before the test can pass but after a response is given
    def assert_mock_called_with_delay(self, delay, mocked_func):
        count = 0
        while count < delay:
            try:
                return self.assertTrue(mocked_func.called)
            except AssertionError:
                count += 0.2
                time.sleep(0.2)

        raise TimeoutError("assertion false, timeout reached")

    def create_app(self):
        return create_app(
            self,
        )

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.publish.balance", autospec=True)
    @mock.patch("app.journeys.view.agent_login", autospec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    @mock.patch("app.resources.async_get_balance_and_publish", autospec=True)
    def test_user_balances(
        self,
        mock_async_balance_and_publish,
        mock_update_pending_join_account,
        mock_pool,
        mock_agent_login,
        mock_publish_balance,
        mock_get_aes_key,
    ):
        mock_publish_balance.return_value = {"user_id": 2, "scheme_account_id": 4}
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/bpl-trenette/balance?credentials={0}&user_set={1}&scheme_account_id={2}".format(credentials, 1, 2)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"user_id": 2, "scheme_account_id": 4})
        self.assertFalse(mock_async_balance_and_publish.called)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.publish.balance", autospec=True)
    @mock.patch("app.journeys.view.agent_login", autospec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    def test_balance_none_exception(
        self, mock_update_pending_join_account, mock_pool, mock_agent_login, mock_publish_balance, mock_get_aes_key
    ):
        mock_publish_balance.return_value = None
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/bpl-trenette/balance?credentials={0}&user_set={1}&scheme_account_id={2}".format(credentials, 1, 2)
        response = self.client.get(url)

        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.publish.balance", autospec=True)
    @mock.patch("app.journeys.view.agent_login", autospec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    def test_balance_unknown_error(
        self, mock_update_pending_join_account, mock_pool, mock_agent_login, mock_publish_balance, mock_get_aes_key
    ):
        mock_publish_balance.side_effect = Exception("test error")
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/bpl-trenette/balance?credentials={0}&user_set={1}&scheme_account_id={2}".format(credentials, 1, 2)
        response = self.client.get(url)

        self.assertTrue(mock_update_pending_join_account)
        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(520, response.status_code)
        self.assertEqual("Unknown error", response.json["name"])
        self.assertEqual("test error", response.json["message"])
        self.assertEqual(520, response.json["code"])

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.publish.transactions", autospec=True)
    @mock.patch("app.resources.agent_login", autospec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    def test_transactions(self, mock_pool, mock_agent_login, mock_publish_transactions, mock_get_aes_key):
        mock_publish_transactions.return_value = [{"points": Decimal("10.00")}]
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/bpl-trenette/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            [
                {"points": 10.0},
            ],
        )

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.publish.transactions", autospec=True)
    @mock.patch("app.resources.agent_login", autospec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    def test_transactions_none_exception(
        self, mock_pool, mock_agent_login, mock_publish_transactions, mock_get_aes_key
    ):
        mock_publish_transactions.return_value = None
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/bpl-trenette/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    @mock.patch("app.publish.transactions", autospec=True)
    @mock.patch("app.resources.agent_login", autospec=True)
    def test_transactions_unknown_error(self, mock_agent_login, mock_publish_transactions, mock_pool, mock_get_aes_key):
        mock_publish_transactions.side_effect = Exception("test error")
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/bpl-trenette/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(520, response.status_code)
        self.assertEqual("Unknown error", response.json["name"])
        self.assertEqual("test error", response.json["message"])
        self.assertEqual(520, response.json["code"])

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    @mock.patch("app.publish.transactions", autospec=True)
    @mock.patch("app.resources.agent_login", autospec=True)
    def test_transactions_login_error(self, mock_agent_login, mock_publish_transactions, mock_pool, mock_get_aes_key):
        mock_publish_transactions.side_effect = StatusLoginFailedError()
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/bpl-trenette/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(403, response.status_code)
        self.assertEqual(
            StatusLoginFailedError().name,
            response.json["name"],
        )
        self.assertEqual(
            StatusLoginFailedError().message,
            response.json["message"],
        )
        self.assertEqual(
            StatusLoginFailedError().code,
            response.json["code"],
        )

    def test_bad_agent(self):
        url = "/bad-agent-key/transactions?credentials=234&scheme_account_id=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    def test_bad_agent_updates_status(self, mock_submit, mock_get_aes_key):
        mock_get_aes_key.return_value = local_aes_key.encode()
        test_creds = json.dumps({"username": "NZ57271", "password": "d4Hgvf47"})
        aes_cipher = AESCipher(local_aes_key.encode())
        credentials = aes_cipher.encrypt(test_creds).decode("utf-8")
        url = "/bad-agent-key/balance?credentials={}&scheme_account_id=1&user_set=1".format(credentials)
        user_info = {
            "credentials": {"username": "NZ57271", "password": "d4Hgvf47"},
            "status": None,
            "user_set": "1",
            "journey_type": None,
            "scheme_account_id": 1,
        }
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        mock_submit.assert_called_with(publish.status, 1, 10, None, user_info)

    def test_bad_parameters(self):
        url = "/harvey-nichols/transactions?credentials=234"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {"message": 'Please provide either "user_set" or "user_id" parameters'})

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.queue.enqueue_request", autospec=True)
    def test_register_view(self, mock_enqueue_request, mock_get_aes_key):
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/harvey-nichols/register"
        data = {
            "scheme_account_id": 2,
            "user_id": 4,
            "credentials": credentials,
            "status": 0,
            "journey_type": 0,
            "channel": "com.bink.wallet",
        }
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")

        self.assertTrue(mock_enqueue_request.called)
        self.assertEqual(response.json, {"message": "success"})

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.queue.enqueue_request", autospec=True)
    def test_join_view(self, mock_enqueue_request, mock_get_aes_key):
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/harvey-nichols/join"
        data = {
            "scheme_account_id": 2,
            "user_id": 4,
            "credentials": credentials,
            "status": 0,
            "journey_type": 0,
            "channel": "com.bink.wallet",
        }
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")

        self.assertTrue(mock_enqueue_request.called)
        self.assertEqual(response.json, {"message": "success"})

    @mock.patch.object(HarveyNichols, "join")
    @mock.patch("app.agents.harvey_nichols.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.agents.base.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    def test_agent_join_success(self, mock_update_pending_join_account, mock_base_config, mock_hn_config, mock_join):
        mock_join.return_value = {"message": "success"}
        user_info = {
            "metadata": {},
            "scheme_slug": "test slug",
            "user_id": "test user id",
            "journey_type": JourneyTypes.JOIN.value,
            "credentials": {},
            "scheme_account_id": 2,
            "status": SchemeAccountStatus.PENDING,
            "channel": "com.bink.wallet",
        }

        result = agent_join(HarveyNichols, user_info, {}, 1)

        self.assertTrue(mock_join.called)
        self.assertFalse(mock_update_pending_join_account.called)
        self.assertFalse(result["error"])
        self.assertTrue(isinstance(result["agent"], HarveyNichols))

    @mock.patch.object(HarveyNichols, "join")
    @mock.patch("app.agents.harvey_nichols.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.agents.base.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.journeys.join.update_pending_join_account", autospec=False)
    def test_agent_join_fail(self, mock_update_pending_join_account, mock_base_config, mock_hn_config, mock_join):
        mock_join.side_effect = StatusRegistrationFailedError()
        mock_update_pending_join_account.side_effect = StatusRegistrationFailedError()
        user_info = {
            "metadata": {},
            "scheme_slug": "test slug",
            "user_id": "test user id",
            "journey_type": JourneyTypes.JOIN.value,
            "credentials": {"consents": [{"id": 1, "value": True}]},
            "scheme_account_id": 2,
            "status": SchemeAccountStatus.PENDING,
            "channel": "com.bink.wallet",
        }

        with self.assertRaises(StatusRegistrationFailedError):
            agent_join(HarveyNichols, user_info, {}, 1)

        self.assertTrue(mock_join.called)
        self.assertTrue(mock_update_pending_join_account.called)
        consent_data_sent = list(mock_update_pending_join_account.call_args[1]["consent_ids"])
        self.assertTrue(consent_data_sent, [1])

    @mock.patch.object(HarveyNichols, "join")
    @mock.patch("app.agents.harvey_nichols.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.agents.base.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.journeys.join.update_pending_join_account", autospec=False)
    def test_agent_join_fail_account_exists(
        self, mock_update_pending_join_account, mock_base_config, mock_hn_config, mock_join
    ):
        mock_join.side_effect = AccountAlreadyExistsError()
        user_info = {
            "credentials": {},
            "scheme_account_id": 2,
            "status": "",
            "channel": "com.bink.wallet",
            "journey_type": JourneyTypes.JOIN.value,
        }
        result = agent_join(HarveyNichols, user_info, {}, "")

        self.assertTrue(mock_join.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue(result["error"])
        self.assertTrue(isinstance(result["agent"], HarveyNichols))

    @mock.patch("app.publish.balance", autospec=True)
    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.journeys.join.publish_transactions", autospec=True)
    @mock.patch("app.journeys.join.agent_join", autospec=True)
    @mock.patch("app.journeys.join.agent_login", autospec=True)
    @mock.patch("app.journeys.join.update_pending_join_account", autospec=True)
    @mock.patch("app.agents.harvey_nichols.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.agents.base.Configuration", side_effect=mocked_hn_configuration)
    def test_join(
        self,
        mock_base_config,
        mock_hn_config,
        mock_update_pending_join_account,
        mock_agent_login,
        mock_agent_join,
        mock_publish_transaction,
        mock_publish_status,
        mock_publish_balance,
    ):
        scheme_slug = "harvey-nichols"
        mock_agent_join.return_value = {
            "agent": HarveyNichols(
                0,
                {
                    "scheme_account_id": "1",
                    "journey_type": JourneyTypes.JOIN.value,
                    "status": None,
                    "channel": "com.bink.wallet",
                    "credentials": {"scheme_slug": encrypted_credentials(), "email": "test@email.com"},
                },
            ),
            "error": None,
        }
        user_info = {
            "credentials": {"scheme_slug": encrypted_credentials(), "email": "test@email.com"},
            "user_set": "4",
            "scheme_account_id": 2,
            "journey_type": JourneyTypes.JOIN.value,
            "status": "",
            "channel": "com.bink.wallet",
        }

        result = attempt_join(scheme_slug, user_info, tid=None)

        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_publish_transaction.called)
        self.assertTrue(mock_publish_status.called)
        self.assertTrue(mock_agent_join.called)
        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertEqual(result, True)

    @mock.patch("app.journeys.join.update_pending_join_account", autospec=True)
    @mock.patch("app.journeys.join.agent_join", autospec=True)
    @mock.patch("app.journeys.join.agent_login", autospec=True)
    @mock.patch("app.agents.harvey_nichols.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.agents.base.Configuration", side_effect=mocked_hn_configuration)
    def test_join_already_exists_fail(
        self, mock_base_config, mock_hn_config, mock_agent_login, mock_agent_join, mock_update_pending_join_account
    ):
        mock_agent_join.return_value = {
            "agent": HarveyNichols(
                0,
                {
                    "scheme_account_id": "1",
                    "journey_type": JourneyTypes.JOIN.value,
                    "status": None,
                    "channel": "com.bink.wallet",
                    "credentials": {"scheme_slug": encrypted_credentials(), "email": "test@email.com"},
                },
            ),
            "error": AccountAlreadyExistsError,
        }
        mock_agent_login.side_effect = StatusLoginFailedError
        scheme_slug = "harvey-nichols"
        user_info = {
            "credentials": {"scheme_slug": encrypted_credentials(), "email": "test@email.com"},
            "user_set": "4",
            "scheme_account_id": 2,
            "journey_type": JourneyTypes.JOIN.value,
            "status": "",
            "channel": "com.bink.wallet",
        }

        result = attempt_join(scheme_slug, user_info, tid=None)
        self.assertTrue(mock_agent_join.called)
        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertEqual(result, True)

    @mock.patch("app.journeys.common.redis_retry", autospec=True)
    @mock.patch("app.agents.harvey_nichols.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.agents.base.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch.object(HarveyNichols, "attempt_login")
    def test_agent_login_success(self, mock_login, mock_base_config, mock_hn_config, mock_retry):
        mock_login.return_value = {"message": "success"}

        agent_login(
            HarveyNichols,
            {
                "scheme_account_id": 2,
                "status": SchemeAccountStatus.ACTIVE,
                "journey_type": JourneyTypes.JOIN.value,
                "credentials": {},
                "channel": "com.bink.wallet",
            },
            "harvey-nichols",
        )
        self.assertTrue(mock_login.called)

    @mock.patch("app.journeys.common.redis_retry", autospec=True)
    @mock.patch("app.agents.harvey_nichols.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.agents.base.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch.object(HarveyNichols, "attempt_login")
    def test_agent_login_system_fail_(self, mock_attempt_login, mock_base_config, mock_hn_config, mock_retry):
        mock_attempt_login.side_effect = NoSuchRecordError()
        user_info = {"scheme_account_id": 1, "credentials": {}, "status": "", "channel": "com.bink.wallet"}
        with self.assertRaises(NoSuchRecordError):
            agent_login(HarveyNichols, user_info, scheme_slug="harvey-nichols", from_join=True)
        self.assertTrue(mock_attempt_login.called)

    @mock.patch("app.journeys.common.redis_retry", autospec=True)
    @mock.patch("app.agents.harvey_nichols.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch("app.agents.base.Configuration", side_effect=mocked_hn_configuration)
    @mock.patch.object(HarveyNichols, "attempt_login")
    def test_agent_login_user_fail_(self, mock_login, mock_base_config, mock_hn_config, mock_retry):
        mock_login.side_effect = StatusLoginFailedError()

        with self.assertRaises(StatusLoginFailedError):
            agent_login(HarveyNichols, self.user_info, "harvey-nichols")
        self.assertTrue(mock_login.called)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    @mock.patch("app.publish.balance", autospec=False)
    @mock.patch("app.journeys.view.agent_login", autospec=False)
    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    def test_balance_updates_hermes_if_agent_sets_identifier(
        self, mock_update_pending_join_account, mock_login, mock_publish_balance, mock_pool, mock_get_aes_key
    ):
        mock_publish_balance.return_value = {"points": 1}
        mock_agent = self.Agent(None)
        mock_agent.identifier = True
        mock_login.return_value = mock_agent
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = {
            "username": "la@loyaltyangels.com",
            "password": "YSHansbrics6",
        }
        aes = AESCipher(local_aes_key.encode())
        credentials = aes.encrypt(json.dumps(credentials)).decode()

        url = "/harvey-nichols/balance?credentials={0}&user_set={1}&scheme_account_id={2}".format(credentials, 1, 2)
        self.client.get(url)

        self.assertTrue(mock_update_pending_join_account)
        self.assertTrue(mock_login.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_pool.called)
        self.assertIsNone(mock_pool.call_args[1]["journey"])

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    @mock.patch("app.publish.balance", autospec=False)
    @mock.patch("app.journeys.view.agent_login", autospec=False)
    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    def test_balance_does_not_update_hermes_if_agent_does_not_set_identifier(
        self, mock_update_pending_join_account, mock_login, mock_publish_balance, mock_pool, mock_get_aes_key
    ):
        mock_publish_balance.return_value = {"points": 1}
        mock_login.return_value = mock.MagicMock()
        mock_login().identifier = None
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = {
            "username": "la@loyaltyangels.com",
            "password": "YSHansbrics6",
        }
        aes = AESCipher(local_aes_key.encode())
        credentials = aes.encrypt(json.dumps(credentials)).decode()

        url = "/harvey-nichols/balance?credentials={0}&user_set={1}&scheme_account_id={2}".format(credentials, 1, 2)
        self.client.get(url)

        self.assertTrue(mock_login.called)
        self.assertFalse(mock_update_pending_join_account.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_pool.called)

    @mock.patch("app.journeys.view.update_pending_link_account", autospec=True)
    @mock.patch("app.journeys.view.get_balance_and_publish", autospec=False)
    def test_async_errors_correctly(self, mock_balance_and_publish, mock_update_pending_link_account):
        scheme_slug = "harvey-nichols"
        mock_balance_and_publish.side_effect = UnknownError(message="Linking error")

        with self.assertRaises(BaseError):
            async_get_balance_and_publish("agent_class", scheme_slug, self.user_info, "tid")

        self.assertTrue(mock_balance_and_publish.called)
        self.assertTrue(mock_update_pending_link_account.called)
        self.assertEqual(
            "Error with async linking. Scheme: harvey-nichols, Error: UnknownError()",
            mock_update_pending_link_account.call_args[1]["message"],
        )

    @mock.patch("requests.get", autospec=True)
    def test_get_hades_balance(self, mock_requests):
        get_hades_balance(1)

        self.assertTrue(mock_requests.called)

    @mock.patch("requests.get", autospec=False)
    def test_get_hades_balance_error(self, mock_requests):
        mock_requests.return_value = None
        with self.assertRaises(UnknownError):
            self.assertEqual(get_hades_balance(1), None)

        self.assertTrue(mock_requests.called)

    @mock.patch("app.journeys.view.delete_scheme_account", autospec=True)
    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    @mock.patch("app.journeys.view.agent_login", autospec=False)
    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.publish.balance", autospec=False)
    @mock.patch("app.publish.transactions", autospec=True)
    def test_get_balance_and_publish(
        self,
        mock_transactions,
        mock_publish_balance,
        mock_publish_status,
        mock_login,
        mock_update_pending_join_account,
        mock_delete,
    ):
        mock_publish_balance.return_value = {"points": 1}

        get_balance_and_publish(HarveyNichols, "scheme_slug", self.user_info, "tid")
        self.assertTrue(mock_login.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_transactions.called)
        self.assertTrue(mock_publish_status.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertFalse(mock_delete.called)

    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    @mock.patch("app.journeys.view.agent_login", autospec=True)
    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.publish.balance", autospec=False)
    def test_get_balance_and_publish_balance_error(
        self, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_join_account
    ):
        mock_publish_balance.side_effect = StatusLoginFailedError()
        user_info = self.user_info
        user_info["pending"] = False

        with self.assertRaises(StatusLoginFailedError):
            get_balance_and_publish(HarveyNichols, "scheme_slug", user_info, "tid")

        self.assertTrue(mock_login.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_publish_status.called)
        self.assertTrue(mock_update_pending_join_account.called)

    @mock.patch("app.journeys.view.update_pending_join_account", autospec=False)
    @mock.patch("app.journeys.view.agent_login", autospec=False)
    @mock.patch("app.publish.status", autospec=False)
    @mock.patch("app.publish.balance", autospec=False)
    @mock.patch("app.journeys.view.publish_transactions", autospec=True)
    def test_balance_runs_everything_while_async(
        self, mock_transactions, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_join_account
    ):

        mock_publish_balance.return_value = {"points": 1}
        mock_login.return_value = self.Agent(None)
        mock_publish_status.return_value = "test"
        mock_update_pending_join_account.return_value = "test2"

        async_balance = thread_pool_executor.submit(
            async_get_balance_and_publish, HarveyNichols, "scheme_slug", self.user_info, "tid"
        )

        self.assertEqual(async_balance.result(), mock_publish_balance.return_value)
        self.assertFalse(mock_update_pending_join_account.called)
        self.assertTrue(mock_login.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_transactions.called)
        self.assertTrue(mock_publish_status.called)

    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    @mock.patch("app.journeys.view.agent_login", autospec=True)
    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.publish.balance", autospec=False)
    @mock.patch("app.journeys.view.publish_transactions", autospec=True)
    def test_balance_runs_everything_while_async_with_identifier(
        self, mock_transactions, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_join_account
    ):

        mock_publish_balance.return_value = {"points": 1}
        mock_login.return_value = self.Agent("test card number")
        mock_publish_status.return_value = "test"
        mock_update_pending_join_account.return_value = "test2"

        async_balance = thread_pool_executor.submit(
            async_get_balance_and_publish, HarveyNichols, "scheme_slug", self.user_info, "tid"
        )

        self.assertEqual(async_balance.result(), mock_publish_balance.return_value)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue(mock_login.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_transactions.called)
        self.assertTrue(mock_publish_status.called)

    @mock.patch("app.journeys.view.update_pending_link_account")
    @mock.patch("app.journeys.view.agent_login", autospec=False)
    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.publish.balance", autospec=False)
    @mock.patch("app.journeys.view.publish_transactions", autospec=True)
    def test_balance_runs_everything_while_async_raises_errors(
        self, mock_transactions, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_link_account
    ):

        mock_publish_balance.side_effect = StatusLoginFailedError()
        mock_login.return_value = self.Agent(None)
        mock_publish_status.return_value = "test"

        async_balance = thread_pool_executor.submit(
            async_get_balance_and_publish, HarveyNichols, "scheme_slug", self.user_info, "tid"
        )

        with self.assertRaises(StatusLoginFailedError):
            async_balance.result(timeout=15)

        self.assertTrue(mock_login.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertFalse(mock_transactions.called)
        self.assertTrue(mock_update_pending_link_account.called)

    @mock.patch("app.journeys.view.update_pending_link_account")
    @mock.patch("app.journeys.view.agent_login", autospec=True)
    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.publish.balance", autospec=False)
    @mock.patch("app.journeys.view.publish_transactions", autospec=True)
    def test_balance_runs_everything_while_async_raises_unexpected_error(
        self, mock_transactions, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_link_account
    ):

        mock_publish_balance.side_effect = KeyError("test not handled agent error")
        mock_update_pending_link_account.side_effect = NoSuchRecordError(message="test not handled agent error")
        mock_login.return_value = self.Agent(None)
        mock_publish_status.return_value = "test"

        with self.assertRaises(UnknownError):
            async_balance = thread_pool_executor.submit(
                async_get_balance_and_publish, HarveyNichols, "scheme_slug", self.user_info, "tid"
            )
            async_balance.result(timeout=15)

        self.assertTrue(mock_login.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertFalse(mock_transactions.called)
        self.assertTrue(mock_update_pending_link_account.called)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    @mock.patch("app.publish.balance", autospec=False)
    @mock.patch("app.journeys.view.agent_login", autospec=False)
    @mock.patch("app.journeys.view.update_pending_join_account", autospec=True)
    def test_balance_sets_create_journey_on_status_call(
        self, mock_update_pending_join_account, mock_login, mock_publish_balance, mock_pool, mock_get_aes_key
    ):

        mock_publish_balance.return_value = {"points": 1}
        mock_agent = self.Agent(None)
        mock_agent.identifier = True
        mock_agent.create_journey = "join"
        mock_login.return_value = mock_agent
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = {
            "username": "la@loyaltyangels.com",
            "password": "YSHansbrics6",
        }
        aes = AESCipher(local_aes_key.encode())
        credentials = aes.encrypt(json.dumps(credentials)).decode()

        url = "/harvey-nichols/balance?credentials={0}&user_set={1}&scheme_account_id={2}".format(credentials, 1, 2)
        self.client.get(url)

        self.assertTrue(mock_update_pending_join_account)
        self.assertTrue(mock_login.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(mock_pool.call_args[1]["journey"], "join")

    @httpretty.activate
    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.agents.base.Configuration")
    @mock.patch("app.journeys.common.redis_retry")
    def test_balance_response_format(self, mock_retry, mock_configuration, mock_get_aes_key):
        mock_retry.get_count.return_value = 0

        config = mock_configuration.return_value
        config.merchant_url = "http://testbink.com/"
        mock_get_aes_key.return_value = local_aes_key.encode()
        config.security_credentials = {
            "outbound": {
                "credentials": [
                    {
                        "value": {
                            "token": "test-token-123",
                        },
                    }
                ],
            },
        }

        httpretty.register_uri(
            httpretty.GET,
            "http://testbink.com/bpl/loyalty/trenette/accounts/test-uuid",
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "UUID": "5ff1bda5-cd8f-4991-86d4-dac89379f47a",
                            "email": "test_zero_balance_user_100@autogen.bpl",
                            "status": "active",
                            "account_number": "TRNT0000000100",
                            "current_balances": [{"value": 0.0, "campaign_slug": "trenette-campaign"}],
                            "transaction_history": [],
                            "pending_rewards": [],
                            "rewards": [
                                {
                                    "code": "1qv7lgUyUVMBkxK",
                                    "issued_date": "1629385871",
                                    "redeemed_date": None,
                                    "expiry_date": "1893456000",
                                    "status": "issued",
                                }
                            ],
                        }
                    ),
                    status=200,
                )
            ],
        )

        httpretty.register_uri(
            httpretty.GET,
            "http://testbink.com/test-uuid",
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "account_number": "test-account-1",
                            "UUID": "1234567890",
                            "current_balances": [
                                {
                                    "value": 123.45,
                                }
                            ],
                            "pending_rewards": [],
                            "rewards": [
                                {
                                    "code": "1qv7lgUyUVMBkxK",
                                    "issued_date": "1629385871",
                                    "redeemed_date": None,
                                    "expiry_date": "1893456000",
                                    "status": "issued",
                                }
                            ],
                        }
                    ),
                    status=200,
                )
            ],
        )

        httpretty.register_uri(
            httpretty.PUT,
            f"{HERMES_URL}/schemes/accounts/2/credentials",
        )

        httpretty.register_uri(
            httpretty.POST,
            f"{HADES_URL}/balance",
        )

        expected = {
            "points": 123.45,
            "value": 123.45,
            "value_label": "",
            "reward_tier": 0,
            "vouchers": [
                {
                    "state": "inprogress",
                    "type": 1,
                    "value": 123.45,
                    "target_value": None,
                },
                {
                    "state": "issued",
                    "type": 1,
                    "issue_date": "1629385871",
                    "expiry_date": "1893456000",
                    "code": "1qv7lgUyUVMBkxK",
                    "value": None,
                    "target_value": None,
                },
            ],
            "scheme_account_id": 2,
            "user_set": "1",
            "points_label": "123",
        }

        credentials = {
            "merchant_identifier": "test-uuid",
        }
        journey_type = JourneyTypes.UPDATE.value

        aes = AESCipher(local_aes_key.encode())
        credentials = aes.encrypt(json.dumps(credentials)).decode()
        url = (
            f"/bpl-trenette/balance?credentials={credentials}&user_set=1"
            f"&scheme_account_id=2&journey_type={journey_type}"
        )
        resp = self.client.get(url)

        self.assertEqual(resp.json, expected)
