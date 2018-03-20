### Local Testing
To run midas with a local copy of the credentials needed for agents' tests:
* set the environment variable CREDENTIALS_LOCAL to True (directly in setting.py if you are not using pipenv)
* run credentials_local.py

This will create a credentials.json file in `app/tests/service/credentials/` containing the latest credentials taken from the helios postgres database.