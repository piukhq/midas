import json

import settings
from app.tests.service.logins import get_credentials

if __name__ == '__main__':
    open(settings.LOCAL_CREDENTIALS_FILE, 'w').close()
    with open(settings.LOCAL_CREDENTIALS_FILE, 'w') as f:
        f.write(json.dumps(get_credentials(), indent=4, sort_keys=True))
