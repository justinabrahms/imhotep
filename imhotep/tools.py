from collections import defaultdict
import re
import os
import logging

log = logging.getLogger(__name__)

class Tool(object):
    def __init__(self, command_executor):
        self.executor = command_executor

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


class FoodCritic(Tool):
    foodcriticrc_filename = '.foodcritic'

    def invoke(self, dirname, filenames=set()):
        from main import run
        to_return = defaultdict(lambda: defaultdict(list))
        line_re = re.compile(
            "(?P<message>\w+: [^:]+): (?P<filename>[^:]+):(?P<line_number>\d+)"
        )
        cmd = (
            "find {path} -name *recipes* -type d | "
            "sed 's/recipes//g'"
        )
        result = self.executor(cmd.format(path=dirname))
        # We want to run foodcritic for each path beacuse some recipes
        # are so borked that they break foodcritic.  Let those fail without
        # shitting on everything.
        for path in result.split('\n'):
            log.debug("Running foodcritic on %s", path)
            result = run("foodcritic {0}".format(path))
            for line in ifilter(lambda x: x, result.split('\n')):
                match = line_re.search(line)
                if match is None:
                    continue
                filename = match.group('filename')
                line_num = match.group('line_number')
                message = match.group('message')
                if not line_num.isdigit():
                    # Fuck EOF errors
                    continue
                to_return[filename][line_num].append(message)
        return to_return


class Tailor(Tool):
    tailorrc_filename = '.tailor'

    def invoke(self, dirname, filenames=set()):
        from main import run
        to_return = defaultdict(lambda: defaultdict(list))
        config_path = os.path.join(dirname, self.tailorrc_filename)
        if not os.path.exists(config_path):
            log.debug(
                "{0} is being skipped because it does "
                "not contain a .tailor file".format(config_path)
            )
            return to_return
        # tailor requires an output format to be specified to output yaml
        # which is why we use the temporary results.yaml
        cmd = (
            "tailor "
            "--output-file=results.yaml "
            "{path} 2>&1 > /dev/null"
        )
        results = run("find {dirname} -name '*.rb'".format(dirname=dirname))
        log.debug("Running tailor on %s", dirname)
        for path in results.split('\n'):
            run(cmd.format(path=path))
            with open('results.yaml') as f:
                for filename, errors in yaml.load(f).items():
                    for error in errors:
                        message = error[':message']
                        line_number = error[':line']
                        to_return[filename][line_number].append(message)

        return to_return


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
        # pylint is stupid, this should fix relative path linting
        # if repo is checked out relative to where imhotep is called.
        if os.path.abspath('.') in dirname:
            dirname = dirname[len(os.path.abspath('.'))+1:]

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
