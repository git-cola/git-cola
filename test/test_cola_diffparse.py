import os
import unittest

from cola import gitcmds
from cola import utils
from cola.diffparse import DiffParser

import helper


class DiffParseModel(object):
    def __init__(self):
        self.last_worktree_diff = None
        self.last_diff = None
        self.head = 'HEAD'
        self.amend = False

    def amending(self):
        return self.amend

    def apply_diff_to_worktree(self, path):
        if os.path.exists(path):
            self.last_worktree_diff = utils.slurp(path)

    def apply_diff(self, path):
        if os.path.exists(path):
            self.last_diff = utils.slurp(path)


class DiffSource(object):
    def __init__(self, fwd, reverse):
        self.fwd = utils.slurp(fwd)
        self.reverse = utils.slurp(reverse)

    def get(self, head, amending, filename, cached, reverse):
        if reverse:
            return self.parse(self.reverse)
        else:
            return self.parse(self.fwd)

    def parse(self, diffoutput):
        return gitcmds.extract_diff_header(
                status=0, deleted=False, encoding=None,
                with_diff_header=True, suppress_header=False,
                diffoutput=diffoutput)


class DiffParseTestCase(unittest.TestCase):
    def setUp(self):
        self.model = DiffParseModel()

    def test_diff(self):
        fwd = helper.fixture('diff.txt')
        reverse = helper.fixture('diff-reverse.txt')
        source = DiffSource(fwd, reverse)
        model = DiffParseModel()
        parser = DiffParser(model, filename='',
                            cached=False, reverse=False,
                            diff_source=source)

        self.assertEqual(parser.offsets(),
                [916, 1798, 2550])
        self.assertEqual(parser.spans(),
                [[0, 916], [916, 1798], [1798, 2550]])

        diffs = parser.diffs()
        self.assertEqual(len(diffs), 3)

        self.assertEqual(len(diffs[0]), 23)
        self.assertEqual(diffs[0][0],
                '@@ -6,10 +6,21 @@ from cola import gitcmds')
        self.assertEqual(diffs[0][1],
                ' from cola import gitcfg')
        self.assertEqual(diffs[0][2],
                ' ')
        self.assertEqual(diffs[0][3],
                ' ')
        self.assertEqual(diffs[0][4],
                '+class DiffSource(object):')

        self.assertEqual(len(diffs[1]), 18)
        self.assertEqual(diffs[1][0],
                '@@ -29,13 +40,11 @@ class DiffParser(object):')
        self.assertEqual(diffs[1][1],
                '         self.diff_sel = []')
        self.assertEqual(diffs[1][2],
                '         self.selected = []')
        self.assertEqual(diffs[1][3],
                '         self.filename = filename')
        self.assertEqual(diffs[1][4],
                '+        self.diff_source = diff_source or DiffSource()')

        self.assertEqual(len(diffs[2]), 18)
        self.assertEqual(diffs[2][0],
                '@@ -43,11 +52,10 @@ class DiffParser(object):')

    def test_diff_at_start(self):
        fwd = helper.fixture('diff-start.txt')
        reverse = helper.fixture('diff-start-reverse.txt')

        source = DiffSource(fwd, reverse)
        model = DiffParseModel()
        parser = DiffParser(model, filename='',
                            cached=False, reverse=False,
                            diff_source=source)

        self.assertEqual(parser.diffs()[0][0], '@@ -1 +1,4 @@')
        self.assertEqual(parser.offsets(), [30])
        self.assertEqual(parser.spans(), [[0, 30]])
        self.assertEqual(parser.diffs_for_range(0, 10),
                         ([u'@@ -1 +1,4 @@\n bar\n+a\n+b\n+c\n\n'],
                          [0]))

    def test_diff_at_end(self):
        fwd = helper.fixture('diff-end.txt')
        reverse = helper.fixture('diff-end-reverse.txt')

        source = DiffSource(fwd, reverse)
        model = DiffParseModel()
        parser = DiffParser(model, filename='',
                            cached=False, reverse=False,
                            diff_source=source)

        self.assertEqual(parser.diffs()[0][0], '@@ -1,39 +1 @@')
        self.assertEqual(parser.offsets(), [1114])
        self.assertEqual(parser.spans(), [[0, 1114]])

if __name__ == '__main__':
    unittest.main()
