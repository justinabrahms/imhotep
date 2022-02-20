import io
import mock

from imhotep.app import parse_args
from imhotep.errors import UnknownTools, NoCommitInfo
from imhotep.http_client import NoGithubCredentials
from imhotep.main import main, load_config


class MockParserRetval(object):
    def __init__(self):
        self.__dict__ = {
            'config_file': 'foo.json',
            'repo_name': 'repo_name',
            'commit': 'commit',
            'origin_commit': 'origin-commit',
            'filenames': [],
            'debug': True,
            'github_username': 'justinabrahms',
            'github_password': 'notachance',
            'authenticated': True,
            'pr_number': 1,
            'cache_directory': '/tmp',
            'linter': 'path.to:Linter',
        }


def test_repo_required():
    try:
        parse_args([])
        assert False, "Should raise an error if repo_name not provided"
    except (SystemExit,):
        pass


def test_main__sanity():
    with mock.patch('imhotep.app.gen_imhotep') as mock_gen:
        with mock.patch('imhotep.app.parse_args') as mock_parser:
            mock_parser.return_value = MockParserRetval()
            main()
            assert mock_gen.called


def test_main__returns_false_if_no_credentials():
    with mock.patch('imhotep.app.gen_imhotep') as mock_gen:
        with mock.patch('imhotep.app.parse_args') as mock_parser:
            mock_parser.return_value = MockParserRetval()
            mock_gen.side_effect = NoGithubCredentials()

            assert main() is False


def test_main__returns_false_if_no_commit_info():
    with mock.patch('imhotep.app.gen_imhotep') as mock_gen:
        with mock.patch('imhotep.app.parse_args') as mock_parser:
            mock_parser.return_value = MockParserRetval()
            mock_gen.side_effect = NoCommitInfo()

            assert main() is False


def test_main__returns_false_if_missing_tools():
    with mock.patch('imhotep.app.gen_imhotep') as mock_gen:
        with mock.patch('imhotep.app.parse_args') as mock_parser:
            mock_parser.return_value = MockParserRetval()
            mock_gen.side_effect = UnknownTools('tools')

            assert main() is False


def test_load_config__returns_json_content():
    with mock.patch('imhotep.main.open', create=True) as mock_open:
        mock_open.return_value = mock.MagicMock(spec=io.IOBase)

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.read.return_value = '{"valid": "json"}'

        cfg = load_config('filename')

        assert {'valid': 'json'} == cfg


def test_load_config__value_error_handled():
    with mock.patch('imhotep.main.open', create=True) as mock_open:
        mock_open.return_value = mock.MagicMock(spec=io.IOBase)

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.read.side_effect = ValueError()

        cfg = load_config('filename')

        assert {} == cfg
