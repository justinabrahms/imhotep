from collections import defaultdict
import logging

log = logging.getLogger(__name__)


class Tool(object):
    """
    Tool represents a program that runs over source code. It returns a nested
    dictionary structure like:

      {'relative_filename': {'line_number': [error1, error2]}}
      eg: {'imhotep/main.py': {'103': ['line too long']}}
    """

    def __init__(self, command_executor, filenames=set()):
        self.executor = command_executor
        self.filenames = filenames

    def invoke(self, dirname, filenames=set()):
        """
        Main entrypoint for all plugins.

        Returns results in the format of:

        {'filename': {
          'line_number': [
            'error1',
            'error2'
            ]
          }
        }

        """
        retval = defaultdict(lambda: defaultdict(list))
        extensions = ' -o '.join(['-name "*%s"' % ext for ext in
                                  self.get_file_extensions()])

        cmd = 'find %s %s | xargs %s' % (
            dirname, extensions, self.get_command(dirname))
        result = self.executor(cmd)
        for line in result.split('\n'):
            output = self.process_line(dirname, line)
            if output is not None:
                filename, lineno, messages = output
                if filename.startswith(dirname):
                    filename = filename[len(dirname) + 1:]
                retval[filename][lineno].append(messages)
        return retval

    def process_line(self, dirname, line):
        """
        Processes a line return a 3-element tuple representing (filename,
        line_number, error_messages) or None to indicate no error.

        :param: dirname - directory the code is running in
        """
        raise NotImplementedError()

    def get_file_extensions(self):
        """
        Returns a list of file extensions this tool should run against.

        eg: ['.py', '.js']
        """
        raise NotImplementedError()

    def get_command(self, dirname):
        """
        Returns the command to run for linting. It is piped a list of files to
        run on over stdin.
        """
        raise NotImplementedError()