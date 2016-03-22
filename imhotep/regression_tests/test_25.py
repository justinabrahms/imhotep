from imhotep.diff_parser import DiffContextParser

diff = """diff --git a/foo.py b/foo.py
new file mode 100644
index 0000000..78ce7f6
--- /dev/null
+++ b/foo.py
@@ -0,0 +1,7 @@
+class Foo(object):
+  pass
+
+class Bar(object):
+  pass
+
+print "Works";
"""


def test_file_adds_arent_off():
    parser = DiffContextParser(diff)
    results = parser.parse()
    assert 'class Foo' in results[0].added_lines[0].contents
