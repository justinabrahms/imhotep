from collections import namedtuple

Remote = namedtuple('Remote', ['name', 'url'])


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
    def has_remote_repo(self):
        return self.json['base']['repo']['owner']['login'] != \
               self.json['head']['repo']['owner']['login']

    @property
    def remote_repo(self):
        return Remote(name=self.json['head']['repo']['owner']['login'],
                      url=self.json['head']['repo']['clone_url'])



def get_pr_info(requester, reponame, number):
    "Returns the PullRequest as a PRInfo object"
    resp = requester.get(
        'https://api.github.com/repos/%s/pulls/%s' % (reponame, number))
    return PRInfo(resp.json)
