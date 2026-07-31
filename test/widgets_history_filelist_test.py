# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Characterization tests for FileWidget as used by the history file panel."""

import sys
from unittest.mock import MagicMock

import pytest

from cola import icons
from cola.widgets.filelist import FileTreeWidgetItem
from cola.widgets.filelist import FileWidget
from cola.widgets.filelist import parse_status_and_numstat
from qtpy import QtCore
from qtpy import QtWidgets

from .helper import app_context

assert app_context is not None


@pytest.fixture(scope='module')
def qapp():
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


@pytest.fixture
def managed_qobject(qapp):
    objects = []

    def manage(obj):
        objects.append(obj)
        return obj

    yield manage

    qapp.processEvents()
    for obj in reversed(objects):
        if isinstance(obj, QtWidgets.QWidget):
            obj.close()
    qapp.processEvents()
    for obj in reversed(objects):
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    qapp.processEvents()


def test_list_files_creates_file_tree_items(qapp, app_context, managed_qobject):
    """list_files() builds FileTreeWidgetItem rows with path and +/- columns."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.list_files(['3\t1\tsrc/a.py', '0\t10\tsrc/b.py'])

    assert widget.topLevelItemCount() == 2
    item = widget.topLevelItem(0)
    assert isinstance(item, FileTreeWidgetItem)
    assert item.path == 'src/a.py'
    assert item.text(0) == 'src/a.py'
    assert item.text(1) == '3'
    assert item.text(2) == '1'


def test_empty_commit_selection_clears_the_list(qapp, app_context, managed_qobject):
    """An empty selection clears the widget without running git."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.list_files(['1\t0\tsrc/a.py'])

    widget.commits_selected([])

    assert widget.topLevelItemCount() == 0


def test_selection_emits_selected_paths(qapp, app_context, managed_qobject):
    """itemSelectionChanged emits files_selected with the selected paths."""
    widget = managed_qobject(FileWidget(app_context, None))
    emitted = []
    widget.files_selected.connect(emitted.append)
    widget.list_files(['3\t1\tsrc/a.py', '0\t10\tsrc/b.py'])

    widget.setCurrentItem(widget.topLevelItem(0))

    assert emitted == [['src/a.py']]


def test_parser_splits_nul_separated_raw_and_numstat():
    """ "git show --raw --numstat -z" yields a status map plus numstat rows."""
    out = ':100644 100644 aaa bbb M\0cola/main.py\0' ':000000 100644 000 ccc A\0cola/new.py\0' '33\t0\tcola/main.py\0' '10\t0\tcola/new.py\0'

    status_by_path, numstat = parse_status_and_numstat(out, '\0')

    assert status_by_path == {'cola/main.py': 'M', 'cola/new.py': 'A'}
    assert numstat == ['33\t0\tcola/main.py', '10\t0\tcola/new.py']


def test_parser_splits_newline_separated_raw_and_numstat():
    """ "git diff-index --raw --numstat" keeps the path inline, newline separated."""
    out = ':100644 100644 aaa bbb M\ta.py\n' ':000000 100644 000 ccc A\tb.py\n' '1\t0\ta.py\n' '1\t0\tb.py\n'

    status_by_path, numstat = parse_status_and_numstat(out, '\n')

    assert status_by_path == {'a.py': 'M', 'b.py': 'A'}
    assert numstat == ['1\t0\ta.py', '1\t0\tb.py']


def test_parser_tolerates_numstat_without_raw():
    """Merge commits emit numstat only; the status map stays empty."""
    status_by_path, numstat = parse_status_and_numstat('1\t0\tt.py\0', '\0')

    assert status_by_path == {}
    assert numstat == ['1\t0\tt.py']


@pytest.mark.parametrize(
    ('status', 'expected'),
    (
        ('A', 'plus.svg'),
        ('M', 'modified.svg'),
        ('D', 'circle-slash-red.svg'),
        ('T', 'modified.svg'),
        ('R', 'git-compare.svg'),
        ('C', 'git-compare.svg'),
        ('X', 'file-text.svg'),
        ('', 'file-text.svg'),
    ),
)
def test_diff_status_basename_maps_known_codes(status, expected):
    """Each git status code maps to the documented icon basename."""
    assert icons.diff_status_basename(status, 'src/Makefile') == expected


def _fake_commit(oid, summary='summary'):
    """Ein Commit-Stellvertreter mit den Feldern, die die Diff-Ansicht liest."""
    commit = MagicMock()
    commit.oid = oid
    commit.author = 'A U Thor'
    commit.email = 'author@example.com'
    commit.authdate = '2026-01-01'
    commit.summary = summary
    return commit


def test_commits_selected_remembers_the_commits(qapp, app_context, managed_qobject):
    """Die angezeigten Dateien gehoeren zu einem Commit - der wird gemerkt."""
    widget = managed_qobject(FileWidget(app_context, None))
    commit = _fake_commit('a' * 40)

    widget.commits_selected([commit])

    assert widget.commits == [commit]


def test_empty_selection_forgets_the_commits(qapp, app_context, managed_qobject):
    """Ohne Auswahl bleibt kein Commit uebrig, an dem ein Doppelklick haengt."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.commits_selected([_fake_commit('a' * 40)])

    widget.commits_selected([])

    assert widget.commits == []


def test_new_widget_starts_without_commits(qapp, app_context, managed_qobject):
    widget = managed_qobject(FileWidget(app_context, None))

    assert widget.commits == []
