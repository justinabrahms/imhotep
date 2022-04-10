from collections import namedtuple
from typing import Any, Dict, Optional

from imhotep.http_client import BasicAuthRequester

Remote = namedtuple("Remote", ("name", "url"))
CommitInfo = namedtuple("CommitInfo", ("commit", "origin", "remote_repo", "ref"))


class PRInfo:
    def __init__(self, json: Dict[str, Any]) -> None:
        self.json = json

    @property
    def base_sha(self) -> str:
        return self.json["base"]["sha"]

    @property
    def head_sha(self) -> str:
        return self.json["head"]["sha"]

    @property
    def base_ref(self):
        return self.json["base"]["ref"]

    @property
    def head_ref(self) -> str:
        return self.json["head"]["ref"]

    @property
    def has_remote_repo(self) -> bool:
        return (
            self.json["base"]["repo"]["owner"]["login"]
            != self.json["head"]["repo"]["owner"]["login"]
        )

    @property
    def remote_repo(self) -> Optional[Remote]:
        remote = None
        if self.has_remote_repo:
            remote = Remote(
                name=self.json["head"]["repo"]["owner"]["login"],
                url=self.json["head"]["repo"]["clone_url"],
            )
        return remote

    def to_commit_info(self) -> CommitInfo:
        return CommitInfo(self.base_sha, self.head_sha, self.remote_repo, self.head_ref)


def get_pr_info(
    requester: BasicAuthRequester, reponame: str, number: str, domain: str
) -> PRInfo:
    "Returns the PullRequest as a PRInfo object"
    # API locations are different for non-github.com locales. https://docs.github.com/en/enterprise-server@3.2/rest/guides/getting-started-with-the-rest-api

    if domain == "github.com":
        api_url = "api.%s" % domain
    else:
        api_url = "%s/api/v3" % domain

    resp = requester.get(f"https://{api_url}/repos/{reponame}/pulls/{number}")
    return PRInfo(resp.json())
