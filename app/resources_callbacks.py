import requests
import sentry_sdk
from flask_restful import Resource
from soteria.configuration import Configuration

from app import redis_retry
from app.agents.exceptions import SERVICE_CONNECTION_ERROR, UNKNOWN, AgentError, JoinError
from app.encryption import hash_ids
from app.exceptions import AgentException, UnknownException
from app.resources import create_response, decrypt_credentials, get_agent_class
from app.scheme_account import JourneyTypes, SchemeAccountStatus, update_pending_join_account
from app.security.utils import authorise
from settings import HERMES_URL, NEW_ICELAND_AGENT_ACTIVE, SERVICE_API_KEY
from app.requests_retry import requests_retry_session


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

            key = redis_retry.get_key(agent_class.__name__, user_info["scheme_account_id"])
            retry_count = redis_retry.get_count(key)
            agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug, config=config)

            # TODO - NEW_ICELAND_AGENT_ACTIVE - Remove reference
            if NEW_ICELAND_AGENT_ACTIVE:
                agent_instance.join_callback(data)
            else:
                agent_instance.join(data, inbound=True)
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
