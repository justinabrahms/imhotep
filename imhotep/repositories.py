import logging
from typing import Callable, List, Optional

from imhotep.tools import Tool

log = logging.getLogger(__name__)


class ToolsNotFound(Exception):
    pass


class Repository:
    """
    Represents a github repository (both in the abstract and on disk).
    """

    def __init__(
        self,
        name: str,
        loc: str,
        tools: List[Tool],
        executor: Optional[Callable],
        shallow: bool = False,
        domain: Optional[str] = "github.com",
    ) -> None:
        if len(tools) == 0:
            raise ToolsNotFound()

        self.name = name
        self.dirname = loc
        self.tools = tools
        self.executor = executor
        self.shallow = shallow
        if domain is None:
            self.domain = "github.com"
        else:
            self.domain = domain

    @property
    def download_location(self) -> str:
        return f"https://{self.domain}/{self.name}.git"

    def apply_commit(self, commit: str) -> None:
        """
        Updates the repository to a given commit.
        """
        if self.executor is None:
            log.error("Executor does not exist.")
            raise RuntimeError
        self.executor(f"cd {self.dirname} && git switch --detach {commit}")

    def diff_commit(self, commit: str, compare_point: Optional[str] = None) -> bytes:
        """
        Returns a diff as a string from the current HEAD to the given commit.
        """
        # @@@ This is a security hazard as compare-point is user-passed in
        # data. Doesn't matter until we wrap this in a service.
        if compare_point is not None:
            self.apply_commit(compare_point)
        if self.executor is None:
            log.error("Executor does not exist.")
            raise RuntimeError
        return self.executor(f"cd {self.dirname} && git diff {commit}")

    def __unicode__(self):
        return self.name


class AuthenticatedRepository(Repository):
    @property
    def download_location(self):
        return f"git@{self.domain}:{self.name}.git"
