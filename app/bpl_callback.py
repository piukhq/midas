import json
import requests

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
from settings import HERMES_URL

tenant_id = "a6e2367a-92ea-4e5a-b565-723830bcc095"
config = OIDCConfig(
    base_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
    issuer=f"https://sts.windows.net/{tenant_id}/",
    audience="api://midas-nonprod",
)
requires_auth = FlaskOIDCAuthDecorator(config)


class JoinCallbackBpl(Resource):
    @requires_auth()
    def post(self, scheme_slug):
        config = configuration.Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        security_agent = get_security_agent(
            config.security_credentials["inbound"]["service"], config.security_credentials
        )

        data = json.loads(security_agent.decode(request.headers, request.get_data().decode("utf8")))

        scheme_account_id = hash_ids.decode(data["third_party_identifier"])

        identifier = {"card_number": data["account_number"], "merchant_identifier": data["UUID"]}
        identifier_data = json.dumps(identifier, cls=JsonEncoder)
        headers = get_headers("success")

        requests.put(
            "{}/schemes/accounts/{}/credentials".format(HERMES_URL, scheme_account_id[0]),
            data=identifier_data,
            headers=headers,
        )
        return create_response({"success": True})
