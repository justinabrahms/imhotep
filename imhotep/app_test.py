from collections import namedtuple
import json

import mock

from .app import (run_analysis, get_tools, UnknownTools, Imhotep, NoCommitInfo,
                  run, load_plugins, gen_imhotep, find_config)
from imhotep.main import load_config
from imhotep.testing_utils import fixture_path
from .reporters.printing import PrintingReporter
from .reporters.github import CommitReporter, PRReporter
from .repositories import Repository, ToolsNotFound
from .repomanagers import RepoManager
from .tools import Tool
from .diff_parser import Entry


repo_name = 'justinabrahms/imhotep'

with open(fixture_path('remote_pr.json')) as f:
    remote_json_fixture = json.loads(f.read())


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


def test_tools_invoked_on_repo():
    m = mock.MagicMock()
    m.invoke.return_value = {}
    repo = Repository('name', 'location', [m], None)
    run_analysis(repo)
    assert m.invoke.called


def test_run_analysis__config_fetch_error_handled():
    mock_tool = mock.Mock()
    mock_tool.get_configs.side_effect = AttributeError()
    mock_tool.invoke.return_value = {}

    repo = Repository('name', 'loc', [mock_tool], None)

    assert {} == run_analysis(repo)


def test_tools_merges_tool_results():
    m = mock.MagicMock()
    m.invoke.return_value = {'a': {'4': ['a violation']}}
    m2 = mock.MagicMock()
    m2.invoke.return_value = {'b': {'32': ['another violation']}}
    repo = Repository('name', 'location', [m, m2], None)
    retval = run_analysis(repo)

    assert 'a' in retval
    assert 'b' in retval


def test_tools_merges_results_without_overwriting():
    m = mock.MagicMock()
    m.invoke.return_value = {'a': {'b': [1]}}
    m2 = mock.MagicMock()
    m2.invoke.return_value = {'a': {'b': [2]}}
    repo = Repository('name', 'location', [m, m2], None)
    retval = run_analysis(repo)

    assert 1 in retval['a']['b']
    assert 2 in retval['a']['b']


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
    assert [t1] == get_tools(['imhotep.app_test:Thing1'], plugins)


test_tool = namedtuple('TestTool', ('executor'), )


class EP(object):
    def load(self):
        return test_tool


def test_load_plugins():
    with mock.patch('pkg_resources.iter_entry_points') as ep:
        ep.return_value = [EP(), EP()]
        plugins = load_plugins()
        assert not isinstance(plugins[0], EP)
        assert 2 == len(plugins)


def test_imhotep_get_filenames():
    e1 = Entry('a.txt', 'a.txt')
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([e1])
    assert filenames == ['a.txt']


def test_imhotep_get_filenames_empty():
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([])
    assert filenames == []


def test_imhotep_get_filenames_requested():
    e1 = Entry('a.txt', 'a.txt')
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([e1], set(['a.txt']))
    assert filenames == ['a.txt']


def test_imhotep_get_filenames_requested_non_existent():
    e1 = Entry('a.txt', 'a.txt')
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([e1], set(['non-existent.txt']))
    assert filenames == []


def test_imhotep_get_filenames_requested_destination():
    e1 = Entry('a.txt', 'b.txt')
    i = Imhotep(pr_number=1)
    filenames = i.get_filenames([e1], set(['b.txt']))
    assert filenames == ['b.txt']


def gen_imhotep_dict():
    return {
        'github_username': 'username',
        'github_password': 'password',
        'linter': '',
        'shallow': False,
        'authenticated': False,
        'cache_directory': '/tmp',
        'pr_number': None,
        'github_domain': 'github.com',
    }


def test_gen_imhotep__returns_instance():
    kwargs = gen_imhotep_dict()
    kwargs['commit'] = 'abcdef0'
    retval = gen_imhotep(**kwargs)
    assert isinstance(retval, Imhotep)


def test_gen_imhotep__shallow_pr():
    kwargs = gen_imhotep_dict()
    kwargs['pr_number'] = 10
    kwargs['shallow'] = True
    kwargs['repo_name'] = 'user/repo'

    with mock.patch('imhotep.http_client.BasicAuthRequester') as mock_gh_req:
        mock_gh_req.return_value.get.return_value.json.return_value = remote_json_fixture
        retval = gen_imhotep(**kwargs)
    assert isinstance(retval, Imhotep)


def test_find_config__glob_no_results():
    with mock.patch('glob.glob') as mock_glob:
        mock_glob.return_value = []
        retval = find_config('dirname', ['configs'])
    assert set() == retval


def test_find_config__glob_multi_results():
    returns = [['setup.py', 'foo.py'], ['bar.py']]
    with mock.patch('glob.glob') as mock_glob:
        mock_glob.side_effect = lambda x: returns.pop(0)
        retval = find_config('dirname', ['configs', 'others'])

    assert retval == set(['setup.py', 'foo.py', 'bar.py'])


