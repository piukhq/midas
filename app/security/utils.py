import json
from importlib import import_module

import hvac
from flask import request

from app import configuration, AgentException
from app.agents.exceptions import AgentError
from settings import VAULT_TOKEN, VAULT_URL


class DoesNotExist(Exception):
    pass


def get_security_agent(security_type, *args, **kwargs):
    """
    Retrieves an instance of a security agent. Security agents must have a file containing a class with equal names,
    where the filename is lowercase.
    :param security_type: string of security type. e.g
    :param args: extra arguments to initialise security agent
    :param kwargs: extra keyword arguments to initialise security agent
    :return: agent instance
    """
    try:
        security_module = import_module('.' + security_type.lower(), package='app.security')
        agent_class = getattr(security_module, security_type)
        agent_instance = agent_class(*args, **kwargs)
    except (AttributeError, ImportError):
        raise DoesNotExist('No security type was found for {}'.format(security_type))

    return agent_instance


def get_security_credentials(key_items):
    """
    Retrieves security credential values from key storage vault.
    :param key_items: list of dicts {'type': e.g 'bink_public_key', 'storage_key': auto-generated hash from helios}
    :return: key_items: returns same list of dict with added 'value' keys containing actual credential values.
    """
    client = hvac.Client(token=VAULT_TOKEN, url=VAULT_URL)

    try:
        for key_item in key_items:
            value = client.read('secret/data/{}'.format(key_item['storage_key']))['data']['data'][key_item['type']]
            key_item['value'] = value
    except TypeError as e:
        raise TypeError('Could not locate security credentials in vault.') from e

    return key_items


def authorise(handler_type):
    """
    Decorator function for validation of requests from merchant APIs. Should be used on all callback views.
    Requires scheme slug and handler type to retrieve configuration details on which security type to use.
    Scheme slug should be passed in as a parameter in the view and handler type passed in as a decorator param.
    :param handler_type: Int. should be a choice from Configuration.HANDLER_TYPE_CHOICES
    :return: decorated function
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            try:
                config = configuration.Configuration(kwargs['scheme_slug'], handler_type)
                security_agent = get_security_agent(config.security_service, config.security_credentials)

                decoded_data = json.loads(security_agent.decode(request.headers,
                                                                request.get_data().decode('utf8')))
            except AgentError as e:
                raise AgentException(e)

            return fn(data=decoded_data, config=config, *args, **kwargs)
        return wrapper
    return decorator
