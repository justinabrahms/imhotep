"""
Thanks to @fridgei & @scottjab for the initial version of this code.
"""
from collections import namedtuple
import re

Line = namedtuple("Line", ["number", "position", "contents"])

diff_re = re.compile(
    "@@ \-(?P<removed_start>\d+),(?P<removed_length>\d+) "
    "\+(?P<added_start>\d+),(?P<added_length>\d+) @@"
)


class Entry(object):
    def __init__(self, origin_filename, result_filename):
        self.origin_filename = origin_filename
        self.result_filename = result_filename
        self.origin_lines = []
        self.result_lines = []
        self.added_lines = []
        self.removed_lines = []

    def new_removed(self, line):
        self.removed_lines.append(line)

    def new_added(self, line):
        self.added_lines.append(line)

    def new_origin(self, line):
        self.origin_lines.append(line)

    def new_result(self, line):
        self.result_lines.append(line)

    def is_dirty(self):
        return self.result_lines or self.origin_lines


class DiffContextParser:
    def __init__(self, diff_text):
        self.diff_text = diff_text

    @staticmethod
    def should_skip_line(line):
        # "index oldsha..newsha permissions" line or..
        # "index 0000000..78ce7f6"
        if re.search(r'index \w+..\w+( \d)?', line):
            return True
        # --- a/.gitignore
        # +++ b/.gitignore
        # --- /dev/null
        elif re.search('(-|\+){3} (a|b)?/.*', line):
            return True
        # "new file mode 100644" on new files
        elif re.search('new file mode.*', line):
            return True
        return False

    def parse(self):
        """
        Parses everyting into a datastructure that looks like:

            result = [{
                'origin_filename': '',
                'result_filename': '',
                'origin_lines': [], // all lines of the original file
                'result_lines': [], // all lines of the newest file
                'added_lines': [], // all lines added to the result file
                'removed_lines': [], // all lines removed from the result file
            }, ...]

        """
        result = []

        z = None

        before_line_number, after_line_number = 0, 0
        position = 0

        for line in self.diff_text.splitlines():
            line = line.decode('utf-8')
            # New File
            match = re.search(r'diff .*a/(?P<origin_filename>.*) '
                              r'b/(?P<result_filename>.*)', line)
            if match is not None:
                if z is not None:
                    result.append(z)
                z = Entry(match.group('origin_filename'),
                          match.group('result_filename'))
                position = 0
                continue

            if self.should_skip_line(line):
                continue

            header = diff_re.search(line)
            if header is not None:
                before_line_number = int(header.group('removed_start'))
                after_line_number = int(header.group('added_start'))
                position += 1
                continue

            # removed line
            if line.startswith('-'):
                z.new_removed(Line(before_line_number, position, line[1:]))
                z.new_origin(Line(before_line_number, position, line[1:]))
                before_line_number += 1

            # added line
            elif line.startswith('+'):
                z.new_added(Line(after_line_number, position, line[1:]))
                z.new_result(Line(after_line_number, position, line[1:]))
                after_line_number += 1

            # untouched context line.
            else:
                z.new_origin(Line(before_line_number, position, line[1:]))
                z.new_result(Line(after_line_number, position, line[1:]))

                before_line_number += 1
                after_line_number += 1

            position += 1

        if z is not None:
            result.append(z)

        return result
