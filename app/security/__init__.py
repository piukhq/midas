from importlib import import_module

import hvac

from settings import VAULT_TOKEN


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
    except (AttributeError, ModuleNotFoundError):
        raise DoesNotExist('No security type was found for {}'.format(security_type))

    return agent_instance


def get_security_credentials(key_items):
    client = hvac.Client(token=VAULT_TOKEN)

    for key_item in key_items:
        value = client.read('secret/{}'.format(key_item['storage_key']))['data'][key_item['type']]
        key_item['value'] = value

    return key_items
