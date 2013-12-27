from imhotep.repositories import Repository, AuthenticatedRepository

def test_unauthed_download_location():
    uar = Repository('justinabrahms/imhotep', None, None)
    assert uar.download_location == "git://github.com/justinabrahms/imhotep.git"

def test_authed_download_location():
    ar = AuthenticatedRepository('justinabrahms/imhotep', None, None)
    assert ar.download_location == "git@github.com:justinabrahms/imhotep.git"
