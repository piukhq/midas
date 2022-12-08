import requests
import sentry_sdk
from flask_restful import Resource
from soteria.configuration import Configuration

from app import db
from app.encryption import hash_ids
from app.error_handler import retry_on_callback
from app.exceptions import BaseError, ServiceConnectionError, UnknownError
from app.models import RetryTaskStatuses
from app.resources import create_response, decrypt_credentials, get_agent_class
from app.retry_util import delete_task, get_task, view_session
from app.scheme_account import JourneyTypes, SchemeAccountStatus, update_pending_join_account
from app.security.utils import authorise

RETRYABLE_ERRORS = ["JOIN_ERROR"]


class JoinCallback(Resource):
    @authorise(Configuration.JOIN_HANDLER)
    @view_session
    def post(self, scheme_slug, data, config, *, session: db.Session):
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

            # Get the saved retry task, contains user_info data from original request
            # and can be used to update the callback retry
            retry_task = get_task(session, scheme_account_id)
            request_data = retry_task.request_data
            decrypted_credentials = decrypt_credentials(request_data["credentials"])

            user_info = {
                "credentials": decrypted_credentials,
                "status": SchemeAccountStatus.PENDING,
                "scheme_account_id": request_data["scheme_account_id"],
                "journey_type": JourneyTypes.JOIN.value,
                "bink_user_id": request_data.get("bink_user_id"),
            }
        except (KeyError, ValueError, AttributeError) as e:
            raise UnknownError(exception=e)
        except (requests.ConnectionError, BaseError) as e:
            raise ServiceConnectionError(exception=e) from e

        try:
            agent_class = get_agent_class(scheme_slug)

            agent_instance = agent_class(retry_task.attempts, user_info, scheme_slug=scheme_slug, config=config)
            error_code = data.get("error_codes")
            if error_code:
                if self._is_error_retryable(error_code):
                    retry_on_callback(session, retry_task, data["error_codes"])
                    if retry_task.status == RetryTaskStatuses.FAILED:
                        delete_task(db_session=session, retry_task=retry_task)
                    else:
                        return
                else:
                    delete_task(session, retry_task=retry_task)
            agent_instance.join_callback(data)
        except BaseError as e:
            update_failed_scheme_account(e)
            raise e
        except Exception as e:
            update_failed_scheme_account(e)
            raise UnknownError(exception=e) from e

        delete_task(session, retry_task)

        return create_response({"success": True})

    @staticmethod
    def _is_error_retryable(error_code):
        if error_code[0]["code"] in RETRYABLE_ERRORS:
            return True
        return False
