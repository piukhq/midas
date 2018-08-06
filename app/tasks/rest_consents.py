from .resend import ReTryTaskStore
from settings import HERMES_URL
import importlib

import requests


def send_consents(url, headers, message, confirm_dic, retries=10, state='Consents', log_errors=False, identifier='',
                  verify = None, verify_decode=None):
    consents_data = {
        "url": url,  # set to scheme url for consent
        "headers": headers,
        "message": message,  # set to message body encoded as required
        "confirm": confirm_dic,  # dic of user consent id and remaining retries for each
        "retries": retries,  # retries for consent send to agent
        "state": state,  # set to first state Consents
    }
    if log_errors:
        consents_data['errors'] = []
        consents_data['identifier'] = identifier

    if verify:
        consents_data['verify'] = verify

    sent, message = try_consents(consents_data)
    if not sent:
        if log_errors:
            consents_data["errors"].append(message)
        task = ReTryTaskStore()
        task.set_task("app.tasks.rest_consents", "try_consents", consents_data)


def try_consents(consents_data):
    """ This function  requires a consents data to be set in 
           
    If successful assume response 200 to 204 is received then for each consent id put consent_confirmed to
    Hermes

    The routine should manage state of process so that only when complete of fatal error will it return true
    It is therefore possible to continue retries if an internal log status message fails
    :param consents_data:
    :return:  Tuple:
                continue_status: True to terminate any retries, False to continue to rety
                response_list:  list of logged errors (successful one will not be wriiten to redis)
    """

    try:
        if consents_data['state'] == "Consents":
            resp = requests.post(consents_data['url'], data=consents_data['message'], timeout=10,
                                 headers=consents_data['headers'])
            if resp.status_code not in (200, 201, 202, 204):
                return False, f"{consents_data.get('identifier','')} " \
                              f"{consents_data['state']}: Error Code {resp.status_code}"
            else:
                if consents_data.get('verify'):
                    module = importlib.import_module(consents_data['verify'])
                    func = getattr(module, consents_data.get('verify_function','verify'))
                    ok, message = func(resp)
                    if not ok:
                        return False, f"{consents_data.get('identifier','')} " \
                                      f"{consents_data['state']}: Error Found {message}"
                consents_data['state'] = "Confirm"
        send_errors = []
        consents_data['retries'] = 0
        if consents_data['state'] == "Confirm":
            for user_consent_id, retry_confirm in consents_data['confirm'].items():
                if retry_confirm > 0:
                    resp = requests.put(f'{HERMES_URL}/schemes/userconsent/confirmed/{user_consent_id}', timeout=10)
                    if resp.status_code == 200:
                        consents_data['confirm'][user_consent_id] = 0   # no more retries for this message

                    else:
                        consents_data['confirm'][user_consent_id] -= 1
                        send_errors.append(f' User consent id {user_consent_id} status code {resp.status_code}')
                consents_data['retries'] += consents_data['confirm'][user_consent_id]

            if consents_data['retries'] == 0:
                consents_data["state"] = "done"
                return True, "done"
            else:
                return False,\
                       f"{consents_data.get('identifier','')} {consents_data['state']}:" \
                       f" Hermes confirm err {''.join(send_errors)}"

        return False, "Internal Error"
    except AttributeError as e:
        # If data is invalid or missing parameters no point in retrying so abort
        return True, f"{consents_data.get('identifier','')} {consents_data['state']}: Attribute error {str(e)}"
    except IOError as e:
        return False, f"{consents_data.get('identifier','')} {consents_data['state']}: IO error {str(e)}"
