import json
import logging
import os
import subprocess
import sys

import pkg_resources
from imhotep.reporters import get_reporter

from repositories import RepoManager
from diff_parser import DiffContextParser
from shas import get_pr_info, CommitInfo
from http import GithubRequester, NoGithubCredentials
from errors import UnknownTools, NoCommitInfo


log = logging.getLogger(__name__)


def run(cmd, cwd='.'):
    log.debug("Running: %s", cmd)
    return subprocess.Popen(
        [cmd], stdout=subprocess.PIPE, shell=True, cwd=cwd).communicate()[0]


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
    for ep in pkg_resources.iter_entry_points(group='imhotep_linters'):
        klass = ep.load()
        tools.append(klass(run))
    return tools


class Imhotep(object):
    def __init__(self, requester=None, repo_manager=None,
                 repo_name=None, pr_number=None,
                 commit_info=None, reporter=None,
                 commit=None, origin_commit=None, no_post=None, debug=None,
                 filenames=None, **kwargs):
        # TODO(justinabrahms): kwargs exist until we handle cli params better
        # TODO(justinabrahms): This is a sprawling API. Tighten it up.
        self.requester = requester
        self.manager = repo_manager
        self.reporter = reporter

        self.commit_info = commit_info
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.commit = commit
        self.origin_commit = origin_commit
        self.no_post = no_post
        self.debug = debug
        self.filenames = filenames

        if self.commit is None and self.pr_number is None:
            raise NoCommitInfo()

    def invoke(self):
        cinfo = self.commit_info

        try:
            diff_txt = self.manager.diff_commit(cinfo.commit,
                                                compare_point=cinfo.origin)
            errors = self.manager.run_tools(filenames=set(self.filenames or []))

            diff_objects = DiffContextParser(diff_txt).parse()
            self.report_errors(diff_objects, errors)
        finally:
            self.manager.cleanup()

    def report_errors(self, diff_objects, errors):
        error_count = 0
        for entry in diff_objects:
            pos_map = dict([(l.number, l.position) for l in entry.added_lines])
            added_lines = pos_map.keys()

            violations = errors.get(entry.result_filename, {})
            violating_lines = [int(l) for l in violations.keys()]

            matching_numbers = set(added_lines).intersection(
                violating_lines)
            for x in matching_numbers:
                error_count += 1
                self.reporter.report_line(
                    self.repo_name, self.commit_info.origin,
                    entry.result_filename,
                    x, pos_map[x], violations['%s' % x])

            log.info("%d violations.", error_count)


def gen_imhotep(**kwargs):
    req = GithubRequester(kwargs['github_username'],
                          kwargs['github_password'])

    plugins = load_plugins()
    tools = get_tools(kwargs['linter'], plugins)

    reporter = get_reporter(req, no_post=kwargs.get('no_post'),
                            pr_number=kwargs.get('pr_number'),
                            commit=kwargs.get('commit'))

    if kwargs['pr_number']:
        pr_info = get_pr_info(req, kwargs['repo_name'], kwargs['pr_number'])
        commit_info = pr_info.to_commit_info()
    else:
        # TODO(justinabrahms): origin & remote_repo doesnt work for commits
        commit_info = CommitInfo(kwargs['commit'], None, None)

    manager = RepoManager(authenticated=kwargs['authenticated'],
                          cache_directory=kwargs['cache_directory'],
                          tools=tools,
                          repo_name=kwargs['repo_name'],
                          remote_repo=commit_info.remote_repo,
                          executor=run)

    return Imhotep(requester=req, repo_manager=manager, reporter=reporter,
                   commit_info=commit_info, **kwargs)


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

    if params['debug']:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()

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
