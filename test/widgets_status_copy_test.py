"""Tests for the Copy actions in cola.widgets.status.

These verify the multi-selection behaviour: selecting N files in the status
tree and triggering "Copy Path" / "Copy Relative Path" / "Copy Basename" /
"Copy Leading Path" / a custom "Copy Format" should put N newline-separated
strings on the clipboard, not just the first file.
"""
from unittest.mock import patch

from cola.widgets import status


class _FakeSelection:
    """Minimal stand-in for cola.models.selection.SelectionModel.

    Real selection.group() returns the first non-empty list among
    (staged, unmerged, modified, untracked); this fake honours the same
    precedence so we can also assert the "staged wins over modified"
    behaviour the copy helpers inherit.
    """

    def __init__(self, staged=None, unmerged=None, modified=None, untracked=None):
        self._staged = staged or []
        self._unmerged = unmerged or []
        self._modified = modified or []
        self._untracked = untracked or []

    def group(self):
        for bucket in (self._staged, self._unmerged, self._modified, self._untracked):
            if bucket:
                return bucket
        return []


class _FakeContext:
    def __init__(self, selection):
        self.selection = selection


def _ctx(**kwargs):
    return _FakeContext(_FakeSelection(**kwargs))


def test_copy_path_relative_joins_selected_paths_with_newlines():
    ctx = _ctx(modified=['a.py', 'sub/b.py', 'sub/c.py'])
    with patch.object(status.qtutils, 'set_clipboard') as set_clipboard:
        status.copy_path(ctx, absolute=False)
    set_clipboard.assert_called_once_with('a.py\nsub/b.py\nsub/c.py')


def test_copy_relpath_is_a_relative_copy():
    """copy_relpath is documented to be copy_path(absolute=False)."""
    ctx = _ctx(modified=['x.py', 'y.py'])
    with patch.object(status.qtutils, 'set_clipboard') as set_clipboard:
        status.copy_relpath(ctx)
    set_clipboard.assert_called_once_with('x.py\ny.py')


def test_copy_basename_strips_extensions_per_path():
    ctx = _ctx(modified=['src/foo.py', 'src/bar.txt', 'baz'])
    with patch.object(status.qtutils, 'set_clipboard') as set_clipboard:
        status.copy_basename(ctx)
    set_clipboard.assert_called_once_with('foo\nbar\nbaz')


def test_copy_leading_path_deduplicates_repeated_prefixes():
    """A multi-file selection inside one directory should not paste the same
    leading path N times -- the helper deduplicates while preserving order."""
    ctx = _ctx(modified=['src/foo.py', 'src/bar.py', 'tests/spam.py'])
    with patch.object(status.qtutils, 'set_clipboard') as set_clipboard:
        status.copy_leading_path(ctx, strip_components=1)
    set_clipboard.assert_called_once_with('src\ntests')


def test_copy_format_runs_the_template_per_selected_path():
    ctx = _ctx(modified=['src/foo.py', 'src/bar.txt'])
    with patch.object(status.qtutils, 'set_clipboard') as set_clipboard:
        status.copy_format(ctx, '%(path)s::%(basename)s')
    set_clipboard.assert_called_once_with('src/foo.py::foo\nsrc/bar.txt::bar')


def test_copy_actions_are_a_no_op_when_nothing_is_selected():
    """No selection -> clipboard is not touched at all."""
    ctx = _ctx()  # all buckets empty
    with patch.object(status.qtutils, 'set_clipboard') as set_clipboard:
        status.copy_path(ctx)
        status.copy_relpath(ctx)
        status.copy_basename(ctx)
        status.copy_leading_path(ctx, strip_components=1)
        status.copy_format(ctx, '%(path)s')
    set_clipboard.assert_not_called()


def test_single_file_selection_does_not_produce_a_trailing_newline():
    ctx = _ctx(staged=['only.py'])
    with patch.object(status.qtutils, 'set_clipboard') as set_clipboard:
        status.copy_path(ctx, absolute=False)
    set_clipboard.assert_called_once_with('only.py')


def test_staged_bucket_wins_over_modified_for_mixed_selections():
    """selection.group() picks the first non-empty bucket. The Copy actions
    inherit this -- selecting one staged file and one modified file copies
    only the staged file, matching the long-standing single-file behaviour."""
    ctx = _ctx(staged=['s.py'], modified=['m.py'])
    with patch.object(status.qtutils, 'set_clipboard') as set_clipboard:
        status.copy_path(ctx, absolute=False)
    set_clipboard.assert_called_once_with('s.py')
