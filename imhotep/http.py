import requests
import json
from requests.auth import HTTPBasicAuth
import logging

log = logging.getLogger(__name__)

class NoGithubCredentials(Exception):
    pass

class GithubRequester(object):
    """
    Object used for issuing authenticated API calls to GitHub.
    """
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_auth(self):
        return HTTPBasicAuth(self.username, self.password)

    def get(self, url):
        log.debug("Fetching %s", url)
        return requests.get(url, auth=self.get_auth())

    def post(self, url, payload):
        log.debug("Posting %s to %s", payload, url)
        return requests.post(
            url, data=json.dumps(payload),
            auth=self.get_auth())
