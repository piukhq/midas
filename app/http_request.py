import socket

from settings import SERVICE_API_KEY


def get_headers(tid):
    headers = {
        "Content-type": "application/json",
        "transaction": str(tid),
        "User-agent": f"Midas on {socket.gethostname()}",
        "Authorization": "token " + SERVICE_API_KEY,
    }

    return headers
