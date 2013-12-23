class Reporter(object):
    def report_line(self, repo_name, commit, file_name, line_number, position, message):
        raise NotImplementedError()


class PrintingReporter(Reporter):
    def report_line(self, repo_name, commit, file_name, line_number, position, message):
        print "Would have posted the following: \n" \
          "commit: %(commit)s\n" \
          "position: %(position)s\n" \
          "message: %(message)s\n" \
          "file: %(filename)s\n" \
          "repo: %(repo)s\n" % {
              'repo': repo.name,
              'commit': commit,
              'position': posMap[x],
              'message': violations['%s' % x],
              'filename': entry.result_filename
          }


class CommitReporter(Reporter):
    def __init__(self, requester):
        self.requester = requester

    def report_line(self, repo_name, commit, file_name, line_number, position, message):
        self.commit_post(
            repo.name, commit, posMap[x], violations['%s' % x],
            entry.result_filename)

    def commit_post(reponame, commit, position, txt, path):
        payload = {
            'body': txt,
            'sha': commit,
            'path': path,
            'position': position,
            'line': None,
        }
        self.requester.post(
            'https://api.github.com/repos/%s/commits/%s/comments' % (reponame, commit),
            payload)


class PRReporter(Reporter):
    def __init__(self, requester, pr_number):
        self.requester = requester
        self.pr_number = pr_number

    def report_line(self, repo_name, commit, file_name, line_number, position, message):
        self.pr_post(
            repo.name, commit, posMap[x], violations['%s' % x],
            entry.result_filename)

    def pr_post(reponame, commit, position, txt, path):
        payload = {
            'body': txt,
            'commit_id': commit, # sha
            'path': path, # relative file path
            'position': position, # line index into the diff
        }

        return self.requester.post(
            'https://api.github.com/repos/%s/pulls/%s/comments' % (reponame, self.pr_number),
            payload)
