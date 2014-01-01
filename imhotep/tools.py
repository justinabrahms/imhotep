from collections import defaultdict
import re
import os
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
                    filename = filename[len(dirname)+1:]
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


class JSHint(Tool):
    response_format = re.compile(r'^(?P<filename>.*): " \
        "line (?P<line_number>\d+), col \d+, (?P<message>.*)$')
    jshintrc_filename = '.jshintrc'

    def process_line(self, dirname, line):
        line = line[len(dirname)+1:]  # +1 for trailing slash to make dir
                                      # relative
        match = self.response_format.search(line)
        if match is not None:
            return match.groups()

    def get_file_extensions(self):
        return ['.js']

    def get_command(self, dirname):
        cmd = "jshint "
        config_path = os.path.join(dirname, self.jshintrc_filename)
        if os.path.exists(config_path):
            cmd += "--config=%s" % config_path
        return cmd


class PyLint(Tool):
    response_format = re.compile(r'(?P<filename>.*):(?P<line_num>\d+):'
                                 '(?P<message>.*)')
    pylintrc_filename = '.pylintrc'

    def get_file_extensions(self):
        return ['.py']

    def process_line(self, dirname, line):
        match = self.response_format.search(line)
        if match is not None:
            if len(self.filenames) != 0:
                if match.group('filename') not in self.filenames:
                    return
            filename, line, messages = match.groups()
            # If you run pylint on /foo/bar/baz and you are in the /foo/bar
            # directory, it will spit out paths that look like: ./baz To fix
            # this, we run it through `os.path.abspath` which will give it a
            # full, absolute path.
            filename = os.path.abspath(filename)
            return filename, line, messages

    def get_command(self, dirname):
        cmd = 'pylint --output-format=parseable -rn'
        if os.path.exists(os.path.join(dirname, self.pylintrc_filename)):
            cmd += " --rcfile=%s" % os.path.join(
                dirname, self.pylintrc_filename)
        return cmd
