import json
import time
from typing import Optional
from decimal import Decimal
from unittest import mock

from flask_testing import TestCase
from app import create_app, AgentException, UnknownException
from app import publish
from app.agents.base import BaseMiner
from app.agents.schemas import Balance
from app.agents.exceptions import (
    AgentError,
    LoginError,
    STATUS_LOGIN_FAILED,
    errors,
    RegistrationError,
    NO_SUCH_RECORD,
    STATUS_REGISTRATION_FAILED,
    ACCOUNT_ALREADY_EXISTS,
)
from app.agents.harvey_nichols import HarveyNichols
from app.agents.merchant_api_generic import MerchantAPIGeneric
from app.encryption import AESCipher
from app.publish import thread_pool_executor
from app.resources import (
    agent_login,
    registration,
    agent_register,
    get_hades_balance,
    get_balance_and_publish,
    async_get_balance_and_publish,
    get_headers,
    log_task,
)
from app.scheme_account import SchemeAccountStatus, JourneyTypes

local_aes_key = "6gZW4ARFINh4DR1uIzn12l7Mh1UF982L"


def encrypted_credentials():
    aes = AESCipher(local_aes_key.encode())
    return aes.encrypt(json.dumps({})).decode()


class TestResources(TestCase):
    TESTING = True
    user_info = {
        "user_set": 1,
        "credentials": {"credentials": "test", "email": "test@email.com"},
        "status": SchemeAccountStatus.WALLET_ONLY,
        "scheme_account_id": 123,
        "pending": True,
        "channel": "com.bink.wallet",
    }

    def test_get_headers(self):
        headers = get_headers("success")

        self.assertEqual(headers["transaction"], "success")

    def test_log_task(self):
        @log_task
        def decorated(x):
            return x

        self.assertEqual(decorated.__name__, "logged_func")

    class Agent(BaseMiner):
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
    @mock.patch("app.publish.balance", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
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
    @mock.patch("app.publish.balance", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
    def test_balance_none_exception(
        self, mock_update_pending_join_account, mock_pool, mock_agent_login, mock_publish_balance,
            mock_get_aes_key
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
    @mock.patch("app.publish.balance", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
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
        self.assertEqual(response.status_code, 520)
        self.assertEqual(response.json["name"], "Unknown Error")
        self.assertEqual(response.json["message"], "test error")
        self.assertEqual(response.json["code"], 520)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.publish.transactions", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
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
    @mock.patch("app.publish.transactions", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
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
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
    @mock.patch("app.publish.transactions", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    def test_transactions_unknown_error(
        self, mock_agent_login, mock_publish_transactions, mock_pool, mock_get_aes_key
    ):
        mock_publish_transactions.side_effect = Exception("test error")
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/bpl-trenette/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 520)
        self.assertEqual(response.json["name"], "Unknown Error")
        self.assertEqual(response.json["message"], "test error")
        self.assertEqual(response.json["code"], 520)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
    @mock.patch("app.publish.transactions", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    def test_transactions_login_error(self, mock_agent_login, mock_publish_transactions, mock_pool, mock_get_aes_key):
        mock_publish_transactions.side_effect = LoginError(STATUS_LOGIN_FAILED)
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = encrypted_credentials()
        url = "/bpl-trenette/transactions?credentials={0}&scheme_account_id={1}&user_id={2}".format(credentials, 3, 5)
        response = self.client.get(url)

        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_pool.called)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["name"], errors[STATUS_LOGIN_FAILED]["name"])
        self.assertEqual(response.json["message"], errors[STATUS_LOGIN_FAILED]["message"])
        self.assertEqual(response.json["code"], errors[STATUS_LOGIN_FAILED]["code"])

    def test_bad_agent(self):
        url = "/bad-agent-key/transactions?credentials=234&scheme_account_id=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
    def test_bad_agent_updates_status(self, mock_submit, mock_get_aes_key):
        mock_get_aes_key.return_value = local_aes_key.encode()
        credentials = (
            "JnoPkhKfU6uddLtbTTOvr1DgsNBeWhI0ADM2VGyfTFR8Wi2%2FRHQ5SX%2Bvk"
            "zIgqmsGGqq94x%2BcBd7Vd%2FKsRTOEBDkV45rsm6WRV6wfZTC51rQ%3D"
        )
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
    @mock.patch("app.resources.thread_pool_executor.submit", autospec=True)
    def test_register_view(self, mock_pool, mock_get_aes_key):
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

        self.assertTrue(mock_pool.called)
        self.assertEqual(response.json, {"message": "success"})

    @mock.patch.object(HarveyNichols, "register")
    @mock.patch("app.resources.update_pending_join_account", autospec=True)
    def test_agent_register_success(self, mock_update_pending_join_account, mock_register):
        mock_register.return_value = {"message": "success"}
        user_info = {
            "metadata": {},
            "scheme_slug": "test slug",
            "user_id": "test user id",
            "credentials": {},
            "scheme_account_id": 2,
            "status": SchemeAccountStatus.PENDING,
            "channel": "com.bink.wallet",
        }

        result = agent_register(HarveyNichols, user_info, {}, 1)

        self.assertTrue(mock_register.called)
        self.assertFalse(mock_update_pending_join_account.called)
        self.assertFalse(result["error"])
        self.assertTrue(isinstance(result["agent"], HarveyNichols))

    @mock.patch.object(HarveyNichols, "register")
    @mock.patch("app.resources.update_pending_join_account", autospec=False)
    def test_agent_register_fail(self, mock_update_pending_join_account, mock_register):
        mock_register.side_effect = RegistrationError(STATUS_REGISTRATION_FAILED)
        mock_update_pending_join_account.side_effect = AgentException(STATUS_REGISTRATION_FAILED)
        user_info = {
            "metadata": {},
            "scheme_slug": "test slug",
            "user_id": "test user id",
            "credentials": {"consents": [{"id": 1, "value": True}]},
            "scheme_account_id": 2,
            "status": SchemeAccountStatus.PENDING,
            "channel": "com.bink.wallet",
        }

        with self.assertRaises(AgentException):
            agent_register(HarveyNichols, user_info, {}, 1)

        self.assertTrue(mock_register.called)
        self.assertTrue(mock_update_pending_join_account.called)
        consent_data_sent = list(mock_update_pending_join_account.call_args[1]["consent_ids"])
        self.assertTrue(consent_data_sent, [1])

    @mock.patch.object(HarveyNichols, "register")
    @mock.patch("app.resources.update_pending_join_account", autospec=False)
    def test_agent_register_fail_account_exists(self, mock_update_pending_join_account, mock_register):
        mock_register.side_effect = RegistrationError(ACCOUNT_ALREADY_EXISTS)
        user_info = {"credentials": {}, "scheme_account_id": 2, "status": "", "channel": "com.bink.wallet"}
        result = agent_register(HarveyNichols, user_info, {}, "")

        self.assertTrue(mock_register.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue(result["error"])
        self.assertTrue(isinstance(result["agent"], HarveyNichols))

    @mock.patch.object(MerchantAPIGeneric, "register")
    @mock.patch("app.resources.update_pending_join_account", autospec=False)
    def test_agent_register_fail_merchant_api(self, mock_update_pending_join_account, mock_register):
        mock_register.side_effect = RegistrationError(ACCOUNT_ALREADY_EXISTS)
        mock_update_pending_join_account.side_effect = AgentException(ACCOUNT_ALREADY_EXISTS)
        user_info = {"credentials": {}, "scheme_account_id": 2, "status": "", "channel": "com.bink.wallet"}

        with self.assertRaises(AgentException):
            agent_register(MerchantAPIGeneric, user_info, {}, "")

        self.assertTrue(mock_register.called)
        self.assertTrue(mock_update_pending_join_account.called)

    @mock.patch("app.publish.balance", auto_spec=True)
    @mock.patch("app.publish.status", auto_spec=True)
    @mock.patch("app.resources.publish_transactions", auto_spec=True)
    @mock.patch("app.resources.agent_register", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
    def test_registration(
        self,
        mock_update_pending_join_account,
        mock_agent_login,
        mock_agent_register,
        mock_publish_transaction,
        mock_publish_status,
        mock_publish_balance,
    ):
        scheme_slug = "harvey-nichols"
        mock_agent_register.return_value = {
            "agent": HarveyNichols(0, {"scheme_account_id": "1", "status": None, "channel": "com.bink.wallet"}),
            "error": None,
        }
        user_info = {
            "credentials": {"scheme_slug": encrypted_credentials(), "email": "test@email.com"},
            "user_set": "4",
            "scheme_account_id": 2,
            "status": "",
            "channel": "com.bink.wallet",
        }

        result = registration(scheme_slug, user_info, tid=None)

        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_publish_transaction.called)
        self.assertTrue(mock_publish_status.called)
        self.assertTrue(mock_agent_register.called)
        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertTrue("success" in mock_update_pending_join_account.call_args[0])
        self.assertEqual(result, True)

    @mock.patch("app.resources.update_pending_join_account", autospec=True)
    @mock.patch("app.resources.agent_register", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    def test_registration_already_exists_fail(
        self, mock_agent_login, mock_agent_register, mock_update_pending_join_account
    ):
        mock_agent_register.return_value = {
            "agent": HarveyNichols(0, {"scheme_account_id": "1", "status": None, "channel": "com.bink.wallet"}),
            "error": ACCOUNT_ALREADY_EXISTS,
        }
        mock_agent_login.side_effect = AgentException(STATUS_LOGIN_FAILED)
        scheme_slug = "harvey-nichols"
        user_info = {
            "credentials": {"scheme_slug": encrypted_credentials(), "email": "test@email.com"},
            "user_set": "4",
            "scheme_account_id": 2,
            "status": "",
            "channel": "com.bink.wallet",
        }

        result = registration(scheme_slug, user_info, tid=None)
        self.assertTrue(mock_agent_register.called)
        self.assertTrue(mock_agent_login.called)
        self.assertTrue(mock_update_pending_join_account.called)
        self.assertEqual(result, True)

    @mock.patch("app.resources.retry", autospec=True)
    @mock.patch.object(HarveyNichols, "attempt_login")
    def test_agent_login_success(self, mock_login, mock_retry):
        mock_login.return_value = {"message": "success"}

        agent_login(
            HarveyNichols,
            {
                "scheme_account_id": 2,
                "status": SchemeAccountStatus.ACTIVE,
                "credentials": {},
                "channel": "com.bink.wallet",
            },
            "harvey-nichols",
        )
        self.assertTrue(mock_login.called)

    @mock.patch("app.resources.retry", autospec=True)
    @mock.patch.object(HarveyNichols, "attempt_login")
    def test_agent_login_system_fail_(self, mock_login, mock_retry):
        mock_login.side_effect = AgentError(NO_SUCH_RECORD)
        user_info = {"scheme_account_id": 1, "credentials": {}, "status": "", "channel": "com.bink.wallet"}
        with self.assertRaises(AgentError):
            agent_login(HarveyNichols, user_info, scheme_slug="harvey-nichols", from_register=True)
        self.assertTrue(mock_login.called)

    @mock.patch("app.resources.retry", autospec=True)
    @mock.patch.object(HarveyNichols, "attempt_login")
    def test_agent_login_user_fail_(self, mock_login, mock_retry):
        mock_login.side_effect = AgentError(STATUS_LOGIN_FAILED)

        with self.assertRaises(AgentException):
            agent_login(HarveyNichols, self.user_info, "harvey-nichols")
        self.assertTrue(mock_login.called)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    @mock.patch("app.resources.agent_login", auto_spec=False)
    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
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
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    @mock.patch("app.resources.agent_login", auto_spec=False)
    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
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

    @mock.patch("app.resources.update_pending_link_account", auto_spec=True)
    @mock.patch("app.resources.get_balance_and_publish", autospec=False)
    def test_async_errors_correctly(self, mock_balance_and_publish, mock_update_pending_link_account):
        scheme_slug = "harvey-nichols"
        mock_balance_and_publish.side_effect = AgentException("Linking error")

        with self.assertRaises(AgentException):
            async_get_balance_and_publish("agent_class", scheme_slug, self.user_info, "tid")

        self.assertTrue(mock_balance_and_publish.called)
        self.assertTrue(mock_update_pending_link_account.called)
        self.assertEqual(
            "Error with async linking. Scheme: {}, Error: {}".format(
                scheme_slug, repr(mock_balance_and_publish.side_effect)
            ),
            mock_update_pending_link_account.call_args[0][1],
        )

    @mock.patch("requests.get", auto_spec=True)
    def test_get_hades_balance(self, mock_requests):
        get_hades_balance(1)

        self.assertTrue(mock_requests.called)

    @mock.patch("requests.get", auto_spec=False)
    def test_get_hades_balance_error(self, mock_requests):
        mock_requests.return_value = None
        with self.assertRaises(UnknownException):
            self.assertEqual(get_hades_balance(1), None)

        self.assertTrue(mock_requests.called)

    @mock.patch("app.resources.delete_scheme_account", auto_spec=True)
    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=False)
    @mock.patch("app.publish.status", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    @mock.patch("app.publish.transactions", auto_spec=True)
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

    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.publish.status", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    def test_get_balance_and_publish_balance_error(
        self, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_join_account
    ):
        mock_publish_balance.side_effect = AgentError(STATUS_LOGIN_FAILED)
        user_info = self.user_info
        user_info["pending"] = False

        with self.assertRaises(AgentException):
            get_balance_and_publish(HarveyNichols, "scheme_slug", user_info, "tid")

        self.assertTrue(mock_login.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertTrue(mock_publish_status.called)
        self.assertTrue(mock_update_pending_join_account.called)

    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.publish.status", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    def test_get_balance_and_publish_with_pending_merchant_api_scheme(
        self, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_join_account
    ):

        pending_user_info = dict(self.user_info)
        pending_user_info["status"] = SchemeAccountStatus.PENDING
        pending_user_info["journey_type"] = JourneyTypes.UPDATE
        balance = get_balance_and_publish(MerchantAPIGeneric, "scheme_slug", pending_user_info, "tid")

        self.assertFalse(mock_login.called)
        self.assertFalse(mock_publish_balance.called)
        self.assertFalse(mock_publish_status.called)
        self.assertFalse(mock_update_pending_join_account.called)

        expected_balance = {
            "points": Decimal(0),
            "points_label": "0",
            "reward_tier": 0,
            "scheme_account_id": 123,
            "user_set": 1,
            "value": Decimal(0),
            "value_label": "Pending",
        }
        self.assertEqual(balance, expected_balance)

    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.publish.status", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    def test_get_balance_and_publish_with_pending_join_merchant_api(
        self, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_join_account
    ):
        pending_user_info = dict(self.user_info)
        pending_user_info["status"] = SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS
        pending_user_info["journey_type"] = JourneyTypes.UPDATE
        balance = get_balance_and_publish(MerchantAPIGeneric, "scheme_slug", pending_user_info, "tid")

        self.assertFalse(mock_login.called)
        self.assertFalse(mock_publish_balance.called)
        self.assertFalse(mock_publish_status.called)
        self.assertFalse(mock_update_pending_join_account.called)

        expected_balance = {
            "points": Decimal(0),
            "points_label": "0",
            "reward_tier": 0,
            "scheme_account_id": 123,
            "user_set": 1,
            "value": Decimal(0),
            "value_label": "Pending",
        }
        self.assertEqual(balance, expected_balance)

    @mock.patch("app.resources.update_pending_join_account", auto_spec=False)
    @mock.patch("app.resources.agent_login", auto_spec=False)
    @mock.patch("app.publish.status", auto_spec=False)
    @mock.patch("app.publish.balance", auto_spec=False)
    @mock.patch("app.resources.publish_transactions", auto_spec=True)
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

    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
    @mock.patch("app.resources.agent_login", auto_spec=True)
    @mock.patch("app.publish.status", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    @mock.patch("app.resources.publish_transactions", auto_spec=True)
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

    @mock.patch("app.resources.update_pending_link_account")
    @mock.patch("app.resources.agent_login", auto_spec=False)
    @mock.patch("app.publish.status", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    @mock.patch("app.resources.publish_transactions", auto_spec=True)
    def test_balance_runs_everything_while_async_raises_errors(
        self, mock_transactions, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_link_account
    ):

        mock_publish_balance.side_effect = AgentError(STATUS_LOGIN_FAILED)
        mock_login.return_value = self.Agent(None)
        mock_publish_status.return_value = "test"

        async_balance = thread_pool_executor.submit(
            async_get_balance_and_publish, HarveyNichols, "scheme_slug", self.user_info, "tid"
        )

        with self.assertRaises(AgentException):
            async_balance.result(timeout=15)

        self.assertTrue(mock_login.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertFalse(mock_transactions.called)
        self.assertTrue(mock_update_pending_link_account.called)

    @mock.patch("app.resources.update_pending_link_account")
    @mock.patch("app.resources.agent_login", auto_spec=False)
    @mock.patch("app.publish.status", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    @mock.patch("app.resources.publish_transactions", auto_spec=True)
    def test_balance_runs_everything_while_async_raises_unexpected_error(
        self, mock_transactions, mock_publish_balance, mock_publish_status, mock_login, mock_update_pending_link_account
    ):

        mock_publish_balance.side_effect = KeyError("test not handled agent error")
        mock_update_pending_link_account.side_effect = AgentException("test not handled agent error")
        mock_login.return_value = self.Agent(None)
        mock_publish_status.return_value = "test"

        with self.assertRaises(AgentException):
            async_balance = thread_pool_executor.submit(
                async_get_balance_and_publish, HarveyNichols, "scheme_slug", self.user_info, "tid"
            )
            async_balance.result(timeout=15)

        self.assertTrue(mock_login.called)
        self.assertTrue(mock_publish_balance.called)
        self.assertFalse(mock_transactions.called)
        self.assertTrue(mock_update_pending_link_account.called)

    @mock.patch("app.resources.get_aes_key")
    @mock.patch("app.resources.thread_pool_executor.submit", auto_spec=True)
    @mock.patch("app.publish.balance", auto_spec=False)
    @mock.patch("app.resources.agent_login", auto_spec=False)
    @mock.patch("app.resources.update_pending_join_account", auto_spec=True)
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
