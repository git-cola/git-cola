#!/usr/bin/env python
"""This module provides utility controllers.
"""


import os
import time
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QFont
from PyQt4.QtGui import QMenu
from PyQt4 import QtGui

from cola import utils
from cola import qtutils
from cola.model import Model
from cola.views import ListView
from cola.views import ComboView
from cola.views import CommitView
from cola.views import OptionsView
from cola.views import LogView
from cola.qobserver import QObserver
from createbranch import create_new_branch

def set_diff_font(model, widget):
    if model.has_param('global_cola_fontdiff'):
        font = model.get_param('global_cola_fontdiff')
        if not font:
            return
        qf = QFont()
        qf.fromString(font)
        widget.setFont(qf)

def choose_from_combo(title, parent, items):
    return ComboView(parent,
                     title=title,
                     items=items).get_selected()

def choose_from_list(title, parent, items=[], dblclick=None):
    return ListView(parent,
                    title=title,
                    items=items,
                    dblclick=dblclick).get_selected()

#+-------------------------------------------------------------
def select_commits(model, parent, title, revs, summaries):
    """Use the CommitView to select commits from a list."""
    original_model = model
    model = model.clone()
    model.set_revisions(revs)
    model.set_summaries(summaries)
    view = CommitView(parent, title)
    ctl = SelectCommitsController(model, view)
    ctl.original_model = original_model
    return ctl.select_commits()

class SelectCommitsController(QObserver):
    def __init__(self, model, view):
        QObserver.__init__(self, model, view)
        set_diff_font(model, view.commit_text)
        self.connect(view.commit_list,
                     'itemSelectionChanged()',
                     self.commit_sha1_selected)
        view.commit_list.contextMenuEvent = self.context_menu_event

    def select_commits(self):
        summaries = self.model.get_summaries()
        if not summaries:
            msg = self.tr('No commits exist in this branch.')
            qtutils.show_output(msg)
            return []
        qtutils.set_items(self.view.commit_list, summaries)
        self.view.show()
        if self.view.exec_() != QDialog.Accepted:
            return []
        revs = self.model.get_revisions()
        list_widget = self.view.commit_list
        return qtutils.get_selection_list(list_widget, revs)

    def context_menu_event(self, event):
        menu = QMenu(self.view);
        menu.addAction(self.tr('Checkout'), self.checkout_commit)
        menu.addAction(self.tr('Create Branch here'), self.create_branch_at)
        menu.addAction(self.tr('Cherry Pick'), self.cherry_pick)
        menu.exec_(self.view.commit_list.mapToGlobal(event.pos()))

    def checkout_commit(self):
        row, selected = qtutils.get_selected_row(self.view.commit_list)
        if not selected:
            return
        sha1 = self.model.get_revision_sha1(row)
        out = self.model.git.checkout(sha1, with_stderr=True)
        qtutils.show_output(out)

    def create_branch_at(self):
        row, selected = qtutils.get_selected_row(self.view.commit_list)
        if not selected:
            return
        create_new_branch(self.original_model, self.view,
                          revision=self.model.get_revision_sha1(row))

    def cherry_pick(self):
        row, selected = qtutils.get_selected_row(self.view.commit_list)
        if not selected:
            return
        sha1 = self.model.get_revision_sha1(row)
        out = self.model.git.cherry_pick(sha1, with_stderr=True)
        qtutils.show_output(out)

    def commit_sha1_selected(self):
        row, selected = qtutils.get_selected_row(self.view.commit_list)
        if not selected:
            self.view.commit_text.setText('')
            self.view.revision.setText('')
            return
        # Get the sha1 and put it in the revision line
        sha1 = self.model.get_revision_sha1(row)
        self.view.revision.setText(sha1)
        self.view.revision.selectAll()

        # Lookup the sha1's commit
        commit_diff = self.model.get_commit_diff(sha1)
        self.view.commit_text.setText(commit_diff)

        # Copy the sha1 into the clipboard
        qtutils.set_clipboard(sha1)

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#+ The Options GUI Controller
def update_options(model, parent):
    view = OptionsView(parent)
    ctl = OptionsController(model,view)
    view.show()
    return view.exec_() == QDialog.Accepted

