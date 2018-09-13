import typing as t

import requests
from flask_restful import Resource
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from app import retry, AgentException, UnknownException, sentry
from app.agents.exceptions import AgentError, SERVICE_CONNECTION_ERROR, RegistrationError, UNKNOWN
from app.configuration import Configuration
from app.encryption import hash_ids
from app.resources import get_agent_class, create_response, decrypt_credentials
from app.scheme_account import update_pending_join_account
from app.utils import SchemeAccountStatus, JourneyTypes
from app.security.utils import authorise
from settings import SERVICE_API_KEY, HERMES_URL


class JoinCallback(Resource):

    @authorise(Configuration.JOIN_HANDLER)
    def post(self, scheme_slug, data, config):
        try:
            message_uid = data['message_uid']
            scheme_account_id = hash_ids.decode(data['record_uid'])
            if not scheme_account_id:
                raise ValueError('The record_uid provided is not valid')

            user_info = {
                'credentials': self._collect_credentials(scheme_account_id[0]),
                'status': SchemeAccountStatus.PENDING,
                'scheme_account_id': scheme_account_id[0],
                'journey_type': JourneyTypes.JOIN.value
            }
        except (KeyError, ValueError, AttributeError) as e:
            sentry.captureException()
            raise UnknownException(e) from e
        except (requests.ConnectionError, AgentError) as e:
            sentry.captureException()
            raise AgentException(RegistrationError(SERVICE_CONNECTION_ERROR)) from e

        try:
            agent_class = get_agent_class(scheme_slug)

            key = retry.get_key(agent_class.__name__, user_info['scheme_account_id'])
            retry_count = retry.get_count(key)
            agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug, config=config)

            agent_instance.register(data, inbound=True)
        except AgentError as e:
            update_pending_join_account(user_info['scheme_account_id'], str(e), message_uid, raise_exception=False)
            sentry.captureException()
            raise AgentException(e)
        except Exception as e:
            update_pending_join_account(user_info['scheme_account_id'], str(e), message_uid, raise_exception=False)
            sentry.captureException()
            raise UnknownException(e)

        return create_response({'success': True})

    @staticmethod
    def _collect_credentials(scheme_account_id):
        session = requests_retry_session()
        response = session.get('{0}/schemes/accounts/{1}/credentials'.format(HERMES_URL, scheme_account_id),
                               headers={'Authorization': f'Token {SERVICE_API_KEY}'})

        if not response.ok:
            raise AgentError(UNKNOWN)

        credentials = decrypt_credentials(response.json()['credentials'])

        return credentials


def requests_retry_session(retries: int = 3,
                           backoff_factor: float = 0.3,
                           status_forcelist: t.Tuple = (500, 502, 504),
                           session: requests.Session = None) -> requests.Session:
    """Create a requests session with the given retry policy.
    This method will create a new session if an existing one is not provided.
    See here for more information about this functionality:
    https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html?highlight=forcelist#urllib3.util.retry.Retry"""
    if session is None:
        session = requests.Session()

    retry = Retry(
        total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist)

    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session
