import re

import mock

from main import load_config, RepoManager
from repositories import Repository, AuthenticatedRepository
from pull_requests import Remote

repo_name = 'justinabrahms/imhotep'

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


def test_cleanup_doesnt_call_without_clean_files():
    m = mock.Mock()
    r = RepoManager(executor=m)
    r.cleanup()

    assert not m.called


def test_clone_dir_nocache():
    # TODO(justinabrahms): this test has side effects which generate temp
    # dirs. Need to fix that.
    r = RepoManager()
    val = r.clone_dir(repo_name)
    assert '/tmp' in val


def test_clone_dir_cached():
    r = RepoManager(cache_directory="/weeble/wobble/")
    val = r.clone_dir(repo_name)
    assert val.startswith('/weeble/wobble/justinabrahms__imhotep')


def test_clone_adds_to_cleanup_dict():
    m = mock.Mock()
    r = RepoManager(cache_directory="/weeble/wobble/", executor=m)
    r.clone_repo(repo_name, None)
    directory = r.clone_dir(repo_name)
    assert directory in r.to_cleanup[repo_name]


def test_updates_if_existing_repo():
    finder = re.compile(r'git clone')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m)

    with mock.patch('os.path.isdir') as isdir:
        isdir.return_value = True
        r.clone_repo(repo_name, None)

    assert len(calls_matching_re(m, finder)) == 0, "Shouldn't git clone"


def calls_matching_re(mockObj, regex):
    matches = []
    for call in mockObj.call_args_list:
        cmd = call[0][0]
        match = regex.search(cmd)
        if match:
            matches.append(call)

    return matches


def test_clones_if_no_existing_repo():
    finder = re.compile(r'git clone')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m)
    r.clone_repo(repo_name, None)

    assert len(calls_matching_re(m, finder)) == 1, "Didn't git clone"


def test_adds_remote_if_pr_is_remote():
    finder = re.compile(r'git remote add name url')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m)
    r.clone_repo(repo_name, Remote("name", "url"))

    assert len(calls_matching_re(m, finder)) == 1, "Remote not added"


def test_pulls_remote_changes_if_remote():
    finder = re.compile(r'git pull --all')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m)
    r.clone_repo(repo_name, Remote("name", "url"))

    assert len(calls_matching_re(m, finder)) == 1, "Didn't pull updates"
