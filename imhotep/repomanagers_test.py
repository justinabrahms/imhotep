import mock
import re
from imhotep.app import find_config

from .testing_utils import calls_matching_re

from .shas import Remote
from .repomanagers import RepoManager, ShallowRepoManager
from .repositories import Repository, AuthenticatedRepository

repo_name = 'justinabrahms/imhotep'


def test_authencticated_repo():
    r = RepoManager(authenticated=True, tools=[None])
    assert AuthenticatedRepository == r.get_repo_class()


def test_unauthencticated_repo():
    r = RepoManager(tools=[None])
    assert Repository == r.get_repo_class()


def test_cleanup_calls_rm():
    m = mock.Mock()
    r = RepoManager(executor=m, tools=[None])
    r.to_cleanup = {'repo': '/tmp/a_dir'}
    r.cleanup()

    assert m.called_with('rm -rf /tmp/a_dir')


def test_cleanup_doesnt_call_without_clean_files():
    m = mock.Mock()
    r = RepoManager(executor=m, tools=[None], cache_directory=[])

    r.cleanup()
    assert not m.called


def test_fetch():
    m = mock.Mock()
    r = RepoManager(executor=m, tools=[None])
    r.fetch('/tmp/a_dir', 'foo', 'newbranch')
    assert m.called_with('cd /tmp/a_dir && git fetch --depth=1 foo')


def test_shallow_clone():
    m = mock.Mock()
    r = ShallowRepoManager(executor=m, tools=[None])
    repo = Repository(repo_name, '/tmp/a_dir', [None], m, shallow=True)
    r.clone_repo(repo_name, Remote("name", "url"), 'foo')

    assert m.called_with('cd /tmp/a_dir && git init')
    assert m.called_with('cd /tmp/a_dir && git remote add name url')


def test_shallow_clone_call():
    m = mock.Mock()
    r = RepoManager(cache_directory="/weeble/wobble/",
                    executor=m,
                    tools=[None],
                    shallow_clone=True)
    r.clone_repo(repo_name, None, 'foo')
    assert m.called_with('cd /weeble/wobble/justinabrahms__imhotep && git init')


def test_clone_dir_nocache():
    # TODO(justinabrahms): this test has side effects which generate temp
    # dirs. Need to fix that.
    r = RepoManager(tools=[None])
    val = r.clone_dir(repo_name)
    assert '/tmp' in val


def test_clone_dir_cached():
    r = RepoManager(cache_directory="/weeble/wobble/", tools=[None])
    val = r.clone_dir(repo_name)
    assert val.startswith('/weeble/wobble/justinabrahms__imhotep')


def test_find_config():
    r = RepoManager(cache_directory="/weeble/wobble/", tools=[None])
    dirname = r.clone_dir(repo_name)
    assert len(find_config(dirname, list())) == 0


def test_clone_adds_to_cleanup_dict():
    m = mock.Mock()
    r = RepoManager(cache_directory="/weeble/wobble/", executor=m,
                    tools=[None])
    r.clone_repo(repo_name, None, None)
    directory = r.clone_dir(repo_name)
    assert directory in r.to_cleanup[repo_name]


def test_updates_if_existing_repo():
    finder = re.compile(r'git clone')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])

    with mock.patch('os.path.isdir') as isdir:
        isdir.return_value = True
        r.clone_repo(repo_name, None, None)

    assert len(calls_matching_re(m, finder)) == 0, "Shouldn't git clone"


def test_clones_if_no_existing_repo():
    finder = re.compile(r'git clone')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])
    r.clone_repo(repo_name, None, None)

    assert len(calls_matching_re(m, finder)) == 1, "Didn't git clone"


def test_adds_remote_if_pr_is_remote():
    finder = re.compile(r'git remote add name url')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])
    r.clone_repo(repo_name, Remote("name", "url"), None)

    assert len(calls_matching_re(m, finder)) == 1, "Remote not added"


def test_pulls_remote_changes_if_remote():
    finder = re.compile(r'git pull --all')
    m = mock.Mock()
    r = RepoManager(cache_directory="/fooz", executor=m, tools=[None])
    r.clone_repo(repo_name, Remote("name", "url"), None)

    assert len(calls_matching_re(m, finder)) == 1, "Didn't pull updates"
