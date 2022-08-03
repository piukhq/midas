import requests
import sentry_sdk
from flask_restful import Resource
from soteria.configuration import Configuration

from app import db, redis_retry
from app.encryption import hash_ids
from app.error_handler import retry_on_callback
from app.exceptions import BaseError, ServiceConnectionError, UnknownError
from app.models import RetryTaskStatuses
from app.requests_retry import requests_retry_session
from app.resources import create_response, decrypt_credentials, get_agent_class
from app.retry_util import delete_task, get_task
from app.scheme_account import JourneyTypes, SchemeAccountStatus, update_pending_join_account
from app.security.utils import authorise
from settings import HERMES_URL, SERVICE_API_KEY

RETRYABLE_ERRORS = ["JOIN_ERROR"]


class JoinCallback(Resource):
    @authorise(Configuration.JOIN_HANDLER)
    def post(self, scheme_slug, data, config):
        def update_failed_scheme_account(exception):
            consents = user_info["credentials"].get("consents", [])
            consent_ids = (consent["id"] for consent in consents)
            update_pending_join_account(
                user_info,
                message_uid,
                error=exception,
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
            raise UnknownError(exception=e)
        except (requests.ConnectionError, BaseError) as e:
            sentry_sdk.capture_exception()
            raise ServiceConnectionError(exception=e) from e

        try:
            agent_class = get_agent_class(scheme_slug)

            key = redis_retry.get_key(agent_class.__name__, user_info["scheme_account_id"])
            retry_count = redis_retry.get_count(key)
            agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug, config=config)
            error_code = data.get("error_codes")
            if error_code:
                if self._is_error_retryable(error_code):
                    with db.session_scope() as session:
                        retry_task = retry_on_callback(session, user_info["scheme_account_id"], data["error_codes"])
                        if retry_task.status == RetryTaskStatuses.FAILED:
                            delete_task(db_session=session, retry_task=retry_task)
                        else:
                            return
                elif error_code[0]["code"] == "JOIN_IN_PROGRESS":
                    return
                else:
                    with db.session_scope() as session:
                        retry_task = get_task(session, user_info["scheme_account_id"])
                        delete_task(session, retry_task=retry_task)
            agent_instance.join_callback(data)
        except BaseError as e:
            update_failed_scheme_account(e)
            raise e
        except Exception as e:
            update_failed_scheme_account(e)
            raise UnknownError(exception=e) from e

        with db.session_scope() as session:
            retry_task = get_task(session, user_info["scheme_account_id"])
            delete_task(session, retry_task)

        return create_response({"success": True})

    @staticmethod
    def _is_error_retryable(error_code):
        if error_code[0]["code"] in RETRYABLE_ERRORS:
            return True
        return False

    @staticmethod
    def _collect_credentials(scheme_account_id):
        session = requests_retry_session()
        response = session.get(
            "{0}/schemes/accounts/{1}/credentials".format(HERMES_URL, scheme_account_id),
            headers={"Authorization": f"Token {SERVICE_API_KEY}"},
        )

        try:
            response.raise_for_status()
        except Exception as e:
            raise UnknownError(exception=e) from e

        credentials = decrypt_credentials(response.json()["credentials"])

        return credentials
