import argparse
import glob
import logging
import subprocess
from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple, Type

import pkg_resources

from imhotep import http_client
from imhotep.diff_parser import Entry
from imhotep.http_client import BasicAuthRequester
from imhotep.repomanagers import RepoManager, ShallowRepoManager
from imhotep.repositories import Repository
from imhotep.shas import CommitInfo

from .diff_parser import DiffContextParser
from .errors import NoCommitInfo, UnknownTools
from .reporters.github import CommitReporter, PRReporter, Reporter
from .reporters.printing import PrintingReporter
from .shas import CommitInfo, get_pr_info

log = logging.getLogger(__name__)


def run(cmd: str, cwd: str = ".") -> bytes:
    log.debug("Running: %s", cmd)
    return subprocess.Popen(
        [cmd], stdout=subprocess.PIPE, shell=True, cwd=cwd
    ).communicate()[0]


def find_config(dirname: str, config_filenames: Set[str]) -> Set[str]:
    configs = []
    for filename in config_filenames:
        configs += glob.glob(f"{dirname}/{filename}")
    return set(configs)


def run_analysis(
    repo: Repository, filenames: List[str] = []
) -> DefaultDict[str, DefaultDict[str, List[str]]]:
    results: DefaultDict = defaultdict(lambda: defaultdict(list))
    for tool in repo.tools:
        log.debug("running %s" % tool.__class__.__name__)
        configs: Set[str] = set()
        try:
            configs = tool.get_configs()
        except AttributeError:
            pass
        configs_found: Set[str] = find_config(repo.dirname, configs)
        log.debug("Tool configs %s, found configs %s", configs, configs_found)
        run_results = tool.invoke(
            repo.dirname, filenames=filenames, linter_configs=configs_found
        )

        for fname, fresults in run_results.items():
            for lineno, violations in fresults.items():
                results[fname][lineno].extend(violations)

    return results


def load_plugins() -> List:
    tools = []
    for ep in pkg_resources.iter_entry_points(group="imhotep_linters"):
        klass = ep.load()
        tools.append(klass(run))
    return tools


class Imhotep:
    def __init__(
        self,
        requester: Optional[BasicAuthRequester] = None,
        repo_manager: Optional[RepoManager] = None,
        repo_name: Optional[str] = None,
        pr_number: Optional[str] = None,
        commit_info: Optional[CommitInfo] = None,
        commit: None = None,
        origin_commit: Optional[str] = None,
        no_post: Optional[bool] = None,
        debug: Optional[bool] = None,
        filenames: Optional[List[str]] = None,
        shallow_clone: bool = False,
        github_domain: Optional[str] = None,
        report_file_violations: bool = False,
        dir_override: Optional[str] = None,
        **kwargs,
    ) -> None:
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
        self.requested_filenames: set[str] = set(filenames)
        self.shallow = shallow_clone
        self.github_domain = github_domain
        self.report_file_violations = report_file_violations
        self.dir_override = dir_override

        if self.commit is None and self.pr_number is None:
            raise NoCommitInfo()

    def get_reporter(self) -> Reporter:
        if self.no_post:
            return PrintingReporter()
        if self.pr_number:
            if self.requester is None:
                log.error(
                    "PR number specified, but requester is missing. Default to printing reporter."
                )
                return PrintingReporter()
            if self.github_domain is None:
                log.error(
                    "PR number specified, but github_domain is missing. Default to printing reporter."
                )
                return PrintingReporter()
            if self.repo_name is None:
                log.error(
                    "PR number specified, but repo_name is missing. Default to printing reporter."
                )
                return PrintingReporter()
            return PRReporter(
                self.requester, self.github_domain, self.repo_name, self.pr_number
            )
        elif self.commit is not None:
            return CommitReporter(self.requester, self.github_domain, self.repo_name)
        log.warn("Default to printing reporter.")
        return PrintingReporter()

    def get_filenames(
        self, entries: List[Entry], requested_set: Optional[Set[Any]] = None
    ) -> List[str]:
        filenames = {x.result_filename for x in entries}
        if requested_set is not None and len(requested_set):
            filenames = requested_set.intersection(filenames)
        return list(filenames)

    def invoke(
        self, reporter: Optional[Reporter] = None, max_errors: float = float("inf")
    ) -> None:
        cinfo = self.commit_info
        if not reporter:
            reporter = self.get_reporter()

        if self.manager is None:
            log.error("Repo manager is missing.")
            return

        if self.repo_name is None:
            log.error("Repo name is missing.")
            return
        if cinfo is None:
            log.error("Commit info is missing.")
            return

        try:
            repo = self.manager.clone_repo(
                self.repo_name,
                remote_repo=cinfo.remote_repo,
                ref=cinfo.ref,
                dir_override=self.dir_override,
            )
            diff = repo.diff_commit(cinfo.commit, compare_point=cinfo.origin)

            # Move out to its own thing
            parser = DiffContextParser(diff)
            parse_results = parser.parse()
            filenames = self.get_filenames(parse_results, self.requested_filenames)
            results = run_analysis(repo, filenames=filenames)

            error_count = 0
            for entry in parse_results:
                added_lines: List[int] = [l.number for l in entry.added_lines]
                if not entry.added_lines:
                    continue
                pos_map: Dict[int, int] = {
                    0: min(l.position for l in entry.added_lines)
                }
                for x in entry.added_lines:
                    pos_map[x.number] = x.position

                if self.report_file_violations:
                    # "magic" value of line 0 represents file-level results.
                    added_lines.append(0)

                violations: Dict[str, List[str]] = results.get(
                    entry.result_filename, {}
                )
                violating_lines: List[int] = [int(l) for l in violations.keys()]

                matching_numbers = set(added_lines).intersection(violating_lines)
                for i in matching_numbers:
                    error_count += 1
                    if error_count > max_errors:
                        continue
                    reporter.report_line(
                        cinfo.origin,
                        entry.result_filename,
                        x,
                        pos_map[i],
                        violations[f"{i}"],
                    )
                if error_count > max_errors and hasattr(reporter, "post_comment"):
                    reporter.post_comment(  # type: ignore
                        "There were too many ({error_count}) linting errors to"
                        " continue.".format(error_count=error_count)
                    )
                log.info("%d violations.", error_count)
        finally:
            self.manager.cleanup()


