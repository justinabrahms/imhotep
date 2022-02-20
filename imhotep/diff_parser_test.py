from imhotep.diff_parser import DiffContextParser, Entry
from imhotep.testing_utils import fixture_path


def test_skip_line__minus():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("--- a/.gitignore")


def test_skip_line__plus():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("+++ b/.gitignore")


def test_skip_line__null():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("--- /dev/null")


def test_skip_line__new_file():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("new file mode 100644")


def test_skip_line__index():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("index 3929bb3..633facf 100644")


def test_skip_line__index_no_permissions():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("index 0000000..78ce7f6")


def test_skip_line__noskip():
    dcp = DiffContextParser("")
    assert not dcp.should_skip_line("+ this is a legit line")


with open(fixture_path('two-block.diff')) as f:
    two_block = bytes(f.read(), 'utf-8')

with open(fixture_path('two-file.diff')) as f:
    two_file = bytes(f.read(), 'utf-8')


def test_multi_block_single_file():
    dcp = DiffContextParser(two_block)
    results = dcp.parse()
    entry = results[0]

    assert len(entry.added_lines) == 5
    assert len(entry.removed_lines) == 1


def test_linum_counting():
    dcp = DiffContextParser(two_block)
    results = dcp.parse()
    entry = results[0]

    assert entry.removed_lines[0].number == 2


def test_position_counting():
    dcp = DiffContextParser(two_block)
    results = dcp.parse()
    entry = results[0]

    # First @@ is 0 and we count from there.
    valid_positions = set([3, 9, 10, 11, 12])
    assert set([x.position for x in entry.added_lines]) == valid_positions


def test_two_file():
    dcp = DiffContextParser(two_file)
    results = dcp.parse()

    entry1, entry2 = results

    assert entry1.origin_filename == '.travis.yml'
    assert entry1.result_filename == '.travis.yml'
    assert entry2.origin_filename == 'requirements.txt'
    assert entry2.result_filename == 'requirements.txt'


def test_entry__clean():
    e = Entry('fna', 'fnb')
    assert not e.is_dirty()


def test_entry__dirty_result():
    e = Entry('fna', 'fnb')
    e.new_result('line')
    assert e.is_dirty()


def test_entry__dirty_result():
    e = Entry('fna', 'fnb')
    e.new_origin('line')
    assert e.is_dirty()
