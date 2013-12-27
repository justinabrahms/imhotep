class Repository(object):
    """
    Represents a github repository (both in the abstract and on disk).
    """
    def __init__(self, name, loc, tools):
        self.name = name
        self.dirname = loc
        self.tools = tools

    @property
    def download_location(self):
        return "git://github.com/%s.git" % self.name

    def __unicode__(self):
        return self.name


class AuthenticatedRepository(Repository):
    @property
    def download_location(self):
        return "git@github.com:%s.git" % self.name
