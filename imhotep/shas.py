from collections import namedtuple

Remote = namedtuple('Remote', ('name', 'url'))
CommitInfo = namedtuple("CommitInfo", ('commit', 'origin', 'remote_repo','ref'))


class PRInfo(object):
    def __init__(self, json):
        self.json = json

    @property
    def base_sha(self):
        return self.json['base']['sha']

    @property
    def head_sha(self):
        return self.json['head']['sha']

    @property
    def base_ref(self):
        return self.json['base']['ref']

    @property
    def head_ref(self):
        return self.json['head']['ref']

    @property
    def has_remote_repo(self):
        return self.json['base']['repo']['owner']['login'] != \
               self.json['head']['repo']['owner']['login']

    @property
    def remote_repo(self):
        remote = None
        if self.has_remote_repo:
            remote = Remote(name=self.json['head']['repo']['owner']['login'],
                            url=self.json['head']['repo']['ssh_url'])
        return remote

    def to_commit_info(self):
        return CommitInfo(self.base_sha, self.head_sha, self.remote_repo, self.head_ref)


def get_pr_info(requester, reponame, number):
    "Returns the PullRequest as a PRInfo object"
    resp = requester.get(
        'https://api.github.com/repos/%s/pulls/%s' % (reponame, number))
    return PRInfo(resp.json)
