from collections import defaultdict
import re
import os
import logging

log = logging.getLogger(__name__)

class Tool(object):
    def __init__(self, command_executor):
        self.executor = command_executor

    def process_line(self, line):
        return []

    def get_file_extension(self):
        """
        Returns a list of file extensions this tool should run against.

        eg: ['.py', '.js']
        """
        return ['']

    def invoke(self, dirname, filenames=set()):
        """
        Returns results in the format of:

        {'filename': {
          'line_number': [
            'error1',
            'error2'
            ]
          }
        }

        """
        raise NotImplementedError


class JSHint(Tool):
    response_format = re.compile(r'^(?P<filename>.*): line (?P<line_number>\d+), col \d+, (?P<message>.*)$')
    jshintrc_filename = '.jshintrc'

    def invoke(self, dirname, filenames=set()):
        to_return = defaultdict(lambda: defaultdict(list))
        cmd = 'find %s -name "*.js" | ' \
          " xargs jshint " % dirname
        jshint_file = os.path.join(dirname, self.jshintrc_filename)
        if os.path.exists(jshint_file):
            cmd += "--config=%s" % jshint_file
        result = self.executor(cmd)
        # format:
        # cssauron/index.js: line 87, col 12, Missing semicolon.
        for l in result.split("\n"):
            line = l[len(dirname)+1:] # +1 for trailing slash to make relative dir
            match = self.response_format.search(line)
            if match is not None:
                to_return[match.group('filename')][match.group('line_number')].append(match.group('message'))
        return to_return


class PyLint(Tool):
    pylintrc_filename = '.pylintrc'

    def invoke(self, dirname, filenames=set()):
        to_return = defaultdict(lambda: defaultdict(list))
        log.debug("Running pylint on %s", dirname)
        cmd = 'find %s -name "*.py" | ' \
          'xargs pylint --output-format=parseable -rn'

        if os.path.exists(os.path.join(dirname, self.pylintrc_filename)):
            cmd += " --rcfile=%s" % os.path.join(
                dirname, self.pylintrc_filename)

        result = self.executor(cmd % dirname)
        # splitting based on newline + dirname and trailing slash will make
        # beginning of line until first colon the relative filename. It also has
        # the nice side effect of allowing us multi-line output from the tool
        # without things breaking.
        for line in result.split("\n%s/" % dirname):
            if len(line) == 0:
                continue
            filename, line_num, error = line.split(':', 2)
            if len(filenames) != 0 and filename not in filenames:
                continue
            to_return[filename][line_num].append(error)
        return to_return
