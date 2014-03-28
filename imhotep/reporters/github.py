import logging
from six import string_types
from .reporter import Reporter

log = logging.getLogger(__name__)


class GitHubReporter(Reporter):
    def __init__(self, requester):
        self._comments = []
        self.requester = requester

    def clean_already_reported(self, comments, file_name, position,
                               message):
        """
        message is potentially a list of messages to post. This is later
        converted into a string.
        """
        for comment in comments:
            if ((comment['path'] == file_name
                 and comment['position'] == position
                 and comment['user']['login'] == self.requester.username)):

                return [m for m in message if m not in comment['body']]
        return message

    def get_comments(self, report_url):
        if not self._comments:
            log.debug("PR Request: %s", report_url)
            result = self.requester.get(report_url)
            if result.status_code >= 400:
                log.error("Error requesting comments from github. %s",
                          result.json())
                return
            self._comments = result.json()
        return self._comments

    def convert_message_to_string(self, message):
        """Convert message from list to string for GitHub API."""
        final_message = ''
        for submessage in message:
            final_message += '* {submessage}\n'.format(submessage=submessage)
        return final_message


class CommitReporter(GitHubReporter):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        report_url = (
            'https://api.github.com/repos/%s/commits/%s/comments'
            % (repo_name, commit))
        comments = self.get_comments(report_url)
        message = self.clean_already_reported(comments, file_name,
                                              position, message)
        payload = {
            'body': self.convert_message_to_string(message),
            'sha': commit,
            'path': file_name,
            'position': position,
            'line': None,
        }
        log.debug("Commit Request: %s", report_url)
        log.debug("Commit Payload: %s", payload)
        self.requester.post(report_url, payload)


class PRReporter(GitHubReporter):
    def __init__(self, requester, pr_number, **kwargs):
        self.pr_number = pr_number
        super(PRReporter, self).__init__(requester)

    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        report_url = (
            'https://api.github.com/repos/%s/pulls/%s/comments'
            % (repo_name, self.pr_number))
        comments = self.get_comments(report_url)
        if isinstance(message, string_types):
            message = [message]
        message = self.clean_already_reported(comments, file_name,
                                              position, message)
        if not message:
            log.debug('Message already reported')
            return None
        payload = {
            'body': self.convert_message_to_string(message),
            'commit_id': commit,  # sha
            'path': file_name,  # relative file path
            'position': position,  # line index into the diff
        }
        log.debug("PR Request: %s", report_url)
        log.debug("PR Payload: %s", payload)
        result = self.requester.post(report_url, payload)
        if result.status_code >= 400:
            log.error("Error posting line to github. %s", result.json)
        return result
