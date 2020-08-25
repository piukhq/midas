import requests
import settings


def _azure_request(vault_name):
    url = f"{settings.AZURE_VAULT_URL}{settings.VAULT_SECRETS_PATH}{vault_name}"
    return requests.request('GET', url)


def _get_secret(vault_name):
    failed_message = f"FAILED to set {vault_name} from vault"
    value = None
    try:
        resp = _azure_request(vault_name)
        resp_dict = resp.json()
    except Exception as err:
        message = f"Bad vault response invalid JSON Exception: {err}"
        settings.logger.error(message)
    else:
        if resp_dict:
            data = resp_dict.get('data', {})
            value = data.get('data', None)
        if not value:
            settings.logger.error(failed_message)
    return value
