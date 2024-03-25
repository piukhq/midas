import json

import requests
import sentry_sdk

from app.exceptions import ConfigurationError, ServiceConnectionError
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
                "headers": {"Authorization": f"{credentials["prefix"]} {response_json["access_token"]}"},
            }
        except requests.RequestException as e:
            sentry_sdk.capture_message(f"Failed request to get oauth token from {url}. exception: {e}")
            raise ServiceConnectionError(exception=e) from e
        except (KeyError, IndexError) as e:
            raise ConfigurationError(exception=e) from e

        return request_data
