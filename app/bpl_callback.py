import json
import requests
import sentry_sdk

import settings
from flask import request
from flask_restful import Resource

from app import AgentException, UnknownException
from app.encoding import JsonEncoder
from app.encryption import hash_ids
from app.resources import create_response, get_agent_class
from azure_oidc.integrations.flask_decorator import FlaskOIDCAuthDecorator
from azure_oidc import OIDCConfig

from app.scheme_account import update_pending_join_account
from app.utils import get_headers
from app.agents.exceptions import AgentError

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
        self.update_hermes(data)
        scheme_account_id = hash_ids.decode(data["third_party_identifier"])
        self.update_balance(scheme_account_id, scheme_slug)
        return create_response({"success": True})

    def update_hermes(self, data):
        scheme_account_id = hash_ids.decode(data["third_party_identifier"])
        identifier = {"card_number": data["account_number"], "merchant_identifier": data["UUID"]}
        identifier_data = json.dumps(identifier, cls=JsonEncoder)
        headers = get_headers("success")

        requests.put(
            "{}/schemes/accounts/{}/credentials".format(settings.HERMES_URL, scheme_account_id[0]),
            data=identifier_data,
            headers=headers,
        )

    def update_balance(self, scheme_account_id, scheme_slug):

        def update_failed_scheme_account(exception):
            update_pending_join_account(scheme_account_id, exception.args[0], 123, scheme_slug=scheme_slug,
                                        consent_ids=(), raise_exception=False)
            sentry_sdk.capture_exception()

        try:
            get_agent_class(scheme_slug)
        except AgentError as e:
            update_failed_scheme_account(e)
            raise AgentException(e)
        except Exception as e:
            update_failed_scheme_account(e)
            raise UnknownException(e)
