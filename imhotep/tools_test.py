import re

import mock
import pytest

from .tools import Tool
from .testing_utils import calls_matching_re


class ExampleTool(Tool):
    def process_line(self, dirname, line):
        return None

    def get_file_extensions(self):
        return [".exe"]

    def get_command(self, dirname, linter_configs=set()):
        return "example-cmd"


def test_tool_configs():
    m = mock.Mock()
    t = ExampleTool(m)
    assert len(t.get_configs()) == 0


def test_find_searches_dirname():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.invoke('/woobie/')

    assert len(calls_matching_re(
        m, re.compile(r'find /woobie/'))) > 0


def test_find_includes_extension():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.invoke('/woobie/')

    assert len(calls_matching_re(
        m, re.compile(r'-name "\*.exe"'))) > 0


def test_find_includes_multiple_extensions_with_dash_o():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.get_file_extensions = lambda: ['.a', '.b']
    t.invoke('/woobie/')

    assert len(calls_matching_re(
        m, re.compile(r'-name "\*.a" -o -name "\*.b"'))) > 0


def test_invoke_runs_command():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.invoke('/woobie/')

    assert len(calls_matching_re(
        m, re.compile("example-cmd"))) == 1


def test_calls_process_line_for_each_line():
    m = mock.Mock()
    m.return_value = "1\n2\n3"
    t = ExampleTool(m)
    process_mock = mock.Mock()
    process_mock.return_value = None
    t.process_line = process_mock
    t.invoke('/woobie/')

    assert process_mock.call_count == 3


def test_ignores_none_results_from_process_line():
    m = mock.Mock()
    m.return_value = ""
    process_mock = mock.Mock()
    process_mock.return_value = None
    t = ExampleTool(m)
    t.process_line = process_mock
    retval = t.invoke('/woobie/')

    assert 0 == len(retval.keys())


def test_appends_process_line_results_to_results():
    m = mock.Mock()
    m.return_value = ""
    process_mock = mock.Mock()
    process_mock.return_value = ('filename', 2, 3)
    t = ExampleTool(m)
    t.process_line = process_mock
    retval = t.invoke('/woobie/')

    assert 1 == len(retval.keys())
    assert retval['filename'][2][0] == 3


def test_invoke_removes_dirname_prefix():
    m = mock.Mock()
    m.return_value = ""
    process_mock = mock.Mock()
    process_mock.return_value = ('/my/full/path/and/extras', 2, 3)
    t = ExampleTool(m)
    t.process_line = process_mock
    retval = t.invoke('/my/full/path')

    assert 'and/extras' in retval.keys()


def test_process_line_no_response_format():
    t = Tool(command_executor='')
    with pytest.raises(NotImplementedError):
        t.process_line(dirname='/my/full/path', line='my line')


def test_invoke_finds_named_files():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.invoke('/woobie/', filenames=['foo.exe'])

    assert len(calls_matching_re(
        m, re.compile(r'-samefile "foo\.exe"'))) > 0

def test_invoke_bails_out_fast_if_no_filename_matches():
    m = mock.Mock()
    m.return_value = ""
    t = ExampleTool(m)
    t.invoke('/woobie/', filenames=['foo.py'])

    assert not m.called