def test_find_config__prefix_dirname():
    with mock.patch('glob.glob') as mock_glob:
        mock_glob.return_value = []

        find_config('dirname', ['config'])

        mock_glob.assert_called_once_with('dirname/config')


def test_find_config__called_with_each_config_file():
    with mock.patch('glob.glob') as mock_glob:
        mock_glob.return_value = []

        find_config('dirname', ['config', 'another'])

        mock_glob.assert_has_calls([mock.call.glob('dirname/config'),
                                    mock.call.glob('dirname/another')])


def test_invoke__reports_errors():
    with open('imhotep/fixtures/two-block.diff') as f:
        two_block = bytes(f.read(), 'utf-8')
    reporter = mock.create_autospec(PRReporter)
    manager = mock.create_autospec(RepoManager)
    tool = mock.create_autospec(Tool)
    tool.get_configs.side_effect = AttributeError
    tool.invoke.return_value = {
        'imhotep/diff_parser_test.py': {
            '13': 'there was an error'
        }
    }
    manager.clone_repo.return_value.diff_commit.return_value = two_block
    manager.clone_repo.return_value.tools = [tool]
    imhotep = Imhotep(
        pr_number=1,
        repo_manager=manager,
        commit_info=mock.Mock(),
    )
    imhotep.invoke(reporter=reporter)

    assert reporter.report_line.called
    assert not reporter.post_comment.called


def test_invoke__skips_empty_files():
    with open('imhotep/fixtures/deleted_file.diff') as f:
        deleted_file = bytes(f.read(), 'utf-8')
    reporter = mock.create_autospec(PRReporter)
    manager = mock.create_autospec(RepoManager)
    tool = mock.create_autospec(Tool)
    tool.get_configs.side_effect = AttributeError
    tool.invoke.return_value = {
        'imhotep/diff_parser_test.py': {
            '13': 'there was an error'
        }
    }
    manager.clone_repo.return_value.diff_commit.return_value = deleted_file
    manager.clone_repo.return_value.tools = [tool]
    imhotep = Imhotep(
        pr_number=1,
        repo_manager=manager,
        commit_info=mock.Mock(),
    )
    imhotep.invoke(reporter=reporter)

    assert not reporter.report_line.called


def test_invoke__triggers_max_errors():
    with open('imhotep/fixtures/10line.diff') as f:
        ten_diff = bytes(f.read(), 'utf-8')
    reporter = mock.create_autospec(PRReporter)
    tool = mock.create_autospec(Tool)
    manager = mock.create_autospec(RepoManager)
    tool.get_configs.side_effect = AttributeError
    tool.invoke.return_value = {
        'f1.txt': {
            '1': 'there was an error',
            '2': 'there was an error',
            '3': 'there was an error',
            '4': 'there was an error',
            '5': 'there was an error',
            '6': 'there was an error',
            '7': 'there was an error',
            '8': 'there was an error',
            '9': 'there was an error',
        }
    }
    manager.clone_repo.return_value.diff_commit.return_value = ten_diff
    manager.clone_repo.return_value.tools = [tool]
    imhotep = Imhotep(
        pr_number=1,
        repo_manager=manager,
        commit_info=mock.Mock(),
    )
    imhotep.invoke(reporter=reporter, max_errors=2)

    assert reporter.report_line.call_count == 2
    assert reporter.post_comment.called


def test_invoke__reports_file_errors():
    with open('imhotep/fixtures/two-block.diff') as f:
        two_block = bytes(f.read(), 'utf-8')
    reporter = mock.create_autospec(PRReporter)
    manager = mock.create_autospec(RepoManager)
    tool = mock.create_autospec(Tool)
    tool.get_configs.side_effect = AttributeError
    tool.invoke.return_value = {
        'imhotep/diff_parser_test.py': {
            '0': 'imports are not sorted in this file'
        }
    }
    manager.clone_repo.return_value.diff_commit.return_value = two_block
    manager.clone_repo.return_value.tools = [tool]
    imhotep = Imhotep(
        pr_number=1,
        repo_manager=manager,
        commit_info=mock.Mock(),
        report_file_violations=True,
    )
    imhotep.invoke(reporter=reporter)

    assert reporter.report_line.called
    assert not reporter.post_comment.called

    # Reset mock and ensure that the default case is no file-level violations.
    reporter.reset_mock()

    imhotep = Imhotep(
        pr_number=1,
        repo_manager=manager,
        commit_info=mock.Mock(),
        # report_file_violations is False by default
    )
    imhotep.invoke(reporter=reporter)

    assert not reporter.report_line.called
    assert not reporter.post_comment.called
