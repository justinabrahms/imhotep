from imhotep.repositories import Repository, AuthenticatedRepository

repo_name = 'justinabrahms/imhotep'


def test_unauthed_download_location():
    uar = Repository(repo_name, None, None, None)
    loc = uar.download_location
    assert loc == "git://github.com/justinabrahms/imhotep.git"


def test_authed_download_location():
    ar = AuthenticatedRepository(repo_name, None, None, None)
    assert ar.download_location == "git@github.com:justinabrahms/imhotep.git"


def test_unicode():
    r = Repository(repo_name, None, None, None)
    assert r.__unicode__() == repo_name
