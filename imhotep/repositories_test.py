import mock
from imhotep.repositories import Repository, AuthenticatedRepository

repo_name = 'justinabrahms/imhotep'


def test_unauthed_download_location():
    uar = Repository(repo_name, None, [None], None)
    loc = uar.download_location
    assert loc == "https://github.com/justinabrahms/imhotep.git"


def test_authed_download_location():
    ar = AuthenticatedRepository(repo_name, None, [None], None)
    assert ar.download_location == "git@github.com:justinabrahms/imhotep.git"


def test_unicode():
    r = Repository(repo_name, None, [None], None)
    assert r.__unicode__() == repo_name


def test_diff_commit():
    executor = mock.Mock()
    uar = Repository(repo_name, '/loc/', [None], executor)
    uar.diff_commit('commit-to-diff')
    executor.assert_called_with("cd /loc/ && git diff commit-to-diff")


def test_diff_commit__compare_point_applied():
    executor = mock.Mock()
    uar = Repository(repo_name, '/loc/', [None], executor)
    uar.diff_commit('commit-to-diff', compare_point='base')
    executor.assert_any_call("cd /loc/ && git checkout base")


def test_apply_commit():
    executor = mock.Mock()
    uar = Repository(repo_name, '/loc/', [None], executor)
    uar.apply_commit('base')
    executor.assert_called_with("cd /loc/ && git checkout base")
