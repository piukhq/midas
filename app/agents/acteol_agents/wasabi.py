from app.agents.acteol import Acteol


class Wasabi(Acteol):
    AUTH_TOKEN_TIMEOUT = 75600  # n_seconds in 21 hours
    RETAILER_ID = "315"
