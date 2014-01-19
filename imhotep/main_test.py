from collections import namedtuple
import re

import mock

from main import (load_config, RepoManager, run_analysis,get_tools,
                  UnknownTools, Imhotep, NoCommitInfo, run, load_plugins)
from reporters import PrintingReporter, CommitReporter, PRReporter
from repositories import Repository, AuthenticatedRepository, ToolsNotFound
from shas import Remote
from testing_utils import calls_matching_re

repo_name = 'justinabrahms/imhotep'


def test_run():
    with mock.patch("subprocess.Popen") as popen:
        run('test')
        popen.assert_called_with(
            ['test'], cwd='.', stdout=mock.ANY, shell=True)


def test_run_known_cwd():
    with mock.patch("subprocess.Popen") as popen:
        run('test', cwd="/known")
        popen.assert_called_with(
            ['test'], cwd='/known', stdout=mock.ANY, shell=True)


def test_config_loading():
    c = load_config('doesnt_exist')
    assert isinstance(c, dict)


def test_authencticated_repo():
    r = RepoManager(authenticated=True, tools=[None])
    assert AuthenticatedRepository == r.get_repo_class()


def test_unauthencticated_repo():
    r = RepoManager(tools=[None])
    assert Repository == r.get_repo_class()


def test_cleanup_calls_rm():
    m = mock.Mock()
    r = RepoManager(executor=m, tools=[None])
    r.to_cleanup = {'repo': '/tmp/a_dir'}
    r.cleanup()

    assert m.called_with('rm -rf /tmp/a_dir')


def test_cleanup_doesnt_call_without_clean_files():
    m = mock.Mock()
    r = RepoManager(executor=m, tools=[None])
    r.cleanup()

    assert not m.called


def test_clone_dir_nocache():
    # TODO(justinabrahms): this test has side effects which generate temp
    # dirs. Need to fix that.
    r = RepoManager(tools=[None])
    val = r.clone_dir(repo_name)
    assert '/tmp' in val


def test_clone_dir_cached():
    r = RepoManager(cache_directory="/weeble/wobble/", tools=[None])
    val = r.clone_dir(repo_name)
    assert val.startswith('/weeble/wobble/justinabrahms__imhotep')


def test_clone_adds_to_cleanup_dict():
    m = mock.Mock()
    r = RepoManager(cache_directory="/weeble/wobble/", executor=m,
                    tools=[None])
    r.clone_repo(repo_name, None)
    directory = r.clone_dir(repo_name)
    assert directory in r.to_cleanup[repo_name]


def test_updates_if_existing_repo():
    finder = re.compile(r'git clone')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])

    with mock.patch('os.path.isdir') as isdir:
        isdir.return_value = True
        r.clone_repo(repo_name, None)

    assert len(calls_matching_re(m, finder)) == 0, "Shouldn't git clone"


def test_clones_if_no_existing_repo():
    finder = re.compile(r'git clone')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])
    r.clone_repo(repo_name, None)

    assert len(calls_matching_re(m, finder)) == 1, "Didn't git clone"


def test_adds_remote_if_pr_is_remote():
    finder = re.compile(r'git remote add name url')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])
    r.clone_repo(repo_name, Remote("name", "url"))

    assert len(calls_matching_re(m, finder)) == 1, "Remote not added"


def test_pulls_remote_changes_if_remote():
    finder = re.compile(r'git pull --all')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])
    r.clone_repo(repo_name, Remote("name", "url"))

    assert len(calls_matching_re(m, finder)) == 1, "Didn't pull updates"


def test_tools_invoked_on_repo():
    m = mock.Mock()
    m.invoke.return_value = {}
    repo = Repository('name', 'location', [m], None)
    run_analysis(repo)
    assert m.invoke.called


def test_tools_merges_tool_results():
    m = mock.Mock()
    m.invoke.return_value = {'a': 1}
    m2 = mock.Mock()
    m2.invoke.return_value = {'b': 2}
    repo = Repository('name', 'location', [m, m2], None)
    retval = run_analysis(repo)

    assert 'a' in retval
    assert 'b' in retval


def test_tools_errors_on_no_tools():
    try:
        Repository('name', 'location', [], None)
        assert False, "Should error if no tools are given"
    except ToolsNotFound:
        pass


def test_imhotep_instantiation__error_without_commit_info():
    try:
        Imhotep()
        assert False, "Expected a NoCommitInfo exception."
    except NoCommitInfo:
        pass


def test_reporter__printing():
    i = Imhotep(no_post=True, commit="asdf")
    assert type(i.get_reporter()) == PrintingReporter


def test_reporter__pr():
    i = Imhotep(pr_number=1)
    assert type(i.get_reporter()) == PRReporter


def test_reporter__commit():
    i = Imhotep(commit='asdf')
    assert type(i.get_reporter()) == CommitReporter


class Thing1(object):
    pass


class Thing2(object):
    pass


def test_plugin_filtering_throws_if_unfound():
    try:
        get_tools('unknown', [Thing1()])
        assert False, "Should have thrown an UnknownTools exception"
    except UnknownTools:
        pass

def test_plugin_filtering_defaults_to_all():
    plugins = [Thing1(), Thing2()]
    assert plugins == get_tools([], plugins)

def test_plugin_filtering_returns_subset_if_found():
    t1 = Thing1()
    plugins = [t1, Thing2()]
    assert [t1] == get_tools(['imhotep.main_test:Thing1'], plugins)


test_tool = namedtuple('TestTool', ('executor'),)


class EP(object):
    def load(self):
        return test_tool


def test_load_plugins():
    with mock.patch('pkg_resources.iter_entry_points') as ep:
        ep.return_value = [EP(), EP()]
        plugins = load_plugins()
        assert not isinstance(plugins[0], EP)
        assert 2 == len(plugins)
