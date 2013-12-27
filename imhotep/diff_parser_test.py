from imhotep.diff_parser import DiffContextParser
    
def test_skip_line__minus():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("--- a/.gitignore")

def test_skip_line__plus():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("+++ b/.gitignore")

def test_skip_line__index():
    dcp = DiffContextParser("")
    assert dcp.should_skip_line("index 3929bb3..633facf 100644")
