#!/usr/bin/env python
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QFont
import utils
import qtutils
from qobserver import QObserver
from views import BranchGUI
from views import CommitGUI
from views import OptionsGUI
from views import OutputGUI

def choose_branch(title, parent, branches):
	dlg = BranchGUI(parent,branches)
	dlg.setWindowTitle(dlg.tr(title))
	return dlg.get_selected()

def select_commits(model, parent, revs, summaries):
	'''Use the CommitBrowser to select commits from a list.'''
	model = model.clone()
	model.set_revisions(revs)
	model.set_summaries(summaries)
	view = CommitGUI(parent)
	ctl = SelectCommitsController(model, view)
	return ctl.select_commits()

class SelectCommitsController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self, model, view)
		self.connect(view.commit_list, 'itemSelectionChanged()',
				self.commit_sha1_selected )

		if model.has_param('global.ugit.fontdiff'):
			font = model.get_param('global.ugit.fontdiff')
			if font:
				qf = QFont()
				qf.fromString(font)
				self.view.commit_text.setFont(qf)

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

	def commit_sha1_selected(self):
		row, selected = qtutils.get_selected_row(self.view.commit_list)
		if not selected:
			self.view.commit_text.setText('')
			self.view.revision_line.setText('')
			return

		# Get the sha1 and put it in the revision line
		sha1 = self.model.get_revision_sha1(row)
		self.view.revision_line.setText(sha1)
		self.view.revision_line.selectAll()

		# Lookup the sha1's commit
		commit_diff = self.model.get_commit_diff(sha1)
		self.view.commit_text.setText(commit_diff)

		# Copy the sha1 into the clipboard
		qtutils.set_clipboard(sha1)

def update_options(model, parent):
	view = OptionsGUI(parent)
	ctl = OptionsController(model,view)
	view.show()
	return view.exec_() == QDialog.Accepted

class OptionsController(QObserver):
	def __init__(self,model,view):

		# used for telling about interactive font changes
		self.original_model = model
		model = model.clone()

		QObserver.__init__(self,model,view)

		model_to_view = {
			'local.user.email': 'local_email_line',
			'global.user.email': 'global_email_line',

			'local.user.name':  'local_name_line',
			'global.user.name':  'global_name_line',

			'local.merge.summary': 'local_summary_checkbox',
			'global.merge.summary': 'global_summary_checkbox',

			'local.merge.diffstat': 'local_diffstat_checkbox',
			'global.merge.diffstat': 'global_diffstat_checkbox',

			'local.gui.diffcontext': 'local_diffcontext_spinbox',
			'global.gui.diffcontext': 'global_diffcontext_spinbox',

			'local.merge.verbosity': 'local_verbosity_spinbox',
			'global.merge.verbosity': 'global_verbosity_spinbox',

			'global.ugit.fontdiff.size': 'diff_font_spinbox',
			'global.ugit.fontdiff':  'diff_font_combo',

			'global.ugit.fontui.size': 'main_font_spinbox',
			'global.ugit.fontui': 'main_font_combo',
		}

		for m,v in model_to_view.iteritems():
			self.model_to_view(m,v)

		self.add_signals('textChanged(const QString&)',
				view.local_name_line,
				view.global_name_line,
				view.local_email_line,
				view.global_email_line)

		self.add_signals('stateChanged(int)',
				view.local_summary_checkbox,
				view.global_summary_checkbox,
				view.local_diffstat_checkbox,
				view.global_diffstat_checkbox)

		self.add_signals('valueChanged(int)',
				view.main_font_spinbox,
				view.diff_font_spinbox,
				view.local_diffcontext_spinbox,
				view.global_diffcontext_spinbox,
				view.local_verbosity_spinbox,
				view.global_verbosity_spinbox)
	
		self.add_signals('currentFontChanged(const QFont&)',
				view.main_font_combo,
				view.diff_font_combo)

		self.add_signals('released()',
				view.save_button,
				view.cancel_button)

		self.add_actions('global.ugit.fontdiff.size', self.update_size)
		self.add_actions('global.ugit.fontui.size', self.update_size)
		self.add_actions('global.ugit.fontdiff', self.update_font)
		self.add_actions('global.ugit.fontui', self.update_font)

		self.add_callbacks(save_button = self.save_settings)
		self.add_callbacks(cancel_button = self.restore_settings)

		view.local_groupbox.setTitle(
			unicode(self.tr('%s Repository')) % model.get_project())

		self.refresh_view()
		self.backup_model = self.model.clone()

	def refresh_view(self):

		font = self.model.get_param('global.ugit.fontui')
		if font:
			size = int(font.split(',')[1])
			self.view.main_font_spinbox.setValue(size)
			self.model.set_param('global.ugit.fontui.size', size)
			ui_font = QFont()
			ui_font.fromString(font)
			self.view.main_font_combo.setCurrentFont(ui_font)

		font = self.model.get_param('global.ugit.fontdiff')
		if font:
			size = int(font.split(',')[1])
			self.view.diff_font_spinbox.setValue(size)
			self.model.set_param('global.ugit.fontdiff.size', size)
			diff_font = QFont()
			diff_font.fromString(font)
			self.view.diff_font_combo.setCurrentFont(diff_font)

		QObserver.refresh_view(self)


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

	def restore_settings(self):
		params = self.backup_model.get_config_params()
		self.model.copy_params(self.backup_model, params)
		self.tell_parent_model()
		self.view.reject()

	def tell_parent_model(self):
		for param in (
				'global.ugit.fontdiff',
				'global.ugit.fontui',
				'global.ugit.fontdiff.size',
				'global.ugit.fontui.size'):
			self.original_model.set_param(param,
					self.model.get_param(param))

	def update_font(self, *rest):
		self.tell_parent_model()
		return

	def update_size(self, *rest):
		combo = self.view.main_font_combo
		param = 'global.ugit.fontui'
		default = str(combo.currentFont().toString())
		self.model.apply_font_size(param, default)

		combo = self.view.diff_font_combo
		param = 'global.ugit.fontdiff'
		default = str(combo.currentFont().toString())
		self.model.apply_font_size(param, default)
		self.tell_parent_model()

