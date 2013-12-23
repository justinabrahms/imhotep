from collections import defaultdict
import logging
import os
from tempfile import mkdtemp
import requests
from requests.auth import HTTPBasicAuth
import json
import subprocess

from github_parse import DiffContextParser


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

def run(cmd):
    return subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True).communicate()[0]


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

        result = run(cmd % dirname)
        # splitting based on newline + dirname and trailing slash will make
        # beginning of line until first colon the relative filename. It also has
        # the nice side effect of allowing us multi-line output from the tool
        # without things breaking.
        for line in result.split("\n%s/" % dirname):
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

    def __init__(self, ignore_cleanup=False):
        self.should_cleanup = not ignore_cleanup

    # TODO(justinabrahms): Implement caching of repos.
    def clone_repo(self, repo_name):
        "Clones the given repo and returns the Repository object."
        dired_repo_name = repo_name.replace('/', '__')
        dirname = mkdtemp(suffix=dired_repo_name)

        self.to_cleanup[repo_name] = dirname
        repo = Repository(repo_name, dirname)
        log.debug("Cloning %s to %s", repo.download_location, dirname)
        run("git clone %s %s" % (repo.download_location, dirname))
        return repo

    def cleanup(self):
        if self.should_cleanup:
            for repo_dir in self.to_cleanup.values():
                log.debug("Cleaning up %s", repo_dir)
                run('rm -rf %s' % repo_dir)


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



def apply_commit(repo, commit, compare_point="HEAD^"):
    # @@@ This is a security hazard as compare-point is user-passed in
    # data. Doesn't matter until we wrap this in a service.
    run("cd %s && git checkout %s" % (repo.dirname, commit))
    return run("cd %s && git diff %s" % (repo.dirname, compare_point))


def run_analysis(repo, filenames=set()):
    results = {}
    for tool in repo.get_tools():
        log.debug("running %s" % tool.__class__.__name__)
        run_results = tool.invoke(repo.dirname, filenames=filenames)
        results.update(run_results)
    return results


def commit_post(reponame, user, password, commit, position, txt, path):
    payload = {
        'body': txt,
        'sha': commit,
        'path': path,
        'position': position,
        'line': None,
    }
    print "Payload: %s" % payload
    return requests.post(
        'https://api.github.com/repos/%s/commits/%s/comments' % (reponame, commit),
        data=json.dumps(payload),
        auth=HTTPBasicAuth(user, password))


def pr_post(reponame, user, passw, num, position, txt):
    resp = requests.post(
        'https://api.github.com/repos/%s/pulls/%s/comments' % (reponame, num),
        data=json.dumps({
            'body': body_txt,
            'commit_id': '', # sha
            'path': '', # relative file path
            'position': 0, # line index into the diff
        }),
        auth=HTTPBasicAuth(user,
                           passw))


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
        '--origin-commit',
        required=False,
        default='HEAD^',
        help='Commit to use as the comparison point.')
    parser.add_argument(
        '--filenames', nargs="+",
        help="filenames you want static analysis to be limited to.")
    parser.add_argument(
        '--debug',
        action='store_true',
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
    origin_commit = args.origin_commit

    if args.debug:
        log.setLevel(logging.DEBUG)

    credentials = {
        'user': args.github_username,
        'password': args.github_password
    }

    manager = RepoManager(ignore_cleanup=args.debug)
    try:
        repo = manager.clone_repo(repo_name)
        diff = apply_commit(repo, commit, origin_commit)
        results = run_analysis(repo, filenames=set(args.filenames or []))
        # Move out to its own thing
        dcp = DiffContextParser(diff)
        z = dcp.parse()

        # TODO(justinabrahms): Should add a flag which swaps out the endpoint
        # for the pull request endpoint and auto-determines the diff-point (from
        # the branch point of the PR)
        for entry in z:
            added_lines = [l.number for l in entry.added_lines]
            posMap = {}
            for x in entry.added_lines:
                posMap[x.number] = x.position

            violations = results.get(entry.result_filename, {})
            violating_lines = [int(l) for l in violations.keys()]

            matching_numbers = set(added_lines).intersection(violating_lines)
            for x in matching_numbers:
                commit_post(repo.name, credentials['user'], credentials['password'],
                            commit, posMap[x], violations['%s' % x], entry.result_filename)
    finally:
        manager.cleanup()
