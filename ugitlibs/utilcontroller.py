#!/usr/bin/env python
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QFont
import utils
import qtutils
from qobserver import QObserver
from views import BranchGUI
from views import CommitGUI
from views import OptionsGUI

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
		self.connect(view.commitList, 'itemSelectionChanged()',
				self.commit_sha1_selected )

		if model.has_param('global.ugit.fontdiff'):
			font = model.get_param('global.ugit.fontdiff')
			if font:
				qf = QFont()
				qf.fromString(font)
				self.view.commitText.setFont(qf)

	def select_commits(self):
		summaries = self.model.get_summaries()
		if not summaries:
			msg = self.tr('No commits exist in this branch.')
			self.show_output(msg)
			return []
		qtutils.set_items(self.view.commitList, summaries)
		self.view.show()
		if self.view.exec_() != QDialog.Accepted:
			return []
		revs = self.model.get_revisions()
		list_widget = self.view.commitList
		return qtutils.get_selection_list(list_widget, revs)

	def commit_sha1_selected(self):
		row, selected = qtutils.get_selected_row(self.view.commitList)
		if not selected:
			self.view.commitText.setText('')
			self.view.revisionLine.setText('')
			return

		# Get the sha1 and put it in the revision line
		sha1 = self.model.get_revision_sha1(row)
		self.view.revisionLine.setText(sha1)
		self.view.revisionLine.selectAll()

		# Lookup the sha1's commit
		commit_diff = self.model.get_commit_diff(sha1)
		self.view.commitText.setText(commit_diff)

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
			'local.user.email': 'localEmailText',
			'global.user.email': 'globalEmailText',

			'local.user.name':  'localNameText',
			'global.user.name':  'globalNameText',

			'local.merge.summary': 'localSummarizeCheckBox',
			'global.merge.summary': 'globalSummarizeCheckBox',

			'local.merge.diffstat': 'localShowDiffstatCheckBox',
			'global.merge.diffstat': 'globalShowDiffstatCheckBox',

			'local.gui.diffcontext': 'localDiffContextSpin',
			'global.gui.diffcontext': 'globalDiffContextSpin',

			'local.merge.verbosity': 'localVerbositySpin',
			'global.merge.verbosity': 'globalVerbositySpin',

			'global.ugit.fontdiff.size': 'diffFontSpin',
			'global.ugit.fontdiff':  'diffFontCombo',

			'global.ugit.fontui.size': 'mainFontSpin',
			'global.ugit.fontui': 'mainFontCombo',
		}

		for m,v in model_to_view.iteritems():
			self.model_to_view(m,v)

		self.add_signals('textChanged(const QString&)',
				view.localNameText,
				view.globalNameText,
				view.localEmailText,
				view.globalEmailText)

		self.add_signals('stateChanged(int)',
				view.localSummarizeCheckBox,
				view.globalSummarizeCheckBox,
				view.localShowDiffstatCheckBox,
				view.globalShowDiffstatCheckBox)

		self.add_signals('valueChanged(int)',
				view.mainFontSpin,
				view.diffFontSpin,
				view.localDiffContextSpin,
				view.globalDiffContextSpin,
				view.localVerbositySpin,
				view.globalVerbositySpin)
	
		self.add_signals('currentFontChanged(const QFont&)',
				view.mainFontCombo,
				view.diffFontCombo)

		self.add_signals('released()',
				view.saveButton,
				view.cancelButton)

		self.add_actions('global.ugit.fontdiff.size', self.update_size)
		self.add_actions('global.ugit.fontui.size', self.update_size)
		self.add_actions('global.ugit.fontdiff', self.update_font)
		self.add_actions('global.ugit.fontui', self.update_font)

		self.add_callbacks(saveButton = self.save_settings)
		self.add_callbacks(cancelButton = self.restore_settings)

		view.localGroupBox.setTitle(
			unicode(self.tr('%s Repository')) % model.get_project())

		self.refresh_view()
		self.backup_model = self.model.clone()

	def refresh_view(self):

		font = self.model.get_param('global.ugit.fontui')
		if font:
			size = int(font.split(',')[1])
			self.view.mainFontSpin.setValue(size)
			self.model.set_param('global.ugit.fontui.size', size)
			ui_font = QFont()
			ui_font.fromString(font)
			self.view.mainFontCombo.setCurrentFont(ui_font)

		font = self.model.get_param('global.ugit.fontdiff')
		if font:
			size = int(font.split(',')[1])
			self.view.diffFontSpin.setValue(size)
			self.model.set_param('global.ugit.fontdiff.size', size)
			diff_font = QFont()
			diff_font.fromString(font)
			self.view.diffFontCombo.setCurrentFont(diff_font)

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
		combo = self.view.mainFontCombo
		param = 'global.ugit.fontui'
		default = str(combo.currentFont().toString())
		self.model.apply_font_size(param, default)

		combo = self.view.diffFontCombo
		param = 'global.ugit.fontdiff'
		default = str(combo.currentFont().toString())
		self.model.apply_font_size(param, default)
		self.tell_parent_model()
