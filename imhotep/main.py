import json
import logging
import os
from pkg_resources import iter_entry_points
import subprocess
import sys
from tempfile import mkdtemp

from reporters import PrintingReporter, CommitReporter, PRReporter
from repositories import Repository, AuthenticatedRepository
from diff_parser import DiffContextParser
from pull_requests import get_pr_info
from http import GithubRequester, NoGithubCredentials
from errors import UnknownTools, NoCommitInfo


logging.basicConfig()
log = logging.getLogger(__name__)


def run(cmd, cwd='.'):
    log.debug("Running: %s", cmd)
    return subprocess.Popen(
        [cmd], stdout=subprocess.PIPE, shell=True, cwd=cwd).communicate()[0]


class RepoManager(object):
    """
    Manages creation and deletion of `Repository` objects.
    """
    to_cleanup = {}

    def __init__(self, authenticated=False, cache_directory=None,
                 tools=None, executor=None):
        self.should_cleanup = cache_directory is None
        self.authenticated = authenticated
        self.cache_directory = cache_directory
        self.tools = tools or []
        self.executor = executor

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

    def clone_repo(self, repo_name, remote_repo):
        """Clones the given repo and returns the Repository object."""
        dirname = self.clone_dir(repo_name)
        self.to_cleanup[repo_name] = dirname
        klass = self.get_repo_class()
        repo = klass(repo_name, dirname, self.tools, self.executor)
        if os.path.isdir("%s/.git" % dirname):
            log.debug("Updating %s to %s", repo.download_location, dirname)
            self.executor(
                "cd %s && git checkout master && git pull --all" % dirname)
        else:
            log.debug("Cloning %s to %s", repo.download_location, dirname)
            self.executor(
                "git clone %s %s" % (repo.download_location, dirname))

        if remote_repo is not None:
            log.debug("Pulling remote branch from %s", remote_repo.url)
            self.executor("cd %s && git remote add %s %s" % (dirname,
                                                             remote_repo.name,
                                                             remote_repo.url))
            self.executor("cd %s && git pull --all" % dirname)
        return repo

    def cleanup(self):
        if self.should_cleanup:
            for repo_dir in self.to_cleanup.values():
                log.debug("Cleaning up %s", repo_dir)
                self.executor('rm -rf %s' % repo_dir)


def run_analysis(repo, filenames=set()):
    results = {}
    for tool in repo.tools:
        log.debug("running %s" % tool.__class__.__name__)
        run_results = tool.invoke(repo.dirname, filenames=filenames)
        results.update(run_results)
    return results


def load_config(filename):
    config = {}
    if filename is not None:
        config_path = os.path.abspath(filename)
        try:
            with open(config_path) as f:
                config = json.loads(f.read())
        except IOError:
            log.error("Could not open config file %s", config_path)
        except ValueError:
            log.error("Could not parse config file %s", config_path)
    return config


def load_plugins():
    tools = []
    for ep in iter_entry_points(group='imhotep_linters'):
        klass = ep.load()
        tools.append(klass(run))
    return tools


class Imhotep(object):
    def __init__(self, requester=None, repo_manager=None,
                 repo_name=None, pr_number=None,
                 commit=None, origin_commit=None, no_post=None, debug=None,
                 filenames=None, **kwargs):
        # TODO(justinabrahms): kwargs exist until we handle cli params better
        # TODO(justinabrahms): This is a sprawling API. Tighten it up.
        self.requester = requester
        self.manager = repo_manager

        self.repo_name = repo_name
        self.pr_number = pr_number
        self.commit = commit
        self.origin_commit = origin_commit
        self.no_post = no_post
        self.debug = debug
        self.filenames = filenames

        if self.commit is None and self.pr_number is None:
            raise NoCommitInfo()

    def get_reporter(self):
        if self.no_post:
            return PrintingReporter()
        if self.pr_number:
            return PRReporter(self.requester, self.pr_number)
        elif self.commit is not None:
            return CommitReporter(self.requester)

    def invoke(self):
        commit = self.commit
        origin_commit = self.origin_commit
        remote_repo = None

        if self.pr_number is not None:
            pr_info = get_pr_info(self.requester, self.repo_name,
                                  self.pr_number)
            commit = pr_info.base_sha
            origin_commit = pr_info.head_sha
            if pr_info.has_remote_repo:
                remote_repo = pr_info.remote_repo

        reporter = self.get_reporter()

        if self.debug:
            log.setLevel(logging.DEBUG)

        try:
            repo = self.manager.clone_repo(self.repo_name,
                                           remote_repo=remote_repo)
            diff = repo.diff_commit(commit, compare_point=origin_commit)
            results = run_analysis(repo, filenames=set(self.filenames or []))
            # Move out to its own thing
            parser = DiffContextParser(diff)
            parse_results = parser.parse()

            error_count = 0
            for entry in parse_results:
                added_lines = [l.number for l in entry.added_lines]
                pos_map = {}
                for x in entry.added_lines:
                    pos_map[x.number] = x.position

                violations = results.get(entry.result_filename, {})
                violating_lines = [int(l) for l in violations.keys()]

                matching_numbers = set(added_lines).intersection(
                    violating_lines)
                for x in matching_numbers:
                    error_count += 1
                    reporter.report_line(
                        repo.name, origin_commit, entry.result_filename, x,
                        pos_map[x], violations['%s' % x])

            log.info("%d violations.", error_count)

        finally:
            self.manager.cleanup()


