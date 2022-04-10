"""
Thanks to @fridgei & @scottjab for the initial version of this code.
"""
import re
from collections import namedtuple
from typing import List, Union

Line = namedtuple("Line", ["number", "position", "contents"])

diff_re = re.compile(
    r"@@ \-(?P<removed_start>\d+),(?P<removed_length>\d+) "
    r"\+(?P<added_start>\d+),(?P<added_length>\d+) @@"
)


class Entry:
    def __init__(self, origin_filename: str, result_filename: str) -> None:
        self.origin_filename = origin_filename
        self.result_filename = result_filename
        self.origin_lines: List[Line] = []
        self.result_lines: List[Line] = []
        self.added_lines: List[Line] = []
        self.removed_lines: List[Line] = []

    def new_removed(self, line):
        self.removed_lines.append(line)

    def new_added(self, line: Line) -> None:
        self.added_lines.append(line)

    def new_origin(self, line):
        self.origin_lines.append(line)

    def new_result(self, line: Line) -> None:
        self.result_lines.append(line)

    def is_dirty(self):
        return self.result_lines or self.origin_lines


class DiffContextParser:
    def __init__(self, diff_text: Union[bytes, str]) -> None:
        self.diff_text = diff_text

    @staticmethod
    def should_skip_line(line: str) -> bool:
        # "index oldsha..newsha permissions" line or..
        # "index 0000000..78ce7f6"
        if re.search(r"index \w+..\w+( \d)?", line):
            return True
        # --- a/.gitignore
        # +++ b/.gitignore
        # --- /dev/null
        elif re.search(r"(-|\+){3} (a|b)?/.*", line):
            return True
        # "new file mode 100644" on new files
        elif re.search("new file mode.*", line):
            return True
        return False

    def parse(self) -> List[Entry]:
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
            if type(line) is bytes:
                line = line.decode("utf-8")
            assert type(line) is str
            # New File
            match = re.search(
                r"diff .*a/(?P<origin_filename>.*) " r"b/(?P<result_filename>.*)", line
            )
            if match is not None:
                if z is not None:
                    result.append(z)
                z = Entry(
                    match.group("origin_filename"), match.group("result_filename")
                )
                position = 0
                continue

            if self.should_skip_line(line):
                continue

            header = diff_re.search(line)
            if header is not None:
                before_line_number = int(header.group("removed_start"))
                after_line_number = int(header.group("added_start"))
                position += 1
                continue

            if z is not None:
                # removed line
                if line.startswith("-"):
                    z.new_removed(Line(before_line_number, position, line[1:]))
                    z.new_origin(Line(before_line_number, position, line[1:]))
                    before_line_number += 1

                # added line
                elif line.startswith("+"):
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
