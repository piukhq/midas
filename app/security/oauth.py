import json

import sentry_sdk
import requests

from app.agents.exceptions import AgentError, CONFIGURATION_ERROR, SERVICE_CONNECTION_ERROR
from app.security.base import BaseSecurity


class OAuth(BaseSecurity):
    def encode(self, json_data):
        try:
            credentials = self.credentials["outbound"]["credentials"][0]["value"]
            url = credentials["url"]
            resp = requests.post(url=url, data=credentials["payload"])
            resp.raise_for_status()
            response_json = resp.json()

            request_data = {
                "json": json.loads(json_data),
                "headers": {"Authorization": "{} {}".format(credentials["prefix"], response_json["access_token"])},
            }
        except requests.RequestException as e:
            sentry_sdk.capture_message("Failed request to get oauth token from {}. exception: {}".format(url, e))
            raise AgentError(SERVICE_CONNECTION_ERROR) from e
        except (KeyError, IndexError) as e:
            raise AgentError(CONFIGURATION_ERROR) from e

        return request_data
