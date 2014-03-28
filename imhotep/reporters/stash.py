import logging
from six import string_types
from .reporter import Reporter

log = logging.getLogger(__name__)


class StashReporter(Reporter):
    def __init__(self, requester, stash_server):
        self.stash_server = stash_server
        self._comments = []
        self.requester = requester

    def clean_already_reported(self, comments, file_name, position,
                               message):
        pass

    def get_comments(self, report_url):
        pass

    def convert_message_to_string(self, message):
        pass


class PReporter(StashReporter):
    def __init__(self, requester, stash_server, pr_number):
        self.pr_number = pr_number
        super(PReporter, self).__init__(requester, stash_server)

    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        project, repo_name = repo_name.split('/')
        report_url = (
            "%s/rest/api/1.0/projects/%s/repos/%s"
            "/pull-requests/%s/comments?path"
            % (self.stash_server, project, repo_name, self.pr_number))
        payload = {
            'text': self.convert_message_to_string(message),
            'anchor': {
                'line': line_number,
                'lineType': 'ADDED',
                'fileType': 'FROM',
                'path': file_name,
                'srcPath': file_name
            }
        }
        log.debug("PR Request: %s", report_url)
        log.debug("PR Payload %s", payload)
        result = self.requester.post(report_url, payload)
        if result.status_code >= 400:
            log.error("Error posting line to stash. %s", result.json)
        return result


