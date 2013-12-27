import os
from collections import namedtuple

dir = os.path.dirname(__file__)
fixture_path = lambda s: os.path.join(dir, 'fixtures/', s)


json_wrapper = namedtuple('wrapper', ('json',))
class Requester(object):
    def __init__(self, fixture):
        self.fixture = fixture

    def get(self, url):
        self.url = url
        return json_wrapper(self.fixture)

    def post(self, url, data):
        self.url = url
        self.data = data
        return json_wrapper(self.fixture)
