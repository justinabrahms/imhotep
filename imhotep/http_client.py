import json
import logging
from typing import Dict

import requests
from requests.auth import HTTPBasicAuth
from requests.models import Response

log = logging.getLogger(__name__)


class NoGithubCredentials(Exception):
    pass


class BasicAuthRequester:
    """
    Object used for issuing authenticated API calls.
    """

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def get_auth(self) -> HTTPBasicAuth:
        return HTTPBasicAuth(self.username, self.password)

    def get(self, url: str) -> Response:
        log.debug("Fetching %s", url)

        response = requests.get(url, auth=self.get_auth())
        if response.status_code > 400:
            log.warning("Error on GET to %s. Response: %s", url, response.content)
        return response

    def delete(self, url):
        log.debug("Deleting %s", url)
        return requests.delete(url, auth=self.get_auth())

    def post(self, url: str, payload: Dict) -> Response:
        log.debug("Posting %s to %s", payload, url)
        response = requests.post(url, data=json.dumps(payload), auth=self.get_auth())
        if response.status_code > 400:
            log.warning("Error on POST to %s. Response: %s", url, response.content)
        return response
