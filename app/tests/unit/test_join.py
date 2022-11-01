from decimal import Decimal
from unittest import TestCase, mock
from unittest.mock import MagicMock
from uuid import uuid4, UUID

from requests.exceptions import RetryError
from werkzeug.exceptions import NotFound

from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists, drop_database

from copy import copy

import app.journeys.join
from app import db
from app.agents.bpl import Bpl
from app.agents.schemas import Balance
from app.exceptions import GeneralError, AccountAlreadyExistsError, UnknownError
from app.journeys.join import agent_join, attempt_join, login_and_publish_status
from app.retry_util import create_task
from app.scheme_account import JourneyTypes, SchemeAccountStatus


class TestJoin(TestCase):
    def setUp(self):
        if db.engine.url.database != "midas_test":
            raise ValueError(f"Unsafe attempt to recreate database: {db.engine.url.database}")
        SessionMaker = sessionmaker(bind=db.engine)
        if database_exists(db.engine.url):
            drop_database(db.engine.url)
        create_database(db.engine.url)
        db.Base.metadata.create_all(bind=db.engine)
        self.db_session = SessionMaker()

    def tearDown(self) -> None:
        self.db_session.close()
        drop_database(db.engine.url)

    TESTING = True

    credentials = {
        "email": "jdoe@bink.com",
        "first_name": "John",
        "last_name": "Doe",
        "join_date": "2021/02/24",
        "card_number": "TRNT9276336436",
        "consents": [{"slug": "email_marketing", "value": True}],
        "merchant_identifier": "54a259f2-3602-4cc8-8f57-1239de7e5700",
    }
    scheme_account_id = 1
    journey_type = JourneyTypes.ADD.value
    tid = 1
    user_info = {
        "scheme_account_id": scheme_account_id,
        "status": SchemeAccountStatus.JOIN,
        "user_set": "1,2",
        "bink_user_id": 777,
        "journey_type": journey_type,
        "credentials": credentials,
        "channel": "com.bink.wallet",
        "tid": tid,
    }
    scheme_slug = "bpl-trenette"

    mock_config_object = MagicMock()
    mock_config_object.security_credentials = {
        "outbound": {
            "credentials": [
                {
                    "value": {
                        "token": "alwiufgalgdlfuglfsdk",
                    }
                }
            ]
        }
    }

    with mock.patch("app.agents.base.Configuration") as mock_configuration:
        mock_configuration.return_value = mock_config_object

        bpl = Bpl(
            retry_count=1,
            user_info=user_info,
            scheme_slug=scheme_slug,
        )
        bpl.base_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/"

    @mock.patch("app.agents.base.Configuration", return_value=mock_config_object)
    @mock.patch.object(Bpl, "join")
    def test_agent_join(self, mock_join, mock_config):
        result = agent_join(Bpl, self.user_info, self.tid, self.scheme_slug)

        self.assertTrue(isinstance(result["agent"], Bpl))
        mock_join.assert_called()
        mock_config.assert_called()

    @mock.patch("app.agents.base.Configuration", return_value=mock_config_object)
    @mock.patch("app.agents.bpl.Bpl.make_request", side_effect=GeneralError(exception=RetryError(response=None)))
    def test_agent_join_throws_exception(self, mock_join, mock_config):
        with self.assertRaises(GeneralError) as e:
            agent_join(Bpl, self.user_info, self.tid, self.scheme_slug)

        self.assertTrue(isinstance(e.exception, GeneralError))
        mock_join.assert_called()
        mock_config.assert_called()

    def test_login_and_publish_status_expecting_callback(self):
        agent = copy(self.bpl)
        agent.expecting_callback = True
        result = login_and_publish_status(
            Bpl, self.user_info, self.scheme_slug, {"agent": agent, "error": ""}, self.tid
        )
        assert result is True

    @mock.patch(
        "app.agents.bpl.Bpl.balance", return_value=Balance(points=Decimal("0.1"), value=Decimal("0.1"), value_label="")
    )
    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.journeys.join.publish_transactions")
    @mock.patch("app.publish.balance")
    @mock.patch("app.journeys.join.update_pending_join_account")
    @mock.patch("app.journeys.join.agent_login")
    def test_login_and_publish_status_agent_has_identifier(
        self,
        mock_agent_login,
        mock_update_pending_join_account,
        mock_publish_balance,
        mock_publish_transactions,
        mock_publish_status,
        mock_bpl_balance,
    ):
        agent = copy(self.bpl)
        agent.identifier = {"merchant_identifier": uuid4()}
        mock_agent_login.return_value = agent
        result = login_and_publish_status(
            Bpl, self.user_info, self.scheme_slug, {"agent": agent, "error": ""}, self.tid
        )

        assert mock_update_pending_join_account.call_args.args == (self.user_info, self.tid)
        assert mock_update_pending_join_account.call_args.kwargs == {"identifier": {"merchant_identifier": mock.ANY}}
        mock_publish_balance.assert_called_once_with(
            {"points": Decimal("0.1"), "value": Decimal("0.1"), "value_label": "", "reward_tier": 0},
            self.user_info["scheme_account_id"],
            self.user_info["user_set"],
            self.tid,
        )
        mock_bpl_balance.assert_called()
        mock_publish_transactions.assert_called_once_with(
            agent, self.user_info["scheme_account_id"], self.user_info["user_set"], self.tid
        )
        mock_publish_status.assert_called_once_with(
            self.user_info["scheme_account_id"],
            SchemeAccountStatus.ACTIVE,
            self.tid,
            self.user_info,
            "join",
        )
        assert result is True

    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.journeys.join.publish_transactions")
    @mock.patch("app.publish.balance", autospec=True)
    @mock.patch("app.agents.bpl.Bpl.balance")
    @mock.patch("app.journeys.join.update_pending_join_account")
    @mock.patch("app.journeys.join.agent_login", return_value=bpl)
    def test_login_and_publish_status_join_result_has_identifier(
        self,
        mock_agent_login,
        mock_update_pending_join_account,
        mock_bpl_balance,
        mock_publish_balance,
        mock_publish_transactions,
        mock_publish_status,
    ):
        agent = copy(self.bpl)
        agent.identifier = {"merchant_identifier": uuid4()}
        result = login_and_publish_status(
            Bpl, self.user_info, self.scheme_slug, {"agent": agent, "error": ""}, self.tid
        )

        mock_agent_login.assert_called()
        assert mock_update_pending_join_account.call_args.args == (self.user_info, self.tid)
        assert mock_update_pending_join_account.call_args.kwargs == {"identifier": {"merchant_identifier": mock.ANY}}
        mock_publish_balance.assert_called()
        mock_bpl_balance.assert_called()
        mock_publish_transactions.assert_called()
        mock_publish_status.assert_called()
        assert result is True

    @mock.patch("app.agents.bpl.Bpl.balance")
    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.journeys.join.publish_transactions")
    @mock.patch("app.publish.balance", side_effect=RetryError(response=None))
    @mock.patch("app.journeys.join.update_pending_join_account")
    @mock.patch("app.journeys.join.agent_login")
    def test_login_and_publish_status_balance_request_throws_error(
        self,
        mock_agent_login,
        mock_update_pending_join_account,
        mock_publish_balance,
        mock_publish_transactions,
        mock_publish_status,
        mock_bpl_balance,
    ):
        agent = copy(self.bpl)
        agent.identifier = {"merchant_identifier": uuid4()}
        mock_agent_login.return_value = agent
        result = login_and_publish_status(
            Bpl, self.user_info, self.scheme_slug, {"agent": agent, "error": ""}, self.tid
        )

        assert mock_update_pending_join_account.call_args.args == (self.user_info, self.tid)
        assert mock_update_pending_join_account.call_args.kwargs == {"identifier": {"merchant_identifier": mock.ANY}}
        mock_publish_balance.assert_called()
        mock_bpl_balance.assert_called()
        mock_publish_transactions.assert_not_called()
        mock_publish_status.assert_called_once_with(
            self.user_info["scheme_account_id"],
            SchemeAccountStatus.UNKNOWN_ERROR,
            self.tid,
            self.user_info,
            "join",
        )
        assert result is True

    @mock.patch("app.journeys.join.update_pending_join_account")
    @mock.patch("app.journeys.join.agent_login", side_effect=AccountAlreadyExistsError())
    def test_login_and_publish_status_base_error_with_join_result(
        self,
        mock_agent_login,
        mock_update_pending_join_account,
    ):
        result = login_and_publish_status(
            Bpl, self.user_info, self.scheme_slug, {"agent": self.bpl, "error": AccountAlreadyExistsError}, self.tid
        )

        mock_agent_login.assert_called()
        assert mock_update_pending_join_account.call_args.args == (self.user_info, self.tid)
        assert isinstance(mock_update_pending_join_account.call_args.kwargs["error"], AccountAlreadyExistsError)
        assert mock_update_pending_join_account.call_args.kwargs["scheme_slug"] == self.scheme_slug
        assert isinstance(
            mock_update_pending_join_account.call_args.kwargs["consent_ids"],
            type(consent["id"] for consent in self.user_info["credentials"].get("consents", [])),
        )
        assert result is True

    @mock.patch("app.publish.zero_balance", autospec=True)
    @mock.patch("app.journeys.join.update_pending_join_account")
    @mock.patch("app.journeys.join.agent_login", side_effect=AccountAlreadyExistsError())
    def test_login_and_publish_status_base_error_without_join_result(
        self,
        mock_agent_login,
        mock_update_pending_join_account,
        mock_publish_zero_balance,
    ):
        result = login_and_publish_status(
            Bpl, self.user_info, self.scheme_slug, {"agent": self.bpl, "error": ""}, self.tid
        )

        mock_agent_login.assert_called()
        mock_update_pending_join_account.assert_not_called()
        mock_publish_zero_balance.assert_called_once_with(
            self.user_info["scheme_account_id"], self.user_info["user_set"], self.tid
        )
        assert result is True

    @mock.patch("app.journeys.join.decrypt_credentials", return_value=credentials)
    @mock.patch("app.journeys.join.agent_join", return_value={"agent": bpl, "error": ""})
    @mock.patch("app.journeys.join.login_and_publish_status")
    def test_attempt_join(self, mock_login_and_publish_status, mock_agent_join, mock_decrypt_credentials):
        with db.session_scope() as session:
            create_task(
                db_session=session,
                user_info=self.user_info,
                journey_type=str(self.journey_type),
                message_uid=str(uuid4()),
                scheme_identifier="scheme",
                scheme_account_id=str(self.scheme_account_id),
            )
        attempt_join(self.scheme_account_id, self.tid, self.scheme_slug, self.user_info)

        self.assertTrue(mock_login_and_publish_status.called)
        mock_agent_join.assert_called()
        mock_decrypt_credentials.assert_called()

    @mock.patch("app.publish.status", autospec=True)
    @mock.patch("app.journeys.join.decrypt_credentials", return_value=credentials)
    def test_attempt_join_agent_not_found(self, mock_decrypt_credentials, mock_publish_status):
        with self.assertRaises(NotFound) as e:
            attempt_join(self.scheme_account_id, self.tid, "not-the-right-slug", self.user_info)

        mock_decrypt_credentials.assert_called()
        assert e.exception.name == "Not Found"
        mock_publish_status.assert_called_once()
        assert mock_publish_status.call_args.args == (
            self.scheme_account_id,
            900,
            self.tid,
            self.user_info,
        )

    @mock.patch("app.journeys.join.decrypt_credentials", return_value=credentials)
    @mock.patch("app.journeys.join.agent_join", return_value={"agent": bpl, "error": ""})
    @mock.patch("app.journeys.join.login_and_publish_status")
    def test_attempt_join_awaiting_callback(
        self, mock_login_and_publish_status, mock_agent_join, mock_decrypt_credentials
    ):
        with db.session_scope() as session:
            create_task(
                db_session=session,
                user_info=self.user_info,
                journey_type=str(self.journey_type),
                message_uid=str(uuid4()),
                scheme_identifier="scheme",
                scheme_account_id=str(self.scheme_account_id),
                awaiting_callback=True,
            )
        attempt_join(self.scheme_account_id, self.tid, self.scheme_slug, self.user_info)

        self.assertFalse(mock_login_and_publish_status.called)
        mock_agent_join.assert_called()
        mock_decrypt_credentials.assert_called()
