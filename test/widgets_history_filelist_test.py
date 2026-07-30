# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Characterization tests for FileWidget as used by the history file panel."""

import sys

import pytest

from cola.widgets.filelist import FileTreeWidgetItem
from cola.widgets.filelist import FileWidget
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
