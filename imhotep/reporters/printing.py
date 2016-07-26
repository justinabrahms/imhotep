import logging
from .reporter import Reporter

log = logging.getLogger(__name__)


class PrintingReporter(Reporter):
    def report_line(self, commit, file_name, line_number, position, message):
        print("Would have posted the following: \n"
              "commit: %(commit)s\n"
              "position: %(position)s\n"
              "message: %(message)s\n"
              "file: %(filename)s\n" % {
                  'commit': commit,
                  'position': position,
                  'message': message,
                  'filename': file_name
              })
