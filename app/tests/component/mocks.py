from http import HTTPMethod, HTTPStatus
from typing import Any
from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoint:
    method: HTTPMethod
    url: str
    response_status: HTTPStatus
    response_body: dict[str, Any]