def gen_imhotep(**kwargs) -> Imhotep:
    # TODO(justinabrahms): Interface should have a "are creds valid?" method
    req = http_client.BasicAuthRequester(
        kwargs["github_username"], kwargs["github_password"]
    )

    plugins = load_plugins()
    tools = get_tools(kwargs["linter"], plugins)

    Manager: Optional[Type[RepoManager]] = None
    if kwargs["shallow"]:
        Manager = ShallowRepoManager
    else:
        Manager = RepoManager
    assert Manager is not None
    domain = kwargs["github_domain"]
    manager = Manager(
        authenticated=kwargs["authenticated"],
        cache_directory=kwargs["cache_directory"],
        tools=tools,
        executor=run,
        domain=domain,
    )

    if kwargs["pr_number"]:
        pr_info = get_pr_info(req, kwargs["repo_name"], kwargs["pr_number"], domain)
        commit_info = pr_info.to_commit_info()
    else:
        # TODO(justinabrahms): origin & remote_repo doesnt work for commits
        commit_info = CommitInfo(kwargs["commit"], None, None, None)

    log.debug("Shallow: %s", kwargs["shallow"])
    shallow_clone = kwargs["shallow"] or False

    return Imhotep(
        requester=req,
        repo_manager=manager,
        commit_info=commit_info,
        shallow_clone=shallow_clone,
        domain=domain,
        **kwargs,
    )


def get_tools(whitelist: List[str], known_plugins: List) -> List:
    """
    Filter all known plugins by a whitelist specified. If the whitelist is
    empty, default to all plugins.
    """

    def getpath(c):
        return f"{c.__module__}:{c.__class__.__name__}"

    tools = [x for x in known_plugins if getpath(x) in whitelist]

    if not tools:
        if whitelist:
            raise UnknownTools(map(getpath, known_plugins))
        tools = known_plugins
    return tools


def parse_args(args: List[str]) -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(
        description="Posts static analysis results to github."
    )
    arg_parser.add_argument(
        "--config-file",
        default="imhotep_config.json",
        type=str,
        help="Configuration file in json.",
    )
    arg_parser.add_argument(
        "--repo_name", required=True, help="Github repository name in owner/repo format"
    )
    arg_parser.add_argument(
        "--commit", help="The sha of the commit to run static analysis on."
    )
    arg_parser.add_argument(
        "--origin-commit",
        required=False,
        default="HEAD^",
        help="Commit to use as the comparison point.",
    )
    arg_parser.add_argument(
        "--filenames",
        nargs="+",
        help="filenames you want static analysis to be limited to.",
    )
    arg_parser.add_argument(
        "--debug",
        action="store_true",
        help="Will dump debugging output and won't clean up after itself.",
    )
    arg_parser.add_argument(
        "--github-username", help="Github user to post comments as."
    )
    arg_parser.add_argument(
        "--github-password", help="Github password for the above user."
    )
    arg_parser.add_argument(
        "--no-post",
        action="store_true",
        help="[DEBUG] will print out comments rather than posting to github.",
    )
    arg_parser.add_argument(
        "--authenticated",
        action="store_true",
        help="Indicates the repository requires authentication",
    )
    arg_parser.add_argument(
        "--pr-number", help="Number of the pull request to comment on"
    )
    arg_parser.add_argument(
        "--cache-directory",
        help="Path to directory to cache the repository",
        type=str,
        required=False,
    )
    arg_parser.add_argument(
        "--linter",
        help="Path to linters to run, e.g. 'imhotep.tools:PyLint'",
        type=str,
        nargs="+",
        default=[],
        required=False,
    )
    arg_parser.add_argument(
        "--shallow", help="Performs a shallow clone of the repo", action="store_true"
    )
    arg_parser.add_argument(
        "--github-domain",
        help="You can provide an alternative domain, if you're using github enterprise, for instance",
        default="github.com",
    )
    arg_parser.add_argument(
        "--report-file-violations",
        help="Report file-level violations, i.e. those not on individual lines",
        action="store_true",
    )
    arg_parser.add_argument(
        "--dir-override",
        help="Override the full path to the local repository.",
    )
    # parse out repo name
    return arg_parser.parse_args(args)
