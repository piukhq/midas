import importlib

import sentry_sdk
from flask_restful import abort

from app import publish, redis_retry
from app.active import AGENTS
from app.agents.exceptions import SYSTEM_ACTION_REQUIRED, UNKNOWN, AgentError, LoginError, RetryLimitError, errors
from app.agents.schemas import transaction_tuple_to_dict
from app.exceptions import AgentException, UnknownException
from app.scheme_account import JourneyTypes


def resolve_agent(name):
    class_path = AGENTS[name]
    module_name, class_name = class_path.split(".")
    module = importlib.import_module("app.agents.{}".format(module_name))
    return getattr(module, class_name)


def get_agent_class(scheme_slug):
    try:
        return resolve_agent(scheme_slug)
    except KeyError:
        performance_slugs = ["performance-mock", "performance-voucher-mock"]
        for performance_slug in performance_slugs:
            if scheme_slug.startswith(performance_slug):
                return resolve_agent(performance_slug)

        abort(404, message="No such agent")


def agent_login(agent_class, user_info, scheme_slug=None, from_join=False):
    """
    Instantiates an agent class and attempts to login.
    :param agent_class: Class object inheriting BaseAgent class.
    :param user_info: Dictionary of user information.
    {
        'user_id': int,
        'credentials': str,
        'status': str,
        'scheme_account_id': int
        'journey_type': int
    }
    :param scheme_slug: String of merchant identifier e.g 'harvey-nichols'
    :param from_join: Boolean of whether the login call is from the join journey.
    :return: Class instance of the agent.
    """
    key = redis_retry.get_key(agent_class.__name__, user_info["scheme_account_id"])
    retry_count = redis_retry.get_count(key)
    if from_join:
        user_info["journey_type"] = JourneyTypes.UPDATE.value
        user_info["from_join"] = True

    agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug)
    try:
        agent_instance.attempt_login()
    except RetryLimitError as e:
        redis_retry.max_out_count(key, agent_instance.retry_limit)
        raise AgentException(e)
    except (LoginError, AgentError) as e:
        # If this is an UNKNOWN error, also log to sentry
        if e.code == errors[UNKNOWN]["code"]:
            sentry_sdk.capture_exception()
        if e.args[0] in SYSTEM_ACTION_REQUIRED and from_join:
            raise e
        redis_retry.inc_count(key)
        raise AgentException(e)
    except Exception as e:
        raise UnknownException(e) from e

    return agent_instance


def publish_transactions(agent_instance, scheme_account_id, user_set, tid):
    transactions = agent_instance.transactions()
    publish.transactions(
        [transaction_tuple_to_dict(tx) for tx in transactions],
        scheme_account_id,
        user_set,
        tid,
    )
