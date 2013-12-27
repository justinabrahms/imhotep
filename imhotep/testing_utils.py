import os

dir = os.path.dirname(__file__)
fixture_path = lambda s: os.path.join(dir, 'fixtures/', s)
