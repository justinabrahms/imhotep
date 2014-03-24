import logging
from six import string_types
from .reporter import Reporter

log = logging.getLogger(__name__)


class PrintingReporter(Reporter):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        print("Would have posted the following: \n"
              "commit: %(commit)s\n"
              "position: %(position)s\n"
              "message: %(message)s\n"
              "file: %(filename)s\n"
              "repo: %(repo)s\n" % {
                  'repo': repo_name,
                  'commit': commit,
                  'position': position,
                  'message': message,
                  'filename': file_name
              })

