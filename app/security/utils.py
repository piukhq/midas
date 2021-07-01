import json
import settings
from importlib import import_module

from flask import request

from soteria import configuration
from app.agents.exceptions import AgentError, CONFIGURATION_ERROR, UNKNOWN
from app.exceptions import AgentException
from app.security import registry


def get_security_agent(security_type, *args, **kwargs):
    """
    Retrieves an instance of a security agent. Security agents must have a file containing a class with equal names,
    where the filename is lowercase.
    :param security_type: Int. Security type choice from Configuration. e.g Configuration.RSA_SECURITY
    :param args: extra arguments to initialise security agent
    :param kwargs: extra keyword arguments to initialise security agent
    :return: agent instance
    """
    try:
        module_name, class_name = registry.TYPES[security_type].split('.')

        security_module = import_module('.' + module_name, package='app.security')

        agent_class = getattr(security_module, class_name)
        agent_instance = agent_class(*args, **kwargs)

    except (AttributeError, ImportError) as e:
        raise AgentError(CONFIGURATION_ERROR) from e

    return agent_instance


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
                config = configuration.Configuration(kwargs['scheme_slug'], handler_type, settings.VAULT_URL,
                                                     settings.VAULT_TOKEN, settings.CONFIG_SERVICE_URL)
                security_agent = get_security_agent(config.security_credentials['inbound']['service'],
                                                    config.security_credentials)

                decoded_data = json.loads(security_agent.decode(request.headers,
                                                                request.get_data().decode('utf8')))
            except AgentError as e:
                raise AgentException(e)
            except Exception as e:
                raise AgentException(AgentError(UNKNOWN)) from e

            return fn(data=decoded_data, config=config, *args, **kwargs)
        return wrapper
    return decorator