def log_window(model, parent):
	model = model.clone()
	view = OutputGUI(parent)
	ctl = LogWindowController(model,view)
	return view

class LogWindowController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self, model, view)

		self.model_to_view('search_text', 'search_line')
		self.add_signals('textChanged(const QString&)',
				self.view.search_line)

		self.connect(self.view.clear_button, 'released()', self.clear)
		self.connect(self.view.next_button, 'released()', self.next)
		self.connect(self.view.prev_button, 'released()', self.prev)
		self.connect(self.view.output_text, 'cursorPositionChanged()',
				self.cursor_position_changed)

		self.reset()

	def clear(self):
		self.view.output_text.clear()
		self.reset()

	def reset(self):
		self.search_offset = 0

	def next(self):
		text = self.model.get_search_text()
		if not text: return
		output = str(self.view.output_text.toPlainText())
		if self.search_offset + len(text) > len(output):
			if qtutils.question(
				self.view,
				unicode(self.tr("%s not found")) % text,
				unicode(self.tr("Could not find '%s'.\n"
						"Search from the beginning?"
						)) % text):
				self.search_offset = 0

		find_in = output[self.search_offset:]
		try:
			index = find_in.index(text)
		except:
			self.search_offset = 0
			if qtutils.question(
				self.view,
				unicode(self.tr("%s not found")) % text,
				unicode(self.tr("Could not find '%s'.\n"
						"Search from the beginning?"
						)) % text):
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
		text = self.model.get_search_text()
		if not text: return
		output = str(self.view.output_text.toPlainText())
		if self.search_offset == 0:
			self.search_offset = len(output)

		find_in = output[:self.search_offset]
		try:
			offset = find_in.rindex(text)
		except:
			self.search_offset = 0
			if qtutils.question(
				self.view,
				unicode(self.tr("%s not found")) % text,
				unicode(self.tr("Could not find '%s'.\n"
						"Search from the end?"
						)) % text):
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
