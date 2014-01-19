import logging
import os
from tempfile import mkdtemp

log = logging.getLogger(__name__)


class ToolsNotFound(Exception):
    pass


class Repository(object):
    """
    Represents a github repository (both in the abstract and on disk).
    """

    def __init__(self, name, loc, tools, executor):
        if len(tools) == 0:
            raise ToolsNotFound()

        self.name = name
        self.dirname = loc
        self.tools = tools
        self.executor = executor

    @property
    def download_location(self):
        return "git://github.com/%s.git" % self.name

    def apply_commit(self, commit):
        """
        Updates the repository to a given commit.
        """
        self.executor("cd %s && git checkout %s" % (self.dirname, commit))

    def diff_commit(self, commit, compare_point=None):
        """
        Returns a diff as a string from the current HEAD to the given commit.
        """
        # @@@ This is a security hazard as compare-point is user-passed in
        # data. Doesn't matter until we wrap this in a service.
        if compare_point is not None:
            self.apply_commit(compare_point)
        return self.executor("cd %s && git diff %s" % (self.dirname, commit))

    def run_tools(self, filenames=set()):
        results = {}
        for tool in self.tools:
            log.debug("running %s" % tool.__class__.__name__)
            run_results = tool.invoke(self.dirname, filenames=filenames)
            results.update(run_results)
        return results

    def __unicode__(self):
        return self.name


class AuthenticatedRepository(Repository):
    @property
    def download_location(self):
        return "git@github.com:%s.git" % self.name


class RepoManager(object):
    """
    Manages creation and deletion of `Repository` objects.
    """
    to_cleanup = {}

    def __init__(self, authenticated=False, cache_directory=None,
                 repo_name=None, remote_repo=None,
                 tools=None, executor=None):
        self.should_cleanup = cache_directory is None
        self.authenticated = authenticated
        self.cache_directory = cache_directory
        self.tools = tools or []
        self.executor = executor
        self.repo_name = repo_name
        self.remote_repo = remote_repo

    def get_repo_class(self):
        if self.authenticated:
            return AuthenticatedRepository
        return Repository

    def _clone_dir(self):
        dired_repo_name = self.repo_name.replace('/', '__')
        if not self.cache_directory:
            dirname = mkdtemp(suffix=dired_repo_name)
        else:
            dirname = os.path.abspath("%s/%s" % (
                self.cache_directory, dired_repo_name))
        return dirname

    def _clone_repo(self):
        """Clones the given repo and returns the Repository object."""
        dirname = self._clone_dir()
        self.to_cleanup[self.repo_name] = dirname
        klass = self.get_repo_class()
        repo = klass(self.repo_name, dirname, self.tools, self.executor)
        if os.path.isdir("%s/.git" % dirname):
            log.debug("Updating %s to %s", repo.download_location, dirname)
            self.executor(
                "cd %s && git checkout master && git pull --all" % dirname)
        else:
            log.debug("Cloning %s to %s", repo.download_location, dirname)
            self.executor(
                "git clone %s %s" % (repo.download_location, dirname))

        if self.remote_repo is not None:
            log.debug("Pulling remote branch from %s", self.remote_repo.url)
            self.executor("cd %s && git remote add %s %s" % (
                dirname, self.remote_repo.name, self.remote_repo.url))
            self.executor("cd %s && git pull --all" % dirname)
        return repo

    def diff_commit(self, commit, compare_point=None):
        if self.repo is None:
            self.repo = self._clone_repo()
        return self.repo.diff_commit(commit, compare_point=compare_point)

    def run_tools(self, filenames=set()):
        return self.repo.run_tools(self.tools, filenames=filenames)

    def cleanup(self):
        if self.should_cleanup:
            for repo_dir in self.to_cleanup.values():
                log.debug("Cleaning up %s", repo_dir)
                self.executor('rm -rf %s' % repo_dir)