class OptionsController(QObserver):
    """ASSUMPTIONS:
    This controller assumes that the view's widgets are named
    the same as the model parameters."""

    def __init__(self, model, view):
        # used for telling about interactive font changes
        self.original_model = model
        model = model.clone()
        QObserver.__init__(self, model, view)
        self.add_observables('local_user_email',
                             'local_user_name',
                             'local_merge_summary',
                             'local_merge_diffstat',
                             'local_merge_verbosity',
                             'local_gui_diffcontext',
                             'global_user_email',
                             'global_user_name',
                             'global_merge_keepbackup',
                             'global_merge_summary',
                             'global_merge_diffstat',
                             'global_merge_verbosity',
                             'global_gui_editor',
                             'global_merge_tool',
                             'global_gui_diffcontext',
                             'global_gui_historybrowser',
                             'global_cola_fontdiff_size',
                             'global_cola_fontdiff',
                             'global_cola_fontui_size',
                             'global_cola_fontui',
                             'global_cola_savewindowsettings',
                             'global_cola_tabwidth',
                             )
        self.add_actions(global_cola_fontdiff = self.tell_parent_model)
        self.add_actions(global_cola_fontui = self.tell_parent_model)
        self.add_callbacks(save_button = self.save_settings)
        self.add_callbacks(global_cola_fontdiff_size = self.update_size)
        self.add_callbacks(global_cola_fontui_size = self.update_size)
        self.connect(self.view, 'rejected()', self.restore_settings)

        self.refresh_view()
        self.backup_model = self.model.clone()

    def refresh_view(self):
        font = self.model.get_cola_config('fontui')
        if font:
            fontui = QFont()
            fontui.fromString(font)
            self.view.global_cola_fontui.setCurrentFont(fontui)

        font = self.model.get_cola_config('fontdiff')
        if font:
            fontdiff = QFont()
            fontdiff.fromString(font)
            self.view.global_cola_fontdiff.setCurrentFont(fontdiff)

        self.view.local_groupbox.setTitle(unicode(self.tr('%s Repository'))
                                          % self.model.get_project())
        QObserver.refresh_view(self)

    # save button
    def save_settings(self):
        params_to_save = []
        params = self.model.get_config_params()
        for param in params:
            value = self.model.get_param(param)
            backup = self.backup_model.get_param(param)
            if value != backup:
                params_to_save.append(param)
        for param in params_to_save:
            self.model.save_config_param(param)

        self.original_model.copy_params(self.model, params_to_save)
        self.view.done(QDialog.Accepted)

    # cancel button -> undo changes
    def restore_settings(self):
        params = self.backup_model.get_config_params()
        self.model.copy_params(self.backup_model, params)
        self.tell_parent_model()

    def tell_parent_model(self,*rest):
        params= ('global_cola_fontdiff',
                 'global_cola_fontui',
                 'global_cola_fontdiff_size',
                 'global_cola_fontui_size',
                 'global_cola_savewindowsettings',
                 'global_cola_tabwidth',
                 )
        for param in params:
            self.original_model.set_param(
                param, self.model.get_param(param))

    def update_size(self, *rest):
        combo = self.view.global_cola_fontui
        param = str(combo.objectName())
        default = str(combo.currentFont().toString())
        self.model.apply_font_size(param, default)

        combo = self.view.global_cola_fontdiff
        param = str(combo.objectName())
        default = str(combo.currentFont().toString())
        self.model.apply_font_size(param, default)

        self.tell_parent_model()

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#+ The Log GUI Controller
def logger():
    model = Model(search_text = '')
    view = LogView(None)
    ctl = LogController(model,view)
    return view

class LogController(QObserver):
    def __init__(self, model, view):
        QObserver.__init__(self, model, view)
        self.add_observables('search_text')
        self.add_actions(search_text = self.insta_search)
        self.add_callbacks(clear_button = self.clear,
                           next_button = self.next,
                           prev_button = self.prev)
        self.connect(self.view.output_text,
                     'cursorPositionChanged()',
                     self.cursor_position_changed)
        self.search_offset = 0

    def insta_search(self,*rest):
        self.search_offset = 0
        txt = self.model.get_search_text().lower()
        if len(txt.strip()):
            self.next()
        else:
            cursor = self.view.output_text.textCursor()
            cursor.clearSelection()
            self.view.output_text.setTextCursor(cursor)

    def clear(self):
        self.view.output_text.clear()
        self.search_offset = 0

    def next(self):
        text = self.model.get_search_text().lower().strip()
        if not text:
            return
        output = str(self.view.output_text.toPlainText())
        if self.search_offset + len(text) > len(output):
            title = unicode(self.tr('%s not found')) % text
            question = unicode(self.tr("Could not find '%s'.\n"
                                       'Search from the beginning?')) % text
            if qtutils.question(self.view, title, question, default=False):
                self.search_offset = 0
            else:
                return

        find_in = output[self.search_offset:].lower()
        try:
            index = find_in.index(text)
        except:
            self.search_offset = 0
            title = unicode(self.tr("%s not found")) % text
            question = unicode(self.tr("Could not find '%s'.\n"
                                       'Search from the beginning?')) % text
            if qtutils.question(self.view, title, default=False):
                self.next()
            return
        cursor = self.view.output_text.textCursor()
        offset = self.search_offset + index
        new_offset = offset + len(text)

        cursor.setPosition(offset)
        cursor.setPosition(new_offset, cursor.KeepAnchor)

        self.view.output_text.setTextCursor(cursor)
        self.search_offset = new_offset

    def prev(self):
        text = self.model.get_search_text().lower().strip()
        if not text:
            return
        output = str(self.view.output_text.toPlainText())
        if self.search_offset == 0:
            self.search_offset = len(output)

        find_in = output[:self.search_offset].lower()
        try:
            offset = find_in.rindex(text)
        except:
            self.search_offset = 0
            title = unicode(self.tr('%s not found')) % text
            question = unicode(self.tr("Could not find '%s'.\n"
                                       'Search from the end?')) % text
            if qtutils.question(self.view, title, question):
                self.prev()
            return
        cursor = self.view.output_text.textCursor()
        new_offset = offset + len(text)

        cursor.setPosition(offset)
        cursor.setPosition(new_offset, cursor.KeepAnchor)

        self.view.output_text.setTextCursor(cursor)
        self.search_offset = offset

    def cursor_position_changed(self):
        cursor = self.view.output_text.textCursor()
        self.search_offset = cursor.selectionStart()
