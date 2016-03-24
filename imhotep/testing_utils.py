import os
from collections import namedtuple

dir = os.path.dirname(__file__)


def fixture_path(s):
    return os.path.join(dir, 'fixtures/', s)


class JsonWrapper(object):
    def __init__(self, json, status):
        self.status_code = status
        self.payload = json

    def json(self):
        return self.payload


class Requester(object):
    def __init__(self, fixture):
        self.fixture = fixture

    def get(self, url):
        self.url = url
        return JsonWrapper(self.fixture, 200)

    def post(self, url, data):
        self.url = url
        self.data = data
        return JsonWrapper(self.fixture, 200)


def calls_matching_re(mockObj, regex):
    matches = []
    for call in mockObj.call_args_list:
        cmd = call[0][0]
        match = regex.search(cmd)
        if match:
            matches.append(call)

    return matches
