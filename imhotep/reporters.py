import logging

log = logging.getLogger(__name__)


class Reporter(object):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        raise NotImplementedError()


class PrintingReporter(Reporter):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        print("Would have posted the following: \n" \
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
              })


class GitHubReporter(Reporter):
    def __init__(self, requester):
        self._comments = []
        self.requester = requester

    def clean_already_reported(self, comments, file_name, position,
                               message):
        for comment in comments:
            if ((comment['path'] == file_name
                 and comment['position'] == position
                 and comment['user']['login'] == self.requester.username)):

                clean_message = []
                for submessage in message:
                    if submessage in comment['body']:
                        continue
                    clean_message.append(submessage)
                return clean_message
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
    def __init__(self, requester, pr_number):
        self.pr_number = pr_number
        super(PRReporter, self).__init__(requester)

    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        report_url = (
            'https://api.github.com/repos/%s/pulls/%s/comments'
            % (repo_name, self.pr_number))
        comments = self.get_comments(report_url)
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
