import json
import requests

import settings
from flask import request
from flask_restful import Resource
from app import configuration
from app.configuration import Configuration
from app.encoding import JsonEncoder
from app.encryption import hash_ids
from app.resources import create_response
from app.security.utils import get_security_agent
from azure_oidc.integrations.flask_decorator import FlaskOIDCAuthDecorator
from azure_oidc import OIDCConfig
from app.utils import get_headers

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
