import json

from sqlalchemy import create_engine, text

from app.encryption import AESCipher
from settings import AES_KEY, HELIOS_DB_URI

# ------------------------------------------------------- #
# - When running test locally from console please add --- #
# - this at the top of the agent just under the imports - #
# ------------------------------------------------------- #

# if not CREDENTIALS:
#     update_credentials()
#     from app.tests.service.logins import CREDENTIALS

CREDENTIALS = None


def get_credentials(agent=None):
    """
    Retrieve midas' agent test credentials from the database for the specified agent
    if one is provided or for all the agents if called without arguments.
    :param agent: loyalty scheme name as used in the tests
    :type agent: str
    :return: dictionary of credentials
    """
    engine = create_engine(HELIOS_DB_URI)
    where = "WHERE app_agent.loyalty_scheme = '{}';".format(agent) if agent else ";"
    query = text(
        "SELECT app_agent.slug, app_credential.field, app_credential.value "
        "FROM app_agent JOIN app_credential "
        "ON app_agent.id = app_credential.agent_id %s" % where
    )

    result = engine.execute(query)

    # we have to add these test credentials here for the test_login_fail case in each agent's test.
    credentials = {
        'bad': {
            'username': "234234@bad.com",
            'email': "234234@bad.com",
            'password': "234234"
        }
    }

    for row in result:
        if credentials.get(row.slug):
            credentials[row.slug].update({row.field: row.value})

        else:
            credentials[row.slug] = {row.field: row.value}

    return credentials


def encrypt(scheme_slug):
    """For testing encryption"""
    aes = AESCipher(AES_KEY.encode())

    return aes.encrypt(json.dumps(CREDENTIALS[scheme_slug])).decode()


def update_credentials():
    """
    Update the CREDENTIALS dictionary with the latest values.
    :return: None
    """
    global CREDENTIALS
    CREDENTIALS = get_credentials()
