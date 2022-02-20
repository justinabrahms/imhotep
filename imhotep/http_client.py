import json
import logging

import requests
from requests.auth import HTTPBasicAuth


log = logging.getLogger(__name__)


class NoGithubCredentials(Exception):
    pass


class BasicAuthRequester(object):
    """
    Object used for issuing authenticated API calls.
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_auth(self):
        return HTTPBasicAuth(self.username, self.password)

    def get(self, url):
        log.debug("Fetching %s", url)

        response = requests.get(url, auth=self.get_auth())
        if response.status_code > 400:
            log.warning("Error on GET to %s. Response: %s", url,
                        response.content)
        return response

    def delete(self, url):
        log.debug("Deleting %s", url)
        return requests.delete(url, auth=self.get_auth())

    def post(self, url, payload):
        log.debug("Posting %s to %s", payload, url)
        response = requests.post(url, data=json.dumps(payload),
                                 auth=self.get_auth())
        if response.status_code > 400:
            log.warning("Error on POST to %s. Response: %s", url,
                        response.content)
        return response
