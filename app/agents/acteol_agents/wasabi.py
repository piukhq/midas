from app.agents.acteol import Acteol


class Wasabi(Acteol):
    BASE_API_URL = "https://wasabiuat.wasabiworld.co.uk/api"
    ORIGIN_ROOT = "Bink-Wasabi"
    AUTH_TOKEN_TIMEOUT = 75600  # n_seconds in 21 hours
    RETAILER_ID = "315"
