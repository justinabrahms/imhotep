import mock
from imhotep.http import BasicAuthRequester


def test_auth():
    ghr = BasicAuthRequester('user', 'pass')
    auth = ghr.get_auth()
    assert auth.username == 'user'
    assert auth.password == 'pass'


def test_get():
    ghr = BasicAuthRequester('user', 'pass')
    with mock.patch('requests.get') as g:
        g.return_value.status_code = 200
        ghr.get('url')
        g.assert_called_with_args('url', auth=mock.ANY)


def test_delete():
    ghr = BasicAuthRequester('user', 'pass')
    with mock.patch('requests.delete') as g:
        ghr.delete('url')
        g.assert_called_with_args('url', auth=mock.ANY)


def test_post():
    ghr = BasicAuthRequester('user', 'pass')
    with mock.patch('requests.post') as g:
        g.return_value.status_code = 200
        ghr.post('url', {"a": 2})
        g.assert_called_with_args('url', data='{"a":2}', auth=mock.ANY)
