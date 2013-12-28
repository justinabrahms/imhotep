import requests
import json
from requests.auth import HTTPBasicAuth


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
        return requests.get(url, auth=self.get_auth())

    def post(self, url, payload):
        return requests.post(
            url, data=json.dumps(payload),
            auth=self.get_auth())
