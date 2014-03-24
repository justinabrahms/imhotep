import logging
from six import string_types

log = logging.getLogger(__name__)


class Reporter(object):
    def report_line(self, repo_name, commit, file_name, line_number, position,
                    message):
        raise NotImplementedError()

