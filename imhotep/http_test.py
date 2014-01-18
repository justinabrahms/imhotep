import mock
from imhotep.http import GithubRequester


def test_auth():
    ghr = GithubRequester('user', 'pass')
    auth = ghr.get_auth()
    assert auth.username == 'user'
    assert auth.password == 'pass'


def test_get():
    ghr = GithubRequester('user', 'pass')
    with mock.patch('requests.get') as g:
        ghr.get('url')
        g.assert_called_with_args('url', auth=mock.ANY)


def test_delete():
    ghr = GithubRequester('user', 'pass')
    with mock.patch('requests.delete') as g:
        ghr.delete('url')
        g.assert_called_with_args('url', auth=mock.ANY)


def test_post():
    ghr = GithubRequester('user', 'pass')
    with mock.patch('requests.post') as g:
        ghr.post('url', {"a": 2})
        g.assert_called_with_args('url', data='{"a":2}', auth=mock.ANY)