import argparse
from collections import defaultdict
import glob
import logging
import subprocess

import pkg_resources

from imhotep.repomanagers import ShallowRepoManager, RepoManager
from .reporters.printing import PrintingReporter
from .reporters.github import CommitReporter, PRReporter
from .diff_parser import DiffContextParser
from .shas import get_pr_info, CommitInfo
from imhotep import http_client
from .errors import UnknownTools, NoCommitInfo


log = logging.getLogger(__name__)


def run(cmd, cwd='.'):
    log.debug("Running: %s", cmd)
    return subprocess.Popen(
        [cmd], stdout=subprocess.PIPE, shell=True, cwd=cwd).communicate()[0]


def find_config(dirname, config_filenames):
    configs = []
    for filename in config_filenames:
        configs += glob.glob('%s/%s' % (dirname, filename))
    return set(configs)


def run_analysis(repo, filenames=set(), linter_configs=set()):
    results = defaultdict(lambda: defaultdict(list))
    for tool in repo.tools:
        log.debug("running %s" % tool.__class__.__name__)
        configs = {}
        try:
            configs = tool.get_configs()
        except AttributeError:
            pass
        linter_configs = find_config(repo.dirname, configs)
        log.debug("Tool configs %s, found configs %s", configs, linter_configs)
        run_results = tool.invoke(repo.dirname,
                                  filenames=filenames,
                                  linter_configs=linter_configs)

        for fname, fresults in run_results.items():
            for lineno, violations in fresults.items():
                results[fname][lineno].extend(violations)

    return results


def load_plugins():
    tools = []
    for ep in pkg_resources.iter_entry_points(group='imhotep_linters'):
        klass = ep.load()
        tools.append(klass(run))
    return tools


class Imhotep(object):
    def __init__(self, requester=None, repo_manager=None,
                 repo_name=None, pr_number=None,
                 commit_info=None,
                 commit=None, origin_commit=None, no_post=None, debug=None,
                 filenames=None, shallow_clone=False, github_domain=None,
                 report_file_violations=False, **kwargs):
        # TODO(justinabrahms): kwargs exist until we handle cli params better
        # TODO(justinabrahms): This is a sprawling API. Tighten it up.
        self.requester = requester
        self.manager = repo_manager

        self.commit_info = commit_info
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.commit = commit
        self.origin_commit = origin_commit
        self.no_post = no_post
        self.debug = debug
        if filenames is None:
            filenames = []
        self.requested_filenames = set(filenames)
        self.shallow = shallow_clone
        self.github_domain = github_domain
        self.report_file_violations = report_file_violations

        if self.commit is None and self.pr_number is None:
            raise NoCommitInfo()

    def get_reporter(self):
        if self.no_post:
            return PrintingReporter()
        if self.pr_number:
            return PRReporter(self.requester, self.repo_name, self.pr_number)
        elif self.commit is not None:
            return CommitReporter(self.requester, self.repo_name)

    def get_filenames(self, entries, requested_set=None):
        filenames = set([x.result_filename for x in entries])
        if requested_set is not None and len(requested_set):
            filenames = requested_set.intersection(filenames)
        return list(filenames)

    def invoke(self, reporter=None, max_errors=float('inf')):
        cinfo = self.commit_info
        if not reporter:
            reporter = self.get_reporter()

        try:
            repo = self.manager.clone_repo(self.repo_name,
                                           remote_repo=cinfo.remote_repo,
                                           ref=cinfo.ref)
            diff = repo.diff_commit(cinfo.commit, compare_point=cinfo.origin)

            # Move out to its own thing
            parser = DiffContextParser(diff)
            parse_results = parser.parse()
            filenames = self.get_filenames(parse_results,
                                           self.requested_filenames)
            results = run_analysis(repo, filenames=filenames)

            error_count = 0
            for entry in parse_results:
                added_lines = [l.number for l in entry.added_lines]
                if not entry.added_lines:
                    continue
                pos_map = {0: min(l.position for l in entry.added_lines)}
                for x in entry.added_lines:
                    pos_map[x.number] = x.position

                if self.report_file_violations:
                    # "magic" value of line 0 represents file-level results.
                    added_lines.append(0)

                violations = results.get(entry.result_filename, {})
                violating_lines = [int(l) for l in violations.keys()]

                matching_numbers = set(added_lines).intersection(
                    violating_lines)
                for x in matching_numbers:
                    error_count += 1
                    if error_count > max_errors:
                        continue
                    reporter.report_line(
                        cinfo.origin, entry.result_filename,
                        x, pos_map[x], violations['%s' % x])

                if error_count > max_errors \
                   and hasattr(reporter, 'post_comment'):
                    reporter.post_comment(
                        "There were too many ({error_count}) linting errors to"
                        " continue.".format(error_count=error_count))
                log.info("%d violations.", error_count)
        finally:
            self.manager.cleanup()


def gen_imhotep(**kwargs):
    # TODO(justinabrahms): Interface should have a "are creds valid?" method
    req = http_client.BasicAuthRequester(kwargs['github_username'],
                                  kwargs['github_password'])

    plugins = load_plugins()
    tools = get_tools(kwargs['linter'], plugins)

    if kwargs['shallow']:
        Manager = ShallowRepoManager
    else:
        Manager = RepoManager

    domain = kwargs['github_domain']
    manager = Manager(authenticated=kwargs['authenticated'],
                      cache_directory=kwargs['cache_directory'],
                      tools=tools,
                      executor=run,
                      domain=domain)

    if kwargs['pr_number']:
        pr_info = get_pr_info(req, kwargs['repo_name'], kwargs['pr_number'], domain)
        commit_info = pr_info.to_commit_info()
    else:
        # TODO(justinabrahms): origin & remote_repo doesnt work for commits
        commit_info = CommitInfo(kwargs['commit'], None, None, None)

    log.debug('Shallow: %s', kwargs['shallow'])
    shallow_clone = kwargs['shallow'] or False

    return Imhotep(
        requester=req, repo_manager=manager, commit_info=commit_info,
        shallow_clone=shallow_clone, domain=domain, **kwargs)


def get_tools(whitelist, known_plugins):
    """
    Filter all known plugins by a whitelist specified. If the whitelist is
    empty, default to all plugins.
    """
    def getpath(c):
        return "%s:%s" % (c.__module__, c.__class__.__name__)

    tools = [x for x in known_plugins if getpath(x) in whitelist]

    if not tools:
        if whitelist:
            raise UnknownTools(map(getpath, known_plugins))
        tools = known_plugins
    return tools


def parse_args(args):
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
    arg_parser.add_argument(
        '--shallow',
        help="Performs a shallow clone of the repo",
        action="store_true")
    arg_parser.add_argument(
        '--github-domain',
        help="You can provide an alternative domain, if you\'re using github enterprise, for instance",
        default="github.com")
    arg_parser.add_argument(
        '--report-file-violations',
        help="Report file-level violations, i.e. those not on individual lines",
        action="store_true")
    # parse out repo name
    return arg_parser.parse_args(args)
