import arrow
from app import constants
from app.agents.acteol import Acteol


class Wasabi(Acteol):
    AUTH_TOKEN_TIMEOUT = 75600  # n_seconds in 21 hours
    RETAILER_ID = "315"

    def _get_registration_credentials(self, credentials: dict, consents: dict) -> dict:
        return {
            "email": credentials[constants.EMAIL],
            "first_name": credentials[constants.FIRST_NAME],
            "surname": credentials[constants.LAST_NAME],
            "join_date": arrow.utcnow().format("YYYY-MM-DD"),
            "email_marketing": consents["email_marketing"],
            "source": "channel",
            "validated": True,
        }
