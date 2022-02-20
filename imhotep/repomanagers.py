import logging
import os
from tempfile import mkdtemp

from .repositories import Repository, AuthenticatedRepository

log = logging.getLogger(__name__)


class RepoManager(object):
    """
    Manages creation and deletion of `Repository` objects.
    """
    to_cleanup = {}

    def __init__(self, authenticated=False, cache_directory=None,
                 tools=None, executor=None, shallow_clone=False, domain=None):
        self.should_cleanup = cache_directory is None
        self.authenticated = authenticated
        self.cache_directory = cache_directory
        self.tools = tools or []
        self.executor = executor
        self.shallow = shallow_clone
        self.domain = domain

    def get_repo_class(self):
        if self.authenticated:
            return AuthenticatedRepository
        return Repository

    def clone_dir(self, repo_name):
        dired_repo_name = repo_name.replace('/', '__')
        if not self.cache_directory:
            dirname = mkdtemp(suffix=dired_repo_name)
        else:
            dirname = os.path.abspath("%s/%s" % (
                self.cache_directory, dired_repo_name))
        return dirname

    def fetch(self, dirname, remote_name, ref):
        log.debug("Fetching %s %s", remote_name, ref)
        self.executor("cd %s && git fetch --depth=1 %s %s" % (dirname,
                                                              remote_name,
                                                              ref))

    def pull(self, dirname):
        log.debug("Pulling all %s", dirname)
        self.executor("cd %s && git pull --all" % dirname)

    def add_remote(self, dirname, name, url):
        log.debug("Adding remote %s url: %s", name, url)
        self.executor("cd %s && git remote add %s %s" % (dirname,
                                                         name,
                                                         url))

    def set_up_clone(self, repo_name, remote_repo):
        """Sets up the working directory and returns a tuple of
        (dirname, repo )"""
        dirname = self.clone_dir(repo_name)
        self.to_cleanup[repo_name] = dirname
        klass = self.get_repo_class()
        repo = klass(repo_name,
                     dirname,
                     self.tools,
                     self.executor,
                     shallow=self.shallow_clone,
                     domain=self.domain)
        return (dirname, repo)

    def clone_repo(self, repo_name, remote_repo, ref):
        """Clones the given repo and returns the Repository object."""
        self.shallow_clone = False
        dirname, repo = self.set_up_clone(repo_name, remote_repo)
        if os.path.isdir("%s/.git" % dirname):
            log.debug("Updating %s to %s", repo.download_location, dirname)
            self.executor(
                "cd %s && git checkout master" % dirname)
            self.pull(dirname)
        else:
            log.debug("Cloning %s to %s", repo.download_location, dirname)
            self.executor(
                "git clone %s %s" % (repo.download_location, dirname))

        if remote_repo is not None:
            log.debug("Pulling remote branch from %s", remote_repo.url)
            self.add_remote(dirname,
                            remote_repo.name,
                            remote_repo.url)
            self.pull(dirname)
        return repo

    def cleanup(self):
        if self.should_cleanup:
            for repo_dir in self.to_cleanup.values():
                log.debug("Cleaning up %s", repo_dir)
                self.executor('rm -rf %s' % repo_dir)


class ShallowRepoManager(RepoManager):
    def __init__(self, *args, **kwargs):
        super(ShallowRepoManager, self).__init__(*args, **kwargs)

    def clone_repo(self, repo_name, remote_repo, ref):
        self.shallow_clone = True
        dirname, repo = self.set_up_clone(repo_name, remote_repo)
        remote_name = 'origin'
        log.debug("Shallow cloning.")
        download_location = repo.download_location
        log.debug("Creating stub git repo at %s" % (dirname))
        self.executor("mkdir -p %s" % (dirname, ))
        self.executor("cd %s && git init" % (dirname, ))
        log.debug("Adding origin repo %s " % (download_location))
        self.add_remote(dirname, 'origin', download_location)

        if remote_repo:
            self.add_remote(dirname, remote_repo.name, remote_repo.url)
            remote_name = remote_repo.name
        self.fetch(dirname, 'origin', 'HEAD')
        self.fetch(dirname, remote_name, ref)
        return repo
