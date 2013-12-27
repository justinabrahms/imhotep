from collections import defaultdict, namedtuple
import json
import logging
import os
import re
from pkg_resources import iter_entry_points
import requests
from requests.auth import HTTPBasicAuth
import subprocess
import sys
from tempfile import mkdtemp

from reporters import PrintingReporter, CommitReporter, PRReporter
from tools import PyLint, JSHint
from github_parse import DiffContextParser
from pull_requests import get_pr_info


logging.basicConfig()
log = logging.getLogger(__name__)


Remote = namedtuple('Remote', ['name', 'url'])

class GithubRequester(object):
    """
    Object used for issuing authenticated API calls to GitHub.
    """
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_auth(self):
        return HTTPBasicAuth(self.username, self.password)

    def get(self, url):
        return requests.get(url, auth=self.get_auth())

    def post(self, url, payload):
        return requests.post(
            url, data=json.dumps(payload),
            auth=self.get_auth())


def run(cmd):
    log.debug("Running: %s", cmd)
    return subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True).communicate()[0]


class RepoManager(object):
    """
    Manages creation and deletion of `Repository` objects.
    """
    to_cleanup = {}

    def __init__(self, authenticated=False, cache_directory=None, tools=None):
        self.should_cleanup = cache_directory is None
        self.authenticated = authenticated
        self.cache_directory = cache_directory
        self.tools = tools or []

    def get_repo_class(self):
        if self.authenticated:
            return AuthenticatedRepository
        return Repository

    def clone_repo(self, repo_name, remote_repo):
        "Clones the given repo and returns the Repository object."
        dired_repo_name = repo_name.replace('/', '__')
        if not self.cache_directory:
            dirname = mkdtemp(suffix=dired_repo_name)
        else:
            dirname = os.path.abspath("%s/%s" % (
                self.cache_directory, dired_repo_name))
        self.to_cleanup[repo_name] = dirname
        klass = self.get_repo_class()
        repo = klass(repo_name, dirname, tools)
        if os.path.isdir("%s/.git" % dirname):
            log.debug("Updating %s to %s", repo.download_location, dirname)
            run("cd %s && git checkout master && git pull --all" % dirname)
        else:
            log.debug("Cloning %s to %s", repo.download_location, dirname)
            run("git clone %s %s" % (repo.download_location, dirname))

        if remote_repo is not None:
            log.debug("Pulling remote branch from %s", remote_repo.url)
            run("cd %s && git remote add %s %s" % (dirname,
                                                   remote_repo.name,
                                                   remote_repo.url))
            run("cd %s && git pull --all" % dirname)
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
    def __init__(self, name, loc, tools):
        self.name = name
        self.dirname = loc
        self.tools = tools

    @property
    def download_location(self):
        return "git://github.com/%s.git" % self.name

    def __unicode__(self):
        return self.name

    def get_tools(self):
        return self.tools


class AuthenticatedRepository(Repository):
    @property
    def download_location(self):
        return "git@github.com:%s.git" % self.name


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


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Posts static analysis results to github.")
    parser.add_argument(
        '--repo_name', required=True,
        help="Github repository name in owner/repo format")
    parser.add_argument(
        '--commit',
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
    parser.add_argument(
        '--no-post',
        action="store_true",
        help="[DEBUG] will print out comments rather than posting to github.")
    parser.add_argument(
        '--authenticated',
        action="store_true",
        help="Indicates the repository requires authentication")
    parser.add_argument(
        '--pr-number',
        help="Number of the pull request to comment on")
    parser.add_argument(
        '--cache-directory',
        help="Path to directory to cache the repository",
        type=str,
        required=False)
    # parse out repo name
    args = parser.parse_args()

    if args.commit == "" and args.pr_number == "":
        print "You must specify a commit or PR number"
        sys.exit(1)

    repo_name = args.repo_name
    commit = args.commit
    origin_commit = args.origin_commit
    no_post = args.no_post
    gh_req = GithubRequester(args.github_username, args.github_password)
    pr_num = args.pr_number
    remote_repo = None
    tools = []

    for ep in iter_entry_points(group='imhotep_linters'):
        klass = ep.load()
        tools.append(klass(run))

    if pr_num != '':
        pr_info = get_pr_info(gh_req, repo_name, pr_num)
        origin_commit = pr_info.head_sha
        commit = pr_info.base_sha
        if pr_info.has_remote_repo:
            remote_repo = pr_info.remote_repo

        reporter = PRReporter(gh_req, pr_num)

    elif commit is not None:
        reporter = CommitReporter(gh_req)

    if no_post:
        reporter = PrintingReporter()

    if args.debug:
        log.setLevel(logging.DEBUG)

    manager = RepoManager(authenticated=args.authenticated,
                          cache_directory=args.cache_directory,
                          tools=tools)

    try:
        repo = manager.clone_repo(repo_name, remote_repo=remote_repo)
        diff = apply_commit(repo, commit, origin_commit)
        results = run_analysis(repo, filenames=set(args.filenames or []))
        # Move out to its own thing
        dcp = DiffContextParser(diff)
        z = dcp.parse()

        for entry in z:
            added_lines = [l.number for l in entry.added_lines]
            posMap = {}
            for x in entry.added_lines:
                posMap[x.number] = x.position

            violations = results.get(entry.result_filename, {})
            violating_lines = [int(l) for l in violations.keys()]

            matching_numbers = set(added_lines).intersection(violating_lines)
            for x in matching_numbers:
                reporter.report_line(
                    repo.name, commit, entry.result_filename, x,
                    posMap[x], violations['%s' % x])
        if not z:
            log.info("No violations. Kudos!")
    finally:
        manager.cleanup()
