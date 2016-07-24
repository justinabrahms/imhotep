import logging

log = logging.getLogger(__name__)


class Reporter(object):
    """Base class for all reporters.

    If this defines an optional `post_comment(self, message)` method, it will
    be used to notify the user that lint stopped running due to a critical
    number of errors.
    """
    def report_line(self, commit, file_name, line_number, position,
                    message):
        raise NotImplementedError()
