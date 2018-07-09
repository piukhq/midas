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

    def encode(self, *args, **kwargs):
        """
        :return: dict of parameters to be unpacked for requests.post()
        """
        raise NotImplementedError()

    def decode(self, *args, **kwargs):
        """
        :return: json string of payload
        """
        raise NotImplementedError()

    def _validate_timestamp(self, timestamp):
        current_time = time.time()
        if (current_time - int(timestamp)) > self.time_limit:
            raise AgentError(VALIDATION)

    @staticmethod
    def _add_timestamp(json_data):
        """Appends a timestamp to a json string."""
        current_time = int(time.time())
        json_with_timestamp = '{}{}'.format(json_data, current_time)
        return json_with_timestamp, current_time

    def _get_key(self, key_type):
        for item in self.credentials:
            if item['type'] == key_type:
                return item['value']
        raise KeyError('{} not in credentials'.format(key_type))
