import logging

log = logging.getLogger(__name__)


class ToolsNotFound(Exception):
    pass


class Repository(object):
    """
    Represents a github repository (both in the abstract and on disk).
    """

    def __init__(self, name, loc, tools, executor, shallow=False, **kwargs):
        if len(tools) == 0:
            raise ToolsNotFound()

        self.name = name
        self.dirname = loc
        self.tools = tools
        self.executor = executor
        self.shallow = shallow
        self.kwargs = kwargs

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
        return self.executor("cd %s && git diff %s..." % (self.dirname, commit))

    def __unicode__(self):
        return self.name


class AuthenticatedRepository(Repository):
    @property
    def download_location(self):
        return "git@github.com:%s.git" % self.name


class StashRepository(Repository):
    '''Exists because stash does PR diffs a bit differently.'''

    @property
    def download_location(self):
        # TODO: allow https vs ssh
        return 'ssh://git@{host}:7999/{project}/{repo}.git'.format(
            host=self.kwargs['stash_host'], project=self.kwargs['project'], repo=self.name)

    def diff_commit(self, commit, compare_point=None):
        """
        Returns a diff as a string from the current HEAD to the given commit.
        """
        # @@@ This is a security hazard as compare-point is user-passed in
        # data. Doesn't matter until we wrap this in a service.
        if compare_point is not None:
            self.apply_commit(compare_point)

        # stash does an actual  merge commit instead of triple dot diff
        merge_result = self.executor('cd %s && git merge %s' % (self.dirname, commit))
        if 'Automatic merge failed; fix conflicts and then commit the result.' in merge_result:
            raise Exception('Exiting since PR has a merge conflict. Fix conflict and run again.')
        return self.executor("cd %s && git diff %s" % (self.dirname, compare_point))
