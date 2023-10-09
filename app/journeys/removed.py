from werkzeug.exceptions import NotFound

from app.journeys.common import get_agent_class
from app.reporting import get_logger

log = get_logger("removed-journey")


def agent_loyalty_card_removed(scheme_slug: str, user_info: dict):
    agent_instance = None
    error = None
    try:
        agent_class = get_agent_class(scheme_slug)
        agent_instance = agent_class(1, user_info, scheme_slug)
        agent_instance.loyalty_card_removed()
    except NotFound:
        error = f"Trying to report loyalty cards removed bink: Unknown Scheme {scheme_slug}"
    except Exception as e:
        error = f"Exception {e} Trying to report loyalty cards removed bink for {scheme_slug}"

    return {"agent": agent_instance, "error": error}


def attempt_loyalty_card_removed(scheme_slug: str, user_info: dict):
    """
    Modelled on join journey and makes testing of agent_loyalty_card_removed easier

    This may be expanded to be the retry target should we need to retry the removed message
    """
    result = agent_loyalty_card_removed(scheme_slug, user_info)
    if result.get("error"):
        log.warning(result["error"])
