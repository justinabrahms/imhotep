from imhotep.reporters import CommitReporter, PRReporter, get_reporter, \
    PrintingReporter
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


def test_reporter__printing():
    r = get_reporter(None, no_post=True, commit="asdf")
    assert type(r) == PrintingReporter


def test_reporter__pr():
    r = get_reporter(None, pr_number=1)
    assert type(r) == PRReporter


def test_reporter__commit():
    r = get_reporter(None, commit='asdf')
    assert type(r) == CommitReporter