import json

import requests
from azure_oidc import OIDCConfig
from azure_oidc.integrations.flask_decorator import FlaskOIDCAuthDecorator
from flask import request
from flask_restful import Resource

import settings
from app import db, redis_retry
from app.encoding import JsonEncoder
from app.encryption import hash_ids
from app.exceptions import UnknownError
from app.http_request import get_headers
from app.resources import create_response, decrypt_credentials, get_agent_class
from app.retry_util import delete_task, get_task, view_session
from app.scheme_account import JourneyTypes, SchemeAccountStatus

tenant_id = "a6e2367a-92ea-4e5a-b565-723830bcc095"
config = OIDCConfig(
    base_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
    issuer=f"https://sts.windows.net/{tenant_id}/",
    audience="api://midas-nonprod",
)

_requires_auth = None


def _nop_decorator(*args, **kwargs):
    return lambda fn: fn


def auth_decorator():
    if settings.API_AUTH_ENABLED is False:
        return _nop_decorator

    global _requires_auth
    if _requires_auth is None:
        _requires_auth = FlaskOIDCAuthDecorator(config)
    return _requires_auth


requires_auth = auth_decorator()


class JoinCallbackBpl(Resource):
    @requires_auth()
    @view_session
    def post(self, scheme_slug, *, session: db.Session):
        data = json.loads(request.get_data())
        self.process_join_callback(scheme_slug, data, session)
        return create_response({"success": True})

    def process_join_callback(self, scheme_slug: str, data: dict, session: db.Session):
        decoded_scheme_account = hash_ids.decode(data["third_party_identifier"])
        scheme_account_id = decoded_scheme_account[0]

        # Get the saved retry task, contains user_info data from original request
        # and can be used to update the callback retry
        retry_task = get_task(session, scheme_account_id)
        request_data = retry_task.request_data
        decrypted_credentials = decrypt_credentials(request_data["credentials"])

        update_hermes(data, scheme_account_id, request_data.get("bink_user_id"))
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


def update_hermes(data, scheme_account_id: int, bink_user_id: int):
    identifier = {
        "card_number": data["account_number"],
        "merchant_identifier": data["UUID"],
        "bink_user_id": bink_user_id,
    }
    identifier_data = json.dumps(identifier, cls=JsonEncoder)
    headers = get_headers("success")

    requests.put(
        "{}/schemes/accounts/{}/credentials".format(settings.HERMES_URL, scheme_account_id),
        data=identifier_data,
        headers=headers,
    )
