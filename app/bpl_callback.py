import json

import requests
from azure_oidc import OIDCConfig
from azure_oidc.integrations.flask_decorator import FlaskOIDCAuthDecorator
from flask import request
from flask_restful import Resource

import settings
from app import redis_retry
from app.agents.exceptions import UNKNOWN, AgentError
from app.encoding import JsonEncoder
from app.encryption import hash_ids
from app.exceptions import UnknownException
from app.http_request import get_headers
from app.requests_retry import requests_retry_session
from app.resources import create_response, decrypt_credentials, get_agent_class
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
    def post(self, scheme_slug):
        data = json.loads(request.get_data())
        self.process_join_callback(scheme_slug, data)
        return create_response({"success": True})

    def process_join_callback(self, scheme_slug, data):
        decoded_scheme_account = hash_ids.decode(data["third_party_identifier"])
        scheme_account_id = decoded_scheme_account[0]
        update_hermes(data, scheme_account_id)
        user_info = {
            "credentials": collect_credentials(scheme_account_id),
            "status": SchemeAccountStatus.PENDING,
            "scheme_account_id": scheme_account_id,
            "journey_type": JourneyTypes.JOIN.value,
        }

        try:
            agent_class = get_agent_class(scheme_slug)

            key = redis_retry.get_key(agent_class.__name__, user_info["scheme_account_id"])
            retry_count = redis_retry.get_count(key)
            agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug)
            agent_instance.update_async_join(data)
        except Exception as e:
            raise UnknownException(e)


def update_hermes(data, scheme_account_id):
    identifier = {"card_number": data["account_number"], "merchant_identifier": data["UUID"]}
    identifier_data = json.dumps(identifier, cls=JsonEncoder)
    headers = get_headers("success")

    requests.put(
        "{}/schemes/accounts/{}/credentials".format(settings.HERMES_URL, scheme_account_id),
        data=identifier_data,
        headers=headers,
    )


def collect_credentials(scheme_account_id):
    session = requests_retry_session()
    response = session.get(
        "{0}/schemes/accounts/{1}/credentials".format(settings.HERMES_URL, scheme_account_id),
        headers={"Authorization": f"Token {settings.SERVICE_API_KEY}"},
    )

    try:
        response.raise_for_status()
    except Exception as ex:
        raise AgentError(UNKNOWN) from ex

    credentials = decrypt_credentials(response.json()["credentials"])

    return credentials
