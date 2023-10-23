from typing import List, Union
    def __init__(self, origin_filename: str, result_filename: str) -> None:
        self.origin_lines: List[Line] = []
        self.result_lines: List[Line] = []
        self.added_lines: List[Line] = []
        self.removed_lines: List[Line] = []
    def new_added(self, line: Line) -> None:
    def new_result(self, line: Line) -> None:
    def __init__(self, diff_text: Union[bytes, str]) -> None:
    def should_skip_line(line: str) -> bool:
    def parse(self) -> List[Entry]:
            assert type(line) is str
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