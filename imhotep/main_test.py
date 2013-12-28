from main import load_config, RepoManager
from repositories import Repository, AuthenticatedRepository
import mock


def test_config_loading():
    c = load_config('doesnt_exist')
    assert isinstance(c, dict)


def test_authencticated_repo():
    r = RepoManager(authenticated=True)
    assert AuthenticatedRepository == r.get_repo_class()


def test_unauthencticated_repo():
    r = RepoManager()
    assert Repository == r.get_repo_class()


def test_cleanup_calls_rm():
    m = mock.Mock()
    r = RepoManager(executor=m)
    r.to_cleanup = {'repo': '/tmp/a_dir'}
    r.cleanup()

    assert m.called_with('rm -rf /tmp/a_dir')


def test_cleanup_doesnt_call_rm_with_cache_dir():
    m = mock.Mock()
    r = RepoManager(executor=m)
    r.to_cleanup = {'repo': '/tmp/a_dir'}
    r.cleanup()

    assert not m.called


def test_clone_dir_nocache():
    r = RepoManager()
    val = r.clone_dir('justinabrahms/imhotep')
    assert '/tmp' in val


def test_clone_dir_cached():
    r = RepoManager(cache_directory="/weeble/wobble/")
    val = r.clone_dir('justinabrahms/imhotep')
    assert val.startswith('/weeble/wobble/justinabrahms__imhotep')
