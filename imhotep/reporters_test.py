import mock

from imhotep.reporters import (CommitReporter, GitHubReporter,
                               PRReporter)
from imhotep.testing_utils import Requester


def test_commit_url():
    requester = Requester("")
    cr = CommitReporter(requester)
    cr.report_line(repo_name='foo/bar', commit='sha',
                   file_name='setup.py', line_number=10, position=0,
                   message="test")

    assert requester.url == \
           "https://api.github.com/repos/foo/bar/commits/sha/comments"


def test_pr_url():
    requester = Requester("")
    pr = PRReporter(requester, 10)
    pr.report_line(repo_name='justinabrahms/imhotep', commit='sha',
                   file_name='setup.py', line_number=10, position=0,
                   message="test")

    assert requester.url == \
           "https://api.github.com/repos/justinabrahms/imhotep/pulls/10/comments"


def test_pr_already_reported():
    requester = mock.MagicMock()
    requester.username = 'magicmock'
    comments = [{'path': 'foo.py',
                'position': 2,
                'body': 'Get that out',
                'user': {'login': 'magicmock'}}]
    pr = PRReporter(requester, 10)
    pr._comments = comments
    result = pr.report_line(repo_name='justinabrahms/imhotep', commit='sha',
                            file_name='foo.py', line_number=2, position=2,
                            message='Get that out')
    assert result is None


def test_get_comments_no_cache():
    return_data = {'foo': 'bar'}
    requester = mock.MagicMock()
    requester.get.return_value.json = return_data
    requester.get.return_value.status_code = 200
    pr = GitHubReporter()
    pr.requester = requester
    pr.report_url = 'example.com'
    result = pr.get_comments()
    assert result == return_data
    assert pr._comments == return_data
    requester.get.assert_called_with('example.com')


def test_get_comments_cache():
    return_data = {'foo': 'bar'}
    requester = mock.MagicMock()
    pr = GitHubReporter()
    pr._comments = return_data
    result = pr.get_comments()
    assert result == return_data
    assert not requester.get.called


def test_get_comments_error():
    requester = mock.MagicMock()
    requester.get.return_value.status_code = 400
    pr = GitHubReporter()
    pr.requester = requester
    pr.report_url = 'example.com'
    result = pr.get_comments()
    assert result is None


def test_clean_already_reported():
    requester = mock.MagicMock()
    requester.username = 'magicmock'
    pr = GitHubReporter()
    pr.requester = requester
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
