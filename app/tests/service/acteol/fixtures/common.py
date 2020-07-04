import pytest
import os
from unittest.mock import MagicMock, patch

from app.agents.acteol import Wasabi
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS


@pytest.fixture(scope="function")
def wasabi():
    with patch("app.agents.acteol.Configuration") as mock_config:

        mock_config_object = MagicMock()
        mock_config_object.merchant_url = "https://wasabiuat.wasabiworld.co.uk/"
        mock_config_object.security_credentials = {
            "outbound": {
                "credentials": [
                    {
                        "value": {
                            "username": os.environ.get("WASABI_USERNAME"),
                            "password": os.environ.get("WASABI_PASSWORD"),
                        }
                    }
                ]
            }
        }
        mock_config.return_value = mock_config_object

        wasabi = Wasabi(*AGENT_CLASS_ARGUMENTS, scheme_slug="wasabi-club")

        yield wasabi


@pytest.fixture(scope="function")
def clean_up_user():
    def _clean_up_user(wasabi, email) -> [int, None]:
        contact_ids = wasabi.get_contact_ids_by_email(email=email)
        if contact_ids["CtcIDs"]:
            ctcid = contact_ids["CtcIDs"][0]["CtcID"]
            delete_response = wasabi.delete_contact_by_ctcid(ctcid=ctcid)

            return delete_response.status_code

    return _clean_up_user
