import json

import time

from app.agents.exceptions import AgentError, VALIDATION


class BaseSecurity:
    time_limit = 120

    def __init__(self, credentials):
        """
        :param credentials: list if dicts e.g
        [{'type': 'bink_private_key', 'storage_key': 'vaultkey', 'value': 'keyvalue'}]
        """
        self.credentials = credentials

    def encode(self, json_data):
        """
        :param json_data: json string of payload
        :return: dict of parameters to be unpacked for requests.post()
        """
        raise NotImplementedError()

    def decode(self, request):
        """
        :param request: request object
        :return: json string of payload
        """
        raise NotImplementedError()

    def _validate_timestamp(self, data):
        message_time = data['timestamp']
        current_time = time.time()
        if (current_time - message_time) > self.time_limit:
            raise AgentError(VALIDATION)

    @staticmethod
    def _add_timestamp(json_data):
        data = json.loads(json_data)
        data['timestamp'] = int(time.time())
        return json.dumps(data)

    def _get_key(self, key_type):
        for item in self.credentials:
            if item['type'] == key_type:
                return item['value']
        raise KeyError('{} not in credentials')
