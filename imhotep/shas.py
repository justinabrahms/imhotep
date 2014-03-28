from collections import namedtuple

Remote = namedtuple('Remote', ('name', 'url'))
CommitInfo = namedtuple("CommitInfo",
                        ('commit', 'origin', 'remote_repo', 'ref'))


class PRInfo(object):
    def __init__(self,
                 base_sha,
                 base_ref,
                 base_repo_login,
                 head_sha,
                 head_ref,
                 head_repo_login,
                 head_repo_ssh):
        self.base_sha = base_sha
        self.head_sha = head_sha
        self.base_ref = base_ref
        self.head_ref = head_ref
        self.base_repo_login = base_repo_login
        self.head_repo_login = head_repo_login
        self.head_repo_ssh = head_repo_ssh

    @property
    def has_remote_repo(self):
        return self.base_repo_login != self.head_repo_login

    @property
    def remote_repo(self):
        remote = None
        if self.has_remote_repo:
            remote = Remote(name=self.head_repo_login,
                            url=self.head_repo_ssh)
        return remote

    def to_commit_info(self):
        return CommitInfo(self.base_sha, self.head_sha, self.remote_repo,
                          self.head_ref)


def get_gh_pr_info(requester, reponame, number):
    "Returns the PullRequest as a PRInfo object"
    resp = requester.get(
        'https://api.github.com/repos/%s/pulls/%s' % (reponame, number))
    pr = resp.json()

    return PRInfo(pr['base']['sha'],
                  pr['base']['ref'],
                  pr['base']['repo']['owner']['login'],
                  pr['head']['sha'],
                  pr['head']['ref'],
                  pr['head']['repo']['owner']['login'],
                  pr['head']['repo']['ssh_url'])


def stash_ssh_url(clone_urls):
    for url in clone_urls:
        if url['name'] == 'ssh':
            return url['href']


def get_stash_pr_info(requester, stash_server, reponame, number):
    project, reponame = reponame.split('/')
    url = "/rest/api/1.0/projects/%s/repos/%s/pull-requests/%s"
    request_url = url % (stash_server, project, reponame, number)
    resp = requester.get(request_url)
    pr = resp.json()

    # stash has sort of a stupid json for PRs.
    base_sha = pr['toRef']['latestChangeset']
    base_ref = pr['toRef']['displayId']
    base_repo_login = pr['toRef']['repository']['project']['name']
    head_sha = pr['fromRef']['latestChangeset']
    head_ref = pr['fromRef']['displayId']
    head_repo_login = pr['fromRef']['repository']['project']['name']
    head_ssh_url = stash_ssh_url(pr['fromRef']['repository']['links']['clone'])
    return PRInfo(base_sha,
                  base_ref,
                  base_repo_login,
                  head_sha,
                  head_ref,
                  head_repo_login,
                  head_ssh_url)

