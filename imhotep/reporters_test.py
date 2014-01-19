from imhotep.reporters import CommitReporter, PRReporter
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
