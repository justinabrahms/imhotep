from collections import namedtuple

import mock

from app import (run_analysis, get_tools, UnknownTools, Imhotep, NoCommitInfo,
    run, load_plugins)
from imhotep.main import load_config
from reporters import PrintingReporter, CommitReporter, PRReporter
from repositories import Repository, ToolsNotFound
from diff_parser import Entry


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


def test_tools_invoked_on_repo():
    m = mock.MagicMock()
    m.invoke.return_value = {}
    repo = Repository('name', 'location', [m], None)
    run_analysis(repo)
    assert m.invoke.called


def test_tools_merges_tool_results():
    m = mock.MagicMock()
    m.invoke.return_value = {'a': 1}
    m2 = mock.MagicMock()
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

