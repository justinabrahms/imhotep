"""
Integration test for imhotep.

1. Run against a known bad pull request.
2. Fetch the list of review comments. Validate the count is the correct number.
3. Delete all review comments.

list comments: GET /repos/:owner/:repo/pulls/:number/comments
               http://developer.github.com/v3/pulls/comments/#list-comments-on-a-pull-request

delete comment: DELETE /repos/:owner/:repo/pulls/comments/:number
                http://developer.github.com/v3/pulls/comments/#delete-a-comment


-- things needed to actually make this sellable:

1. landing page
2. github linking
3. config management per account
4. billing system
5. web hook from github to trigger build run


Questionaire:

1. Does your company have a code review process?
2. Who do you use for it? github, bb, google code, other
3. Do you you run linters on your code?
4. How much time do you spend on code review?
5. T/F: Within the past month, I have caught style infractions in code review that linters would have caught.


Finding Customers, broken into segments:
1. Rank/File Developers
2. Architects
3. Management / Business owners
"""
import os
import pytest
from imhotep.http import GithubRequester
from imhotep.reporters import PRReporter

ghu = os.getenv('GITHUB_USERNAME')
ghp = os.getenv('GITHUB_PASSWORD')

@pytest.mark.skipif(not ghu or not ghp,
                    reason="must specify github credentials as env var")
def test_github_post():
    repo = 'imhotepbot/sacrificial-integration-tests'
    pr = 1
    test_str = 'integration test error name'
    req = GithubRequester(ghu, ghp)
    r = PRReporter(req, pr)
    r.report_line(repo,
                  'da6a127',
                  'foo.py',
                  2,
                  3, # the first 'pass' line.
                  test_str)
    comments = req.get('https://api.github.com/repos/%s/pulls/%s/comments' %
                       (repo, pr)).json
    posted = [x for x in comments if test_str in x['body']]

    try:
        assert len(posted) == 1
    finally:
        for comment in comments:
            req.delete('https://api.github.com/repos/%s/pulls/comments/%s' % (
                repo, comment['id']))