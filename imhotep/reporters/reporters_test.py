import mock

from imhotep.reporters.github import CommitReporter, GitHubReporter, PRReporter
from imhotep.reporters.printing import PrintingReporter
from imhotep.testing_utils import Requester


def test_commit_url():
    requester = Requester("")
    cr = CommitReporter(requester, 'foo/bar')
    cr.report_line(commit='sha', file_name='setup.py', line_number=10,
                   position=0, message="test")

    assert requester.url == "https://api.github.com/repos/foo/bar/commits/sha/comments"


def test_pr_url():
    requester = Requester("")
    pr = PRReporter(requester, 'justinabrahms/imhotep', 10)
    pr.report_line(commit='sha', file_name='setup.py', line_number=10,
                   position=0, message="test")

    assert requester.url == "https://api.github.com/repos/justinabrahms/imhotep/pulls/10/comments"


def test_pr_already_reported():
    requester = mock.MagicMock()
    requester.username = 'magicmock'
    comments = [{
        'path': 'foo.py',
        'position': 2,
        'body': 'Get that out',
        'user': {
            'login': 'magicmock'
        }
    }]

    pr = PRReporter(requester, 'justinabrahms/imhotep', 10)
    pr._comments = comments
    result = pr.report_line(commit='sha', file_name='foo.py', line_number=2,
                            position=2, message='Get that out')
    assert result is None


def test_get_comments_no_cache():
    return_data = {'foo': 'bar'}
    requester = mock.MagicMock()
    requester.get.return_value.json = lambda: return_data
    requester.get.return_value.status_code = 200
    pr = GitHubReporter(requester, 'repo-name')
    result = pr.get_comments('example.com')
    assert result == return_data
    assert pr._comments == return_data
    requester.get.assert_called_with('example.com')


def test_get_comments_cache():
    return_data = {'foo': 'bar'}
    requester = mock.MagicMock()
    pr = GitHubReporter(requester, 'test-repo')
    pr._comments = return_data
    result = pr.get_comments('example.com')
    assert result == return_data
    assert not requester.get.called


def test_get_comments_error():
    requester = mock.MagicMock()
    requester.get.return_value.status_code = 400
    pr = GitHubReporter(requester, 'test-repo')
    result = pr.get_comments('example.com')
    assert len(result) == 0


def test_clean_already_reported():
    requester = mock.MagicMock()
    requester.username = 'magicmock'
    pr = GitHubReporter(requester, 'test-repo')
    comments = [{'path': 'foo.py',
                 'position': 2,
                 'body': 'Get that out',
                 'user': {'login': 'magicmock'}},
                {'path': 'foo.py',
                 'position': 2,
                 'body': 'Different comment',
                 'user': {'login': 'magicmock'}}]
    message = ['Get that out', 'New message']
    result = pr.clean_already_reported(comments, 'foo.py',
                                       2, message)
    assert result == ['New message']


def test_convert_message_to_string():
    message = ['foo', 'bar']
    requester = mock.MagicMock()
    requester.username = 'magicmock'
    pr = GitHubReporter(requester, 'test-repo')
    result = pr.convert_message_to_string(message)
    assert result == '* foo\n* bar\n'


def test_pr__post_comment():
    requester = mock.MagicMock()
    requester.username = 'magicmock'
    requester.post.return_value.status_code = 200
    pr = PRReporter(requester, 'justinabrahms/imhotep', 10)
    pr.post_comment("my-message")

    assert requester.post.called


def test_printing_reporter_report_line():
    # smoke test to make sure the string interpolation doesn't explode
    PrintingReporter().report_line(
        commit='commit',
        file_name='file.py',
        line_number=123,
        position=1,
        message='message'
    )
