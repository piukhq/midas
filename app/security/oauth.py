import json

import requests

from app.agents.exceptions import AgentError, CONFIGURATION_ERROR, SERVICE_CONNECTION_ERROR
from app.security.base import BaseSecurity


class OAuth(BaseSecurity):

    def encode(self, json_data):
        try:
            credentials = self.credentials['outbound']['credentials'][0]['value']
            url = credentials['url']
            resp = requests.post(url=url, data=credentials['payload'])
            response_json = resp.json()

            request_data = {
                "json": json.loads(json_data),
                "headers": {
                    "Authorization": "{} {}".format(credentials['prefix'], response_json['access_token'])
                }
            }
        except requests.RequestException as e:
            raise AgentError(SERVICE_CONNECTION_ERROR) from e
        except KeyError as e:
            raise AgentError(CONFIGURATION_ERROR) from e

        return request_data
