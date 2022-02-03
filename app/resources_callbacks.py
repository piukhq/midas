import typing as t

import requests
import sentry_sdk
from flask_restful import Resource
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from soteria.configuration import Configuration

from app import retry
from app.agents.exceptions import SERVICE_CONNECTION_ERROR, UNKNOWN, AgentError, JoinError
from app.encryption import hash_ids
from app.exceptions import AgentException, UnknownException
from app.resources import create_response, decrypt_credentials, get_agent_class
from app.scheme_account import JourneyTypes, SchemeAccountStatus, update_pending_join_account
from app.security.utils import authorise
from settings import HERMES_URL, SERVICE_API_KEY


class JoinCallback(Resource):
    @authorise(Configuration.JOIN_HANDLER)
    def post(self, scheme_slug, data, config):
        def update_failed_scheme_account(exception):
            consents = user_info["credentials"].get("consents", [])
            consent_ids = (consent["id"] for consent in consents)
            update_pending_join_account(
                user_info,
                exception.args[0],
                message_uid,
                scheme_slug=scheme_slug,
                consent_ids=consent_ids,
                raise_exception=False,
            )
            sentry_sdk.capture_exception()

        try:
            message_uid = data["message_uid"]
            scheme_account_id = hash_ids.decode(data["record_uid"])
            if not scheme_account_id:
                raise ValueError("The record_uid provided is not valid")

            user_info = {
                "credentials": self._collect_credentials(scheme_account_id[0]),
                "status": SchemeAccountStatus.PENDING,
                "scheme_account_id": scheme_account_id[0],
                "journey_type": JourneyTypes.JOIN.value,
            }
        except (KeyError, ValueError, AttributeError) as e:
            sentry_sdk.capture_exception()
            raise UnknownException(e) from e
        except (requests.ConnectionError, AgentError) as e:
            sentry_sdk.capture_exception()
            raise AgentException(JoinError(SERVICE_CONNECTION_ERROR)) from e

        try:
            agent_class = get_agent_class(scheme_slug)

            key = retry.get_key(agent_class.__name__, user_info["scheme_account_id"])
            retry_count = retry.get_count(key)
            agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug, config=config)

            agent_instance.join_callback(data)
        except AgentError as e:
            update_failed_scheme_account(e)
            raise AgentException(e)
        except Exception as e:
            update_failed_scheme_account(e)
            raise UnknownException(e)

        return create_response({"success": True})

    @staticmethod
    def _collect_credentials(scheme_account_id):
        session = requests_retry_session()
        response = session.get(
            "{0}/schemes/accounts/{1}/credentials".format(HERMES_URL, scheme_account_id),
            headers={"Authorization": f"Token {SERVICE_API_KEY}"},
        )

        try:
            response.raise_for_status()
        except Exception as ex:
            raise AgentError(UNKNOWN) from ex

        credentials = decrypt_credentials(response.json()["credentials"])

        return credentials


def requests_retry_session(
    retries: int = 3,
    backoff_factor: float = 0.3,
    status_forcelist: t.Tuple = (500, 502, 504),
    session: requests.Session = None,
) -> requests.Session:
    """Create a requests session with the given retry policy.
    This method will create a new session if an existing one is not provided.
    See here for more information about this functionality:
    https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html?highlight=forcelist#urllib3.util.retry.Retry"""
    if session is None:
        session = requests.Session()

    retry = Retry(
        total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session
