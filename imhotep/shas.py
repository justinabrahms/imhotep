from collections import namedtuple

Remote = namedtuple('Remote', ('name', 'url'))
CommitInfo = namedtuple("CommitInfo",
                        ('commit', 'origin', 'remote_repo', 'ref'))


class PRInfo(object):

    def to_commit_info(self):
        raise NotImplementedError


class GithubPR(PRInfo):

    def __init__(self, requester, reponame, number, **kwargs):
        resp = requester.get(
            'https://api.github.com/repos/%s/pulls/%s' % (reponame, number))
        self.json =  resp.json()

    @property
    def base_sha(self):
        return self.json['base']['sha']

    @property
    def base_ref(self):
        return self.json['base']['ref']

    @property
    def head_sha(self):
        return self.json['head']['sha']

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
                            url=self.json['head']['repo']['clone_url'])
        return remote

    def to_commit_info(self):
        return CommitInfo(self.base_sha, self.head_sha, self.remote_repo,
                          self.head_ref)


class StashPR(PRInfo):

    def __init__(self, requester, reponame, number, **kwargs):
        url = 'https://{stash_host}/rest/api/1.0/projects/{project}/repos/{repo}/pull-requests/{pr}'.format(
            project=kwargs['project_name'], repo=reponame, pr=number, stash_host=kwargs['stash_host'])
        self.json = requester.get(url).json()

    @property
    def base_sha(self):
        return self.json['fromRef']['latestChangeset']

    @property
    def base_ref(self):
        return self.json['fromRef']['id']

    @property
    def head_sha(self):
        return self.json['toRef']['latestChangeset']

    @property
    def head_ref(self):
        return self.json['toRef']['id']

    @property
    def has_remote_repo(self):
        # TODO:
        return True

    @property
    def remote_repo(self):
        # TODO: always return ssh or use https and auth creds?
        repo = self.json['fromRef']['repository']['links']['clone'][0]
        if repo['name'] == 'http':
            repo = self.json['fromRef']['repository']['links']['clone'][1]
        url = repo['href']
        name = self.json['fromRef']['repository']['name']

        return Remote(name=name, url=url)

    def to_commit_info(self):
        return CommitInfo(self.base_sha, self.head_sha, self.remote_repo,
                          self.head_ref)
