from requests.exceptions import RequestException
from settings import MNEMOSYNE_URL, SERVICE_API_KEY, logger

import json
import requests
import time


class EventRaiseError(Exception):
    pass


def raise_event(event_name, user_id, user_email, metadata):
    destination = '{}/analytics/service'.format(MNEMOSYNE_URL)
    headers = {
        'content-type': 'application/json',
        'Authorization': 'Token {}'.format(SERVICE_API_KEY)
    }
    payload = {
        'service': 'midas',
        'user': {
            'e': user_email,
            'id': user_id
        },
        "events": [
            {
                "time": int(time.time()),
                "type": 6,
                "id": event_name,
                "intercom": 1,
                "data": {
                    "metadata": metadata
                }
            }
        ]
    }

    body_data = json.dumps(payload)

    try:
        response = requests.post(destination, data=body_data, headers=headers)
    except RequestException as ex:
        error_message = 'analytics request error: {}, event_name: {}'
        logger.debug(error_message.format(repr(ex), event_name))
        raise EventRaiseError from ex

    try:
        response.raise_for_status()
    except RequestException as ex:
        error_message = 'analytics status error: {}, error status code: {}, event_name: {}'
        logger.debug(error_message.format(repr(ex), response.status_code, event_name))
        raise EventRaiseError from ex

    return response
