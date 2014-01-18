import logging

log = logging.getLogger(__name__)


class Reporter(object):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        raise NotImplementedError()


class PrintingReporter(Reporter):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        print "Would have posted the following: \n" \
              "commit: %(commit)s\n" \
              "position: %(position)s\n" \
              "message: %(message)s\n" \
              "file: %(filename)s\n" \
              "repo: %(repo)s\n" % {
                  'repo': repo_name,
                  'commit': commit,
                  'position': position,
                  'message': message,
                  'filename': file_name
              }


class CommitReporter(Reporter):
    def __init__(self, requester):
        self.requester = requester

    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        payload = {
            'body': message,
            'sha': commit,
            'path': file_name,
            'position': position,
            'line': None,
        }
        request = 'https://api.github.com/repos/%s/commits/%s/comments' % (
            repo_name, commit)
        log.debug("Commit Request: %s", request)
        log.debug("Commit Payload: %s", payload)
        self.requester.post(request, payload)


class PRReporter(Reporter):
    def __init__(self, requester, pr_number):
        self.requester = requester
        self.pr_number = pr_number

    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        payload = {
            'body': message,
            'commit_id': commit, # sha
            'path': file_name, # relative file path
            'position': position, # line index into the diff
        }
        request = 'https://api.github.com/repos/%s/pulls/%s/comments' % (
            repo_name, self.pr_number)
        log.debug("PR Request: %s", request)
        log.debug("PR Payload: %s", payload)
        result = self.requester.post(request, payload)
        if result.status_code >= 400:
            log.error("Error posting line to github. %s", result.json)
        return result
