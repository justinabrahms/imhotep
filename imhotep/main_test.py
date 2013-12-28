from main import load_config, RepoManager
from repositories import Repository, AuthenticatedRepository


def test_config_loading():
    c = load_config('doesnt_exist')
    assert isinstance(c, dict)


def test_authencticated_repo():
    r = RepoManager(authenticated=True)
    assert AuthenticatedRepository == r.get_repo_class()


def test_unauthencticated_repo():
    r = RepoManager()
    assert Repository == r.get_repo_class()
