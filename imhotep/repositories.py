import logging

log = logging.getLogger(__name__)


class ToolsNotFound(Exception):
    pass


class Repository:
    """
    Represents a github repository (both in the abstract and on disk).
    """

    def __init__(self, name, loc, tools, executor, shallow=False, domain="github.com"):
        if len(tools) == 0:
            raise ToolsNotFound()

        self.name = name
        self.dirname = loc
        self.tools = tools
        self.executor = executor
        self.shallow = shallow
        self.domain = domain

    @property
    def download_location(self):
        return f"https://{self.domain}/{self.name}.git"

    def apply_commit(self, commit):
        """
        Updates the repository to a given commit.
        """
        self.executor(f"cd {self.dirname} && git checkout {commit}")

    def diff_commit(self, commit, compare_point=None):
        """
        Returns a diff as a string from the current HEAD to the given commit.
        """
        # @@@ This is a security hazard as compare-point is user-passed in
        # data. Doesn't matter until we wrap this in a service.
        if compare_point is not None:
            self.apply_commit(compare_point)
        return self.executor(f"cd {self.dirname} && git diff {commit}")

    def __unicode__(self):
        return self.name


class AuthenticatedRepository(Repository):
    @property
    def download_location(self):
        return f"git@{self.domain}:{self.name}.git"