def gen_imhotep(**kwargs):
    req = GithubRequester(kwargs['github_username'],
                          kwargs['github_password'])

    plugins = load_plugins()
    tools = get_tools(kwargs['linter'], plugins)

    manager = RepoManager(authenticated=kwargs['authenticated'],
                          cache_directory=kwargs['cache_directory'],
                          tools=tools,
                          executor=run)
    return Imhotep(requester=req, repo_manager=manager, **kwargs)


def get_tools(whitelist, known_plugins):
    """
    Filter all known plugins by a whitelist specified. If the whitelist is
    empty, default to all plugins.
    """
    getpath = lambda c: "%s:%s" % (c.__module__, c.__class__.__name__)

    tools = [x for x in known_plugins if getpath(x) in whitelist]

    if not tools:
        if whitelist:
            raise UnknownTools(map(getpath, known_plugins))
        tools = known_plugins
    return tools


if __name__ == '__main__':
    import argparse
    arg_parser = argparse.ArgumentParser(
        description="Posts static analysis results to github.")
    arg_parser.add_argument(
        '--config-file',
        default="imhotep_config.json",
        type=str,
        help="Configuration file in json.")
    arg_parser.add_argument(
        '--repo_name', required=True,
        help="Github repository name in owner/repo format")
    arg_parser.add_argument(
        '--commit',
        help="The sha of the commit to run static analysis on.")
    arg_parser.add_argument(
        '--origin-commit',
        required=False,
        default='HEAD^',
        help='Commit to use as the comparison point.')
    arg_parser.add_argument(
        '--filenames', nargs="+",
        help="filenames you want static analysis to be limited to.")
    arg_parser.add_argument(
        '--debug',
        action='store_true',
        help="Will dump debugging output and won't clean up after itself.")
    arg_parser.add_argument(
        '--github-username',
        help='Github user to post comments as.')
    arg_parser.add_argument(
        '--github-password',
        help='Github password for the above user.')
    arg_parser.add_argument(
        '--no-post',
        action="store_true",
        help="[DEBUG] will print out comments rather than posting to github.")
    arg_parser.add_argument(
        '--authenticated',
        action="store_true",
        help="Indicates the repository requires authentication")
    arg_parser.add_argument(
        '--pr-number',
        help="Number of the pull request to comment on")
    arg_parser.add_argument(
        '--cache-directory',
        help="Path to directory to cache the repository",
        type=str,
        required=False)

    arg_parser.add_argument(
        '--linter',
        help="Path to linters to run, e.g. 'imhotep.tools:PyLint'",
        type=str,
        nargs="+",
        default=[],
        required=False)

    # parse out repo name
    args = arg_parser.parse_args()
    params = args.__dict__
    params.update(**load_config(args.config_file))

    try:
        imhotep = gen_imhotep(**params)
    except NoGithubCredentials:
        log.error("You must specify a GitHub username or password.")
        sys.exit(1)
    except NoCommitInfo:
        log.error("You must specify a commit or PR number")
        sys.exit(1)
    except UnknownTools as e:
        log.error("Didn't find any of the specified linters.")
        log.error("Known linters: %s", ', '.join(e.known))
        sys.exit(1)

    imhotep.invoke()
