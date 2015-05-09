import logging
from six import string_types
from .reporter import Reporter


log = logging.getLogger(__name__)


class StashReporter(Reporter):

    def __init__(self, requester):
        self._comments = None
        self.requester = requester

    def clean_already_reported(self, comments, file_name, line_number, messages):
        for comment in comments:
            if (comment['anchor']['path'] == file_name
                    and comment['anchor']['line'] == line_number
                    and comment['author']['name'] == self.requester.username):
                return [m for m in messages if m not in comment['text']]
        return messages

    def get_comments(self, base_url):
        if self._comments is None:
            # get changes to get file set, then get comments per file
            changes_url = base_url + '/changes'
            res = self.requester.get(changes_url)
            files = [obj['path']['toString'] for obj in res.json()['values']]

            comments = []
            for path in files:
                url = base_url + '/comments?path=' + path
                res = self.requester.get(url)
                comments.extend(res.json()['values'])
            self._comments = comments

        return self._comments

    def convert_message_to_string(self, message):
        final_message = ''
        for submessage in message:
            final_message += '* {submessage}\n'.format(submessage=submessage)
        return final_message


class CommitReporter(StashReporter):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        report_url = (
            'https://localhost/repos/%s/commits/%s/comments'
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


class PRReporter(StashReporter):

    def __init__(self, requester, pr_number):
        self.pr_number = pr_number
        super(PRReporter, self).__init__(requester)

    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message, **kwargs):

        pr_url = 'https://{host}/rest/api/1.0/projects/{project}/repos/{repo}/pull-requests/{pr}'.format(
            host=kwargs['stash_host'], project=kwargs['project'], repo=repo_name, pr=self.pr_number)
        report_url = pr_url + '/comments'

        comments = self.get_comments(pr_url)
        if isinstance(message, string_types):
            message = [message]
        message = self.clean_already_reported(comments, file_name,
                                              line_number, message)
        if not message:
            log.debug('Message already reported')
            return None
        payload = {
            'text': self.convert_message_to_string(message),
            'anchor': {
                'line': line_number,
                'lineType': 'ADDED',
                'fileType': 'TO',
                'path': file_name,
                'srcPath': file_name,
            },
        }

        log.debug("PR Request: %s", report_url)
        log.debug("PR Payload: %s", payload)
        result = self.requester.post(report_url, payload)
        if result.status_code >= 400:
            log.error("Error posting line to github. %s", result.json())
        return result
