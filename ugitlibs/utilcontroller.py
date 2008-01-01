#!/usr/bin/env python
from PyQt4.QtGui import QDialog
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
	model = model.clone(init=False)
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
		# used when "cancel" is clicked
		self.backup_model = model.clone(init=False)

		model = model.clone(init=False)

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
				view.localSummarizeCheckBox)

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

		self.add_actions('global.ugit.fontdiff.size', self.update_all_sizes)
		self.add_actions('global.ugit.fontui.size', self.update_all_sizes)
		self.add_actions('global.ugit.fontdiff', self.update_all_fonts)
		self.add_actions('global.ugit.fontui', self.update_all_fonts)

		self.add_callbacks(saveButton = self.save_settings)
		self.add_callbacks(cancelButton = self.restore_settings)

		view.localGroupBox.setTitle(
			unicode(self.tr('%s Repository')) % model.get_project())

		self.refresh_view()

	def save_settings(self):
		self.tell_parent_model()

	def restore_settings(self):
		print self.model
		self.view.reject()

	def tell_parent_model(self):
		self.original_model.set_param('global.ugit.fontdiff',
				self.model.get_param('global.ugit.fontdiff'))
		self.original_model.set_param('global.ugit.fontui',
				self.model.get_param('global.ugit.fontui'))

	def update_all_fonts(self, *rest):
		if self.sender().objectName() == 'mainFontCombo':
			combo = self.view.mainFontCombo
			spin = self.view.mainFontSpin
			param = 'global.ugit.fontui.size'
		else:
			combo = self.view.diffFontCombo
			spin = self.view.diffFontSpin
			param = 'global.ugit.fontdiff.size'
		self.update_font(combo, spin, param)

	def update_font(self, combo, spin, param):
		new_font = str(combo.currentFont().toString())
		new_size = int(new_font.split(',')[1])
		self.model.set_param(param, new_size)
		spin.setValue(new_size)
		self.tell_parent_model()

	def update_all_sizes(self, *rest):
		if self.sender().objectName() == 'mainFontSpin':
			comboui = self.view.mainFontCombo
			paramui = 'global.ugit.fontui'
		else:
			comboui = self.view.diffFontCombo
			paramui = 'global.ugit.fontdiff'

		self.update_size(comboui, paramui)
		self.tell_parent_model()

	def update_size(self, combo, param):

		old_font = self.model.get_param(param)
		if not old_font:
			old_font = str(combo.currentFont().toString())

		size = self.model.get_param(param+'.size')
		props = old_font.split(',')
		props[1] = str(size)
		new_font = ','.join(props)

		self.model.set_param(param, new_font)
