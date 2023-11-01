import json
import typing as t

import requests
from flask import request
from flask_restful import Resource

import settings
from app import db, redis_retry
from app.encoding import JsonEncoder
from app.encryption import hash_ids
from app.exceptions import UnknownError
from app.http_request import get_headers
from app.reporting import get_logger
from app.resources import create_response, decrypt_credentials, get_agent_class
from app.retry_util import delete_task, get_task, view_session
from app.scheme_account import JourneyTypes, SchemeAccountStatus

log = get_logger("bpl-callback")


def _nop_decorator(*args, **kwargs):
    return lambda fn: fn


class JoinCallbackBpl(Resource):

    @view_session
    def post(self, scheme_slug, *, session: db.Session):
        log.debug("Callback POST request received for scheme {}".format(scheme_slug))
        data = json.loads(request.get_data())
        self.process_join_callback(scheme_slug, data, session)
        return create_response({"success": True})

    def process_join_callback(self, scheme_slug: str, data: dict, session: db.Session):
        log.debug("{} received a callback".format(scheme_slug))
        decoded_scheme_account = hash_ids.decode(data["third_party_identifier"])
        scheme_account_id = decoded_scheme_account[0]

        # Get the saved retry task, contains user_info data from original request
        # and can be used to update the callback retry
        retry_task = get_task(session, scheme_account_id)
        request_data = t.cast(dict, retry_task.request_data)
        decrypted_credentials = decrypt_credentials(request_data["credentials"])

        update_hermes(data, scheme_account_id, t.cast(str, request_data.get("bink_user_id")))
        user_info = {
            "credentials": decrypted_credentials,
            "status": SchemeAccountStatus.PENDING,
            "scheme_account_id": scheme_account_id,
            "journey_type": JourneyTypes.JOIN.value,
            "bink_user_id": request_data.get("bink_user_id"),
        }

        try:
            agent_class = get_agent_class(scheme_slug)

            key = redis_retry.get_key(agent_class.__name__, user_info["scheme_account_id"])
            retry_count = redis_retry.get_count(key)

            agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug)
            agent_instance.update_async_join(data)
        except Exception as e:
            delete_task(session, retry_task)
            raise UnknownError(exception=e) from e

        delete_task(session, retry_task)


def update_hermes(data, scheme_account_id: int, bink_user_id: str):
    log.debug("Updating scheme account {} in Hermes".format(scheme_account_id))
    identifier = {
        "card_number": data["account_number"],
        "merchant_identifier": data["UUID"],
    }
    identifier_data = json.dumps(identifier, cls=JsonEncoder)
    headers = get_headers("success")
    headers["bink-user-id"] = bink_user_id

    requests.put(
        "{}/schemes/accounts/{}/credentials".format(settings.HERMES_URL, scheme_account_id),
        data=identifier_data,
        headers=headers,
    )
