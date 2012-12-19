from collections import defaultdict
import logging
import os
from tempfile import mkdtemp
import envoy
import requests
from requests.auth import HTTPBasicAuth
import json


logging.basicConfig()
log = logging.getLogger(__name__)


class Tool(object):
    def invoke(self, dirname, filenames=set()):
        """
        Returns results in the format of:

        {'filename': {
          'line_number': {
            'error1',
            'error2'
            }
          }
        }

        """
        raise NotImplementedError


class PyLint(Tool):
    pylintrc_filename = '.pylintrc'

    def invoke(self, dirname, filenames=set()):
        to_return = defaultdict(lambda: defaultdict(list))
        log.debug("Running pylint on %s", dirname)
        cmd = 'find %s -name "*.py" | ' \
          'xargs pylint --output-format=parseable -rn'

        if os.path.exists(os.path.join(dirname, self.pylintrc_filename)):
            cmd += " --rcfile=%s" % os.path.join(
                dirname, self.pylintrc_filename)

        result = envoy.run(cmd % dirname)
        # splitting based on newline + dirname and trailing slash will make
        # beginning of line until first colon the relative filename. It also has
        # the nice side effect of allowing us multi-line output from the tool
        # without things breaking.
        for line in result.std_out.split("\n%s/" % dirname):
            if len(line) == 0:
                continue
            filename, line_num, error = line.split(':', 2)
            if len(filenames) != 0 and filename not in filenames:
                continue
            to_return[filename][line_num].append(error)
        return to_return


class RepoManager(object):
    """
    Manages creation and deletion of `Repository` objects.
    """
    to_cleanup = {}

    def __init__(self, cleanup=False):
        self.should_cleanup = cleanup

    # TODO(justinabrahms): Implement caching of repos.
    def clone_repo(self, repo_name):
        "Clones the given repo and returns the Repository object."
        dired_repo_name = repo_name.replace('/', '__')
        dirname = mkdtemp(suffix=dired_repo_name)

        self.to_cleanup[repo_name] = dirname
        repo = Repository(repo_name, dirname)
        log.debug("Cloning %s to %s", repo.download_location, dirname)
        envoy.run("git clone %s %s" % (repo.download_location, dirname))
        return repo

    def cleanup(self):
        if self.should_cleanup:
            for repo_dir in self.to_cleanup.values():
                log.debug("Cleaning up %s", repo_dir)
                envoy.run('rm -rf %s' % repo_dir)


class Repository(object):
    """
    Represents a github repository (both in the abstract and on disk).
    """
    def __init__(self, name, loc):
        self.name = name
        self.dirname = loc

    @property
    def download_location(self):
        return "git://github.com/%s.git" % self.name

    def __unicode__(self):
        return self.name

    def get_tools(self):
        return [PyLint()]


def apply_commit(repo, commit):
    envoy.run("cd %s && git checkout %s" % (repo.dirname, commit))


def run_analysis(repo, filenames=set()):
    results = {}
    for tool in repo.get_tools():
        log.debug("running %s" % tool.__class__.__name__)
        run_results = tool.invoke(repo.dirname, filenames=filenames)
        results.update(run_results)
    return results


class ResultSet(object):
    def __init__(self):
        self.results = []

    def add(self, filename, line, result):
        self.results.append({'filename': filename,
                             'line': int(line),
                             'result': result})

    def sort(self):
        self.results.sort(key=lambda x: (x['filename'], x['line']))

    def github_print(self):
        return '\n'.join("%s:%s - %s" % (x['filename'], x['line'], x['result'])
                         for x in self.results)

def post_comments(repo, credentials, commit, results):
    payloads = []
    rs = ResultSet()
    for filename, line_results in results.items():
        for line, results in line_results.items():
            for result in results:
                rs.add(filename, line, result)

    rs.sort()
    body_txt = "Found the following errors:\n\n%s" % rs.github_print()

    # auth to github
    # post commit comment for file in results.
    resp = requests.post(
        'https://api.github.com/repos/%s/commits/%s/comments' % (repo.name,
                                                                 commit),
        data=json.dumps({'body': body_txt}),
        auth=HTTPBasicAuth(credentials['user'],
                           credentials['password']))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Posts static analysis results to github.")
    parser.add_argument(
        '--repo_name', required=True,
        help="Github repository name in owner/repo format")
    parser.add_argument('--commit', required=True,
                        help="The sha of the commit to run static analysis on.")
    parser.add_argument(
        '--filenames', nargs="+",
        help="filenames you want static analysis to be limited to.")
    parser.add_argument(
        '--debug', action='store_true',
        help="Will dump debugging output and won't clean up after itself.")
    parser.add_argument(
        '--github-username',
        required=True,
        help='Github user to post comments as.')
    parser.add_argument(
        '--github-password',
        required=True,
        help='Github password for the above user.')
    # parse out repo name
    args = parser.parse_args()
    repo_name = args.repo_name
    commit = args.commit

    if args.debug:
        log.setLevel(logging.DEBUG)

    credentials = {
        'user': args.github_username,
        'password': args.github_password
    }

    manager = RepoManager(cleanup=args.debug)
    try:
        repo = manager.clone_repo(repo_name)
        apply_commit(repo, commit)
        results = run_analysis(repo, filenames=set(args.filenames or []))
        post_comments(repo, credentials, commit, results)
    finally:
        manager.cleanup()
