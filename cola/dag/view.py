import collections
import math
import sys
import time
import urllib

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtNetwork
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import difftool
from cola import gitcmds
from cola import observable
from cola import qtutils
from cola import resources
from cola import signals
from cola.compat import hashlib
from cola.dag.model import archive
from cola.dag.model import RepoReader
from cola.prefs import diff_font
from cola.qt import DiffSyntaxHighlighter
from cola.qt import GitLogLineEdit
from cola.widgets import defs
from cola.widgets import standard
from cola.widgets.createbranch import create_new_branch
from cola.widgets.createtag import create_tag
from cola.widgets.archive import GitArchiveDialog
from cola.widgets.browse import BrowseDialog


class GravatarLabel(QtGui.QLabel):
    def __init__(self, parent=None):
        super(GravatarLabel, self).__init__(parent)

        self.email = None
        self.response = None
        self.timeout = 0
        self.imgsize = 48

        self.network = QtNetwork.QNetworkAccessManager()
        self.connect(self.network,
                     SIGNAL('finished(QNetworkReply*)'),
                     self.network_finished)

    def url_for_email(self, email):
        email_hash = hashlib.md5(email).hexdigest()
        default_url = 'http://git-cola.github.com/images/git-64x64.jpg'
        encoded_url = urllib.quote(default_url, '')
        query = '?s=%d&d=%s' % (self.imgsize, encoded_url)
        url = 'http://gravatar.com/avatar/' + email_hash + query
        return url

    def get_email(self, email):
        if (self.timeout > 0 and
                (int(time.time()) - self.timeout) < (5 * 60)):
            self.set_pixmap_from_response()
            return
        if email == self.email and self.response is not None:
            self.set_pixmap_from_response()
            return
        self.email = email
        self.get(self.url_for_email(email))

    def get(self, url):
        self.network.get(QtNetwork.QNetworkRequest(QtCore.QUrl(url)))

    def default_pixmap_as_bytes(self):
        xres = self.imgsize
        pixmap = QtGui.QPixmap(resources.icon('git.svg'))
        pixmap = pixmap.scaledToHeight(xres, Qt.SmoothTransformation)
        byte_array = QtCore.QByteArray()
        buf = QtCore.QBuffer(byte_array)
        buf.open(QtCore.QIODevice.WriteOnly)
        pixmap.save(buf, 'PNG')
        buf.close()
        return byte_array

    def network_finished(self, reply):
        header = QtCore.QByteArray('Location')
        raw_header = reply.rawHeader(header)
        if raw_header:
            location = unicode(QtCore.QString(raw_header)).strip()
            request_location = unicode(self.url_for_email(self.email))
            relocated = location != request_location
        else:
            relocated = False

        if reply.error() == QtNetwork.QNetworkReply.NoError:
            if relocated:
                # We could do get_url(urllib.unquote(location)) to
                # download the default image.
                # Save bandwidth by using a pixmap.
                self.response = self.default_pixmap_as_bytes()
            else:
                self.response = reply.readAll()
            self.timeout = 0
        else:
            self.response = self.default_pixmap_as_bytes()
            self.timeout = int(time.time())
        self.set_pixmap_from_response()

    def set_pixmap_from_response(self):
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(self.response)
        self.setPixmap(pixmap)


class TextLabel(QtGui.QLabel):
    def __init__(self, parent=None):
        super(TextLabel, self).__init__(parent)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse |
                                     Qt.LinksAccessibleByMouse)
        self.setOpenExternalLinks(True)
        self._text = ''
        self._elide = False

    def elide(self):
        self._elide = True

    def setText(self, text):
        if self._elide:
            self._text = text
            width = self.width()
            fm = QtGui.QFontMetrics(self.font())
            text = fm.elidedText(text, Qt.ElideRight, width-2)
        super(TextLabel, self).setText(text)

    def resizeEvent(self, event):
        super(TextLabel, self).resizeEvent(event)
        if self._elide:
            self.setText(self._text)


class DiffWidget(QtGui.QWidget):
    def __init__(self, notifier, parent):
        QtGui.QWidget.__init__(self, parent)

        author_font = QtGui.QFont(self.font())
        author_font.setPointSize(int(author_font.pointSize() * 1.1))

        summary_font = QtGui.QFont(author_font)
        summary_font.setWeight(QtGui.QFont.Bold)

        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Minimum)

        self.gravatar_label = GravatarLabel()

        self.author_label = TextLabel()
        self.author_label.setTextFormat(Qt.RichText)
        self.author_label.setFont(author_font)
        self.author_label.setSizePolicy(policy)
        self.author_label.setAlignment(Qt.AlignBottom)

        self.summary_label = TextLabel()
        self.summary_label.setTextFormat(Qt.PlainText)
        self.summary_label.setFont(summary_font)
        self.summary_label.setSizePolicy(policy)
        self.summary_label.setAlignment(Qt.AlignTop)
        self.summary_label.elide()

        self.diff = QtGui.QTextEdit()
        self.diff.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.diff.setReadOnly(True)
        self.diff.setFont(diff_font())
        self.highlighter = DiffSyntaxHighlighter(self.diff.document())

        self.info_layout = QtGui.QVBoxLayout()
        self.info_layout.setMargin(0)
        self.info_layout.setSpacing(0)
        self.info_layout.addWidget(self.author_label)
        self.info_layout.addWidget(self.summary_label)

        self.logo_layout = QtGui.QHBoxLayout()
        self.logo_layout.setContentsMargins(defs.margin, 0, defs.margin, 0)
        self.logo_layout.setSpacing(defs.button_spacing)
        self.logo_layout.addWidget(self.gravatar_label)
        self.logo_layout.addLayout(self.info_layout)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(0)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addLayout(self.logo_layout)
        self.main_layout.addWidget(self.diff)
        self.setLayout(self.main_layout)

        sig = signals.commits_selected
        notifier.add_observer(sig, self.commits_selected)

    def commits_selected(self, commits):
        if len(commits) != 1:
            return
        commit = commits[0]
        sha1 = commit.sha1
        self.diff.setText(gitcmds.diff_info(sha1))

        email = commit.email or ''
        summary = commit.summary or ''
        author = commit.author or ''

        template_args = {
                'author': author,
                'email': email,
                'summary': summary
        }

        self.gravatar_label.get_email(email)
        author_text = ("""%(author)s &lt;"""
                       """<a href="mailto:%(email)s">"""
                       """%(email)s</a>&gt;"""
                       % template_args)

        self.author_label.setText(author_text)
        self.summary_label.setText(summary)


class ViewerMixin(object):
    def __init__(self):
        self.selected = None
        self.clicked = None
        self.menu_actions = self.context_menu_actions()

    def diff_selected_this(self):
        clicked_sha1 = self.clicked.sha1
        selected_sha1 = self.selected.sha1
        self.emit(SIGNAL('diff_commits'), selected_sha1, clicked_sha1)

    def diff_this_selected(self):
        clicked_sha1 = self.clicked.sha1
        selected_sha1 = self.selected.sha1
        self.emit(SIGNAL('diff_commits'), clicked_sha1, selected_sha1)

    def cherry_pick(self):
        sha1 = self.clicked.sha1
        cola.notifier().broadcast(signals.cherry_pick, [sha1])

    def copy_to_clipboard(self):
        clicked_sha1 = self.clicked.sha1
        qtutils.set_clipboard(clicked_sha1)

    def create_branch(self):
        sha1 = self.clicked.sha1
        create_new_branch(revision=sha1)

    def create_tag(self):
        sha1 = self.clicked.sha1
        create_tag(revision=sha1)

    def create_tarball(self):
        ref = self.clicked.sha1
        shortref = ref[:7]
        GitArchiveDialog.save(ref, shortref, self)

    def save_blob_dialog(self):
        return BrowseDialog.browse(self.clicked.sha1)

    def context_menu_actions(self):
        return {
        'diff_this_selected':
            qtutils.add_action(self, 'Diff this -> selected',
                               self.diff_this_selected),
        'diff_selected_this':
            qtutils.add_action(self, 'Diff selected -> this',
                               self.diff_selected_this),
        'create_branch':
            qtutils.add_action(self, 'Create Branch',
                               self.create_branch),
        'create_patch':
            qtutils.add_action(self, 'Create Patch',
                               self.create_patch),
        'create_tag':
            qtutils.add_action(self, 'Create Tag',
                               self.create_tag),
        'create_tarball':
            qtutils.add_action(self, 'Save As Tarball/Zip...',
                               self.create_tarball),
        'cherry_pick':
            qtutils.add_action(self, 'Cherry Pick',
                               self.cherry_pick),
        'save_blob':
            qtutils.add_action(self, 'Grab File...',
                               self.save_blob_dialog),
        'copy':
            qtutils.add_action(self, 'Copy SHA-1',
                               self.copy_to_clipboard,
                               QtGui.QKeySequence.Copy),
        }

    def update_menu_actions(self, event):
        clicked = self.itemAt(event.pos())
        selected_items = self.selectedItems()
        has_single_selection = len(selected_items) == 1

        has_selection = bool(selected_items)
        can_diff = bool(clicked and has_single_selection and
                        clicked is not selected_items[0])

        self.clicked = clicked.commit
        if can_diff:
            self.selected = selected_items[0].commit
        else:
            self.selected = None

        self.menu_actions['diff_this_selected'].setEnabled(can_diff)
        self.menu_actions['diff_selected_this'].setEnabled(can_diff)

        self.menu_actions['create_branch'].setEnabled(has_single_selection)
        self.menu_actions['create_tag'].setEnabled(has_single_selection)

        self.menu_actions['cherry_pick'].setEnabled(has_single_selection)
        self.menu_actions['create_patch'].setEnabled(has_selection)
        self.menu_actions['create_tarball'].setEnabled(has_single_selection)

        self.menu_actions['save_blob'].setEnabled(has_single_selection)
        self.menu_actions['copy'].setEnabled(has_single_selection)

    def context_menu_event(self, event):
        self.update_menu_actions(event)
        menu = QtGui.QMenu(self)
        menu.addAction(self.menu_actions['diff_this_selected'])
        menu.addAction(self.menu_actions['diff_selected_this'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['create_branch'])
        menu.addAction(self.menu_actions['create_tag'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['cherry_pick'])
        menu.addAction(self.menu_actions['create_patch'])
        menu.addAction(self.menu_actions['create_tarball'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['save_blob'])
        menu.addAction(self.menu_actions['copy'])
        menu.exec_(self.mapToGlobal(event.pos()))


class CommitTreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, commit, parent=None):
        QtGui.QListWidgetItem.__init__(self, parent)
        self.commit = commit
        self.setText(0, commit.summary)
        self.setText(1, commit.author)
        self.setText(2, commit.authdate)


class CommitTreeWidget(QtGui.QTreeWidget, ViewerMixin):
    def __init__(self, notifier, parent):
        QtGui.QTreeWidget.__init__(self, parent)
        ViewerMixin.__init__(self)

        self.setSelectionMode(self.ContiguousSelection)
        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(False)
        self.setHeaderLabels(['Summary', 'Author', 'Age'])

        self.sha1map = {}
        self.notifier = notifier
        self.selecting = False
        self.commits = []

        self.action_up = qtutils.add_action(self, 'Go Up', self.go_up,
                                            QtCore.Qt.Key_K)

        self.action_down = qtutils.add_action(self, 'Go Down', self.go_down,
                                              QtCore.Qt.Key_J)

        sig = signals.commits_selected
        notifier.add_observer(sig, self.commits_selected)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.selection_changed)

    def contextMenuEvent(self, event):
        self.context_menu_event(event)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.RightButton:
            event.accept()
            return
        if event.modifiers() == QtCore.Qt.MetaModifier:
            event.accept()
            return
        super(CommitTreeWidget, self).mousePressEvent(event)

    def go_up(self):
        self.goto(self.itemAbove)

    def go_down(self):
        self.goto(self.itemBelow)

    def goto(self, finder):
        items = self.selectedItems()
        item = items and items[0] or None
        if item is None:
            return
        found = finder(item)
        if found:
            self.select([found.commit.sha1], block_signals=False)

    def set_selecting(self, selecting):
        self.selecting = selecting

    def selection_changed(self):
        items = self.selectedItems()
        if not items:
            return
        self.set_selecting(True)
        sig = signals.commits_selected
        self.notifier.notify_observers(sig, [i.commit for i in items])
        self.set_selecting(False)

    def commits_selected(self, commits):
        if self.selecting:
            return
        self.clicked = commits and commits[0] or None
        self.select([commit.sha1 for commit in commits])

    def select(self, sha1s, block_signals=True):
        self.clearSelection()
        for sha1 in sha1s:
            try:
                item = self.sha1map[sha1]
            except KeyError:
                continue
            block = self.blockSignals(block_signals)
            self.scrollToItem(item)
            item.setSelected(True)
            self.blockSignals(block)

    def adjust_columns(self):
        width = self.width()-20
        zero = width*2/3
        onetwo = width/6
        self.setColumnWidth(0, zero)
        self.setColumnWidth(1, onetwo)
        self.setColumnWidth(2, onetwo)

    def clear(self):
        QtGui.QTreeWidget.clear(self)
        self.sha1map.clear()
        self.commits = []

    def add_commits(self, commits):
        self.commits.extend(commits)
        items = []
        for c in reversed(commits):
            item = CommitTreeWidgetItem(c)
            items.append(item)
            self.sha1map[c.sha1] = item
            for tag in c.tags:
                self.sha1map[tag] = item
        self.insertTopLevelItems(0, items)

    def create_patch(self):
        items = self.selectedItems()
        if not items:
            return
        items.reverse()
        sha1s = [item.commit.sha1 for item in items]
        all_sha1s = [c.sha1 for c in self.commits]
        cola.notifier().broadcast(signals.format_patch, sha1s, all_sha1s)


class DAGView(standard.Widget):
    """The git-dag widget."""

    def __init__(self, model, dag, parent=None, args=None):
        super(DAGView, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_MacMetalStyle)
        self.setMinimumSize(1, 1)

        # change when widgets are added/removed
        self.widget_version = 1
        self.model = model
        self.dag = dag

        self.commits = {}
        self.commit_list = []

        self.old_count = None
        self.old_ref = None

        self.revtext = GitLogLineEdit(parent=self)

        self.maxresults = QtGui.QSpinBox()
        self.maxresults.setMinimum(1)
        self.maxresults.setMaximum(99999)
        self.maxresults.setPrefix('git log -')
        self.maxresults.setSuffix('')

        self.displaybutton = QtGui.QPushButton()
        self.displaybutton.setText('Display')

        self.zoom_in = QtGui.QPushButton()
        self.zoom_in.setIcon(qtutils.theme_icon('zoom-in.png'))
        self.zoom_in.setFlat(True)

        self.zoom_out = QtGui.QPushButton()
        self.zoom_out.setIcon(qtutils.theme_icon('zoom-out.png'))
        self.zoom_out.setFlat(True)

        self.top_layout = QtGui.QHBoxLayout()
        self.top_layout.setMargin(defs.margin)
        self.top_layout.setSpacing(defs.button_spacing)

        self.top_layout.addWidget(self.maxresults)
        self.top_layout.addWidget(self.revtext)
        self.top_layout.addWidget(self.displaybutton)
        self.top_layout.addStretch()
        self.top_layout.addWidget(self.zoom_out)
        self.top_layout.addWidget(self.zoom_in)

        self.notifier = notifier = observable.Observable()
        self.notifier.refs_updated = refs_updated = 'refs_updated'
        self.notifier.add_observer(refs_updated, self.display)

        self.graphview = GraphView(notifier, self)
        self.treewidget = CommitTreeWidget(notifier, self)
        self.diffwidget = DiffWidget(notifier, self)

        for signal in (archive,):
            qtutils.relay_signal(self, self.graphview, SIGNAL(signal))
            qtutils.relay_signal(self, self.treewidget, SIGNAL(signal))

        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.setHandleWidth(defs.handle_width)

        self.left_splitter = QtGui.QSplitter()
        self.left_splitter.setOrientation(QtCore.Qt.Vertical)
        self.left_splitter.setChildrenCollapsible(True)
        self.left_splitter.setHandleWidth(defs.handle_width)
        self.left_splitter.setStretchFactor(0, 1)
        self.left_splitter.setStretchFactor(1, 1)
        self.left_splitter.insertWidget(0, self.treewidget)
        self.left_splitter.insertWidget(1, self.diffwidget)

        self.splitter.insertWidget(0, self.left_splitter)
        self.splitter.insertWidget(1, self.graphview)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(0)
        self.main_layout.setSpacing(0)
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addWidget(self.splitter)
        self.setLayout(self.main_layout)

        # Also re-loads dag.* from the saved state
        if not qtutils.apply_state(self):
            self.resize_to_desktop()

        # Update fields affected by model
        self.revtext.setText(dag.ref)
        self.maxresults.setValue(dag.count)
        self.update_window_title()

        self.thread = ReaderThread(self, dag)

        self.thread.connect(self.thread, self.thread.commits_ready,
                            self.add_commits)

        self.thread.connect(self.thread, self.thread.done,
                            self.thread_done)

        self.connect(self.splitter, SIGNAL('splitterMoved(int,int)'),
                     self.splitter_moved)

        self.connect(self.zoom_in, SIGNAL('pressed()'),
                     self.graphview.zoom_in)

        self.connect(self.zoom_out, SIGNAL('pressed()'),
                     self.graphview.zoom_out)

        self.connect(self.treewidget, SIGNAL('diff_commits'),
                     self.diff_commits)

        self.connect(self.graphview, SIGNAL('diff_commits'),
                     self.diff_commits)

        self.connect(self.maxresults, SIGNAL('editingFinished()'),
                     self.display)

        self.connect(self.displaybutton, SIGNAL('pressed()'),
                     self.display)

        self.connect(self.revtext, SIGNAL('ref_changed'),
                     self.display)

        self.connect(self.revtext, SIGNAL('textChanged(QString)'),
                     self.text_changed)

        # The model is updated in another thread so use
        # signals/slots to bring control back to the main GUI thread
        self.model.add_observer(self.model.message_updated,
                                self.emit_model_updated)

        self.connect(self, SIGNAL('model_updated'),
                     self.model_updated)

        qtutils.add_close_action(self)

    def text_changed(self, txt):
        self.dag.ref = unicode(txt)
        self.update_window_title()

    def update_window_title(self):
        project = self.model.project
        if self.dag.ref:
            self.setWindowTitle('%s: %s' % (project, self.dag.ref))
        else:
            self.setWindowTitle(project)

    def export_state(self):
        state = super(DAGView, self).export_state()
        state['count'] = self.dag.count
        return state

    def apply_state(self, state):
        try:
            super(DAGView, self).apply_state(state)
        except:
            pass
        try:
            count = state['count']
        except KeyError:
            pass
        else:
            if not self.dag.overridden('count'):
                self.dag.set_count(count)

    def emit_model_updated(self):
        self.emit(SIGNAL('model_updated'))

    def model_updated(self):
        if self.dag.ref:
            self.revtext.update_matches()
            return
        if not self.model.currentbranch:
            return
        self.revtext.setText(self.model.currentbranch)
        self.display()

    def display(self):
        new_ref = unicode(self.revtext.text())
        if not new_ref:
            return
        new_count = self.maxresults.value()
        old_ref = self.old_ref
        old_count = self.old_count
        if old_ref == new_ref and old_count == new_count:
            return

        self.setEnabled(False)

        self.old_ref = new_ref
        self.old_count = new_count

        self.stop()
        self.clear()
        self.dag.set_ref(new_ref)
        self.dag.set_count(self.maxresults.value())
        self.start()

    def show(self):
        super(DAGView, self).show()
        self.splitter.setSizes([self.width()/2, self.width()/2])
        self.left_splitter.setSizes([self.height()/4, self.height()*3/4])
        self.treewidget.adjust_columns()

    def resizeEvent(self, e):
        super(DAGView, self).resizeEvent(e)
        self.treewidget.adjust_columns()

    def splitter_moved(self, pos, idx):
        self.treewidget.adjust_columns()

    def clear(self):
        self.graphview.clear()
        self.treewidget.clear()
        self.commits.clear()
        self.commit_list = []

    def add_commits(self, commits):
        self.commit_list.extend(commits)
        # Keep track of commits
        for commit_obj in commits:
            self.commits[commit_obj.sha1] = commit_obj
            for tag in commit_obj.tags:
                self.commits[tag] = commit_obj
        self.graphview.add_commits(commits)
        self.treewidget.add_commits(commits)

    def thread_done(self):
        self.setEnabled(True)
        try:
            commit_obj = self.commit_list[-1]
        except IndexError:
            return
        sig = signals.commits_selected
        self.notifier.notify_observers(sig, [commit_obj])
        self.graphview.update_scene_rect()
        self.graphview.view_fit()

    def closeEvent(self, event):
        self.revtext.close_popup()
        self.stop()
        qtutils.save_state(self)
        return super(DAGView, self).closeEvent(event)

    def pause(self):
        self.thread.mutex.lock()
        self.thread.stop = True
        self.thread.mutex.unlock()

    def stop(self):
        self.thread.abort = True
        self.thread.wait()

    def start(self):
        self.thread.abort = False
        self.thread.stop = False
        self.thread.start()

    def resume(self):
        self.thread.mutex.lock()
        self.thread.stop = False
        self.thread.mutex.unlock()
        self.thread.condition.wakeOne()

    def resize_to_desktop(self):
        desktop = QtGui.QApplication.instance().desktop()
        width = desktop.width()
        height = desktop.height()
        self.resize(width, height)

    def diff_commits(self, a, b):
        paths = self.dag.paths()
        if paths:
            difftool.launch([a, b, '--'] + paths)
        else:
            difftool.diff_commits(self, a, b)


class ReaderThread(QtCore.QThread):

    commits_ready = SIGNAL('commits_ready')
    done = SIGNAL('done')

    def __init__(self, parent, dag):
        QtCore.QThread.__init__(self, parent)
        self.dag = dag
        self.abort = False
        self.stop = False
        self.mutex = QtCore.QMutex()
        self.condition = QtCore.QWaitCondition()

    def run(self):
        repo = RepoReader(self.dag)
        repo.reset()
        commits = []
        for c in repo:
            self.mutex.lock()
            if self.stop:
                self.condition.wait(self.mutex)
            self.mutex.unlock()
            if self.abort:
                repo.reset()
                return
            commits.append(c)
            if len(commits) >= 512:
                self.emit(self.commits_ready, commits)
                commits = []

        if commits:
            self.emit(self.commits_ready, commits)
        self.emit(self.done)


class Cache(object):
    pass


class Edge(QtGui.QGraphicsItem):
    item_type = QtGui.QGraphicsItem.UserType + 1
    arrow_size = 2.0
    arrow_extra = (arrow_size+1.0)/2.0

    pen = QtGui.QPen(QtCore.Qt.gray, 1.0,
                     QtCore.Qt.DotLine,
                     QtCore.Qt.SquareCap,
                     QtCore.Qt.BevelJoin)

    def __init__(self, source, dest,
                 extra=arrow_extra,
                 arrow_size=arrow_size):

        QtGui.QGraphicsItem.__init__(self)

        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.source = source
        self.dest = dest
        self.setZValue(-2)

        dest_pt = Commit.item_bbox.center()

        self.source_pt = self.mapFromItem(self.source, dest_pt)
        self.dest_pt = self.mapFromItem(self.dest, dest_pt)
        self.line = QtCore.QLineF(self.source_pt, self.dest_pt)

        width = self.dest_pt.x() - self.source_pt.x()
        height = self.dest_pt.y() - self.source_pt.y()
        rect = QtCore.QRectF(self.source_pt, QtCore.QSizeF(width, height))
        self.bound = rect.normalized().adjusted(-extra, -extra, extra, extra)

    def type(self):
        return self.item_type

    def boundingRect(self):
        return self.bound

    def paint(self, painter, option, widget,
              arrow_size=arrow_size,
              gray=QtCore.Qt.gray):
        # Draw the line
        painter.setPen(self.pen)
        painter.drawLine(self.line)


class Commit(QtGui.QGraphicsItem):
    item_type = QtGui.QGraphicsItem.UserType + 2
    width = 46.
    height = 24.

    item_shape = QtGui.QPainterPath()
    item_shape.addRect(width/-2., height/-2., width, height)
    item_bbox = item_shape.boundingRect()

    inner_rect = QtGui.QPainterPath()
    inner_rect.addRect(width/-2.+2., height/-2.+2, width-4., height-4.)
    inner_rect = inner_rect.boundingRect()

    selected_color = QtGui.QColor.fromRgb(255, 255, 0)
    outline_color = QtGui.QColor.fromRgb(64, 96, 192)


    text_options = QtGui.QTextOption()
    text_options.setAlignment(QtCore.Qt.AlignCenter)

    commit_pen = QtGui.QPen()
    commit_pen.setWidth(1.0)
    commit_pen.setColor(outline_color)

    cached_commit_color = QtGui.QColor.fromRgb(128, 222, 255)
    cached_commit_selected_color = QtGui.QColor.fromRgb(32, 64, 255)
    cached_merge_color = QtGui.QColor.fromRgb(255, 255, 255)

    def __init__(self, commit,
                 notifier,
                 selectable=QtGui.QGraphicsItem.ItemIsSelectable,
                 cursor=QtCore.Qt.PointingHandCursor,
                 xpos=width/2. + 1.,
                 commit_color=cached_commit_color,
                 commit_selected_color=cached_commit_selected_color,
                 merge_color=cached_merge_color):

        QtGui.QGraphicsItem.__init__(self)

        self.setZValue(0)
        self.setFlag(selectable)
        self.setCursor(cursor)

        self.commit = commit
        self.notifier = notifier

        if commit.tags:
            self.label = label = Label(commit)
            label.setParentItem(self)
            label.setPos(xpos, 0.)
        else:
            self.label = None

        if len(commit.parents) > 1:
            self.commit_color = merge_color
        else:
            self.commit_color = commit_color
        self.text_pen = QtCore.Qt.black
        self.sha1_text = commit.sha1[:8]

        self.pressed = False
        self.dragged = False

    #
    # Overridden Qt methods
    #

    def blockSignals(self, blocked):
        self.notifier.notification_enabled = not blocked

    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemSelectedHasChanged:
            # Broadcast selection to other widgets
            selected_items = self.scene().selectedItems()
            commits = [item.commit for item in selected_items]
            self.scene().parent().set_selecting(True)
            sig = signals.commits_selected
            self.notifier.notify_observers(sig, commits)
            self.scene().parent().set_selecting(False)

            # Cache the pen for use in paint()
            if value.toPyObject():
                self.commit_color = self.cached_commit_selected_color
                self.text_pen = QtCore.Qt.white
                color = self.selected_color
            else:
                self.text_pen = QtCore.Qt.black
                if len(self.commit.parents) > 1:
                    self.commit_color = self.cached_merge_color
                else:
                    self.commit_color = self.cached_commit_color
                color = self.outline_color
            commit_pen = QtGui.QPen()
            commit_pen.setWidth(1.0)
            commit_pen.setColor(color)
            self.commit_pen = commit_pen

        return QtGui.QGraphicsItem.itemChange(self, change, value)

    def type(self):
        return self.item_type

    def boundingRect(self, rect=item_bbox):
        return rect

    def shape(self):
        return self.item_shape

    def paint(self, painter, option, widget,
              inner=inner_rect,
              text_opts=text_options,
              cache=Cache):

        # Do not draw outside the exposed rect
        painter.setClipRect(option.exposedRect)

        # Draw ellipse
        painter.setPen(self.commit_pen)
        painter.setBrush(self.commit_color)
        painter.drawEllipse(inner)

        # Draw text
        try:
            font = cache.font
        except AttributeError:
            font = cache.font = painter.font()
            font.setPointSize(5)
        painter.setFont(font)
        painter.setPen(self.text_pen)
        painter.drawText(inner, self.sha1_text, text_opts)

    def mousePressEvent(self, event):
        QtGui.QGraphicsItem.mousePressEvent(self, event)
        self.pressed = True
        self.selected = self.isSelected()

    def mouseMoveEvent(self, event):
        if self.pressed:
            self.dragged = True
        QtGui.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)
        if (not self.dragged and
                self.selected and
                event.button() == QtCore.Qt.LeftButton):
            return
        self.pressed = False
        self.dragged = False


class Label(QtGui.QGraphicsItem):
    item_type = QtGui.QGraphicsItem.UserType + 3

    width = 72
    height = 18

    item_shape = QtGui.QPainterPath()
    item_shape.addRect(0, 0, width, height)
    item_bbox = item_shape.boundingRect()

    text_options = QtGui.QTextOption()
    text_options.setAlignment(QtCore.Qt.AlignCenter)
    text_options.setAlignment(QtCore.Qt.AlignVCenter)

    def __init__(self, commit,
                 other_color=QtGui.QColor.fromRgb(255, 255, 64),
                 head_color=QtGui.QColor.fromRgb(64, 255, 64)):
        QtGui.QGraphicsItem.__init__(self)
        self.setZValue(-1)

        # Starts with enough space for two tags. Any more and the commit
        # needs to be taller to accomodate.
        self.commit = commit
        height = len(commit.tags) * self.height/2. + 4. # +6 padding

        self.label_box = QtCore.QRectF(0., -height/2., self.width, height)
        self.text_box = QtCore.QRectF(2., -height/2., self.width-4., height)
        self.tag_text = '\n'.join(commit.tags)

        if 'HEAD' in commit.tags:
            self.color = head_color
        else:
            self.color = other_color

        self.pen = QtGui.QPen()
        self.pen.setColor(self.color.darker())
        self.pen.setWidth(1.0)

    def type(self):
        return self.item_type

    def boundingRect(self, rect=item_bbox):
        return rect

    def shape(self):
        return self.item_shape

    def paint(self, painter, option, widget,
              text_opts=text_options,
              black=QtCore.Qt.black,
              cache=Cache):
        # Draw tags
        painter.setBrush(self.color)
        painter.setPen(self.pen)
        painter.drawRoundedRect(self.label_box, 4, 4)
        try:
            font = cache.font
        except AttributeError:
            font = cache.font = painter.font()
            font.setPointSize(5)
        painter.setFont(font)
        painter.setPen(black)
        painter.drawText(self.text_box, self.tag_text, text_opts)


class GraphView(QtGui.QGraphicsView, ViewerMixin):
    def __init__(self, notifier, parent):
        QtGui.QGraphicsView.__init__(self, parent)
        ViewerMixin.__init__(self)
        try:
            from PyQt4 import QtOpenGL
            glformat = QtOpenGL.QGLFormat(QtOpenGL.QGL.SampleBuffers)
            self.glwidget = QtOpenGL.QGLWidget(glformat)
            self.setViewport(self.glwidget)
        except:
            pass

        self.x_off = 132
        self.y_off = 32
        self.x_max = 0
        self.y_min = 0

        self.selection_list = []
        self.notifier = notifier
        self.commits = []
        self.items = {}
        self.saved_matrix = QtGui.QMatrix(self.matrix())

        self.x_offsets = collections.defaultdict(int)

        self.is_panning = False
        self.pressed = False
        self.selecting = False
        self.last_mouse = [0, 0]
        self.zoom = 2
        self.setDragMode(self.RubberBandDrag)

        scene = QtGui.QGraphicsScene(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        self.setScene(scene)


        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setOptimizationFlag(self.DontAdjustForAntialiasing, True)
        self.setViewportUpdateMode(self.SmartViewportUpdate)
        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setBackgroundBrush(QtGui.QColor.fromRgb(0, 0, 0))

        self.action_zoom_in = (
            qtutils.add_action(self, 'Zoom In',
                               self.zoom_in,
                               QtCore.Qt.Key_Plus,
                               QtCore.Qt.Key_Equal))

        self.action_zoom_out = (
            qtutils.add_action(self, 'Zoom Out',
                               self.zoom_out,
                               QtCore.Qt.Key_Minus))

        self.action_zoom_fit = (
            qtutils.add_action(self, 'Zoom to Fit',
                               self.view_fit,
                               QtCore.Qt.Key_F))

        self.action_select_parent = (
            qtutils.add_action(self, 'Select Parent',
                               self.select_parent,
                               QtCore.Qt.Key_J))

        self.action_select_oldest_parent = (
            qtutils.add_action(self, 'Select Oldest Parent',
                               self.select_oldest_parent,
                               'Shift+J'))

        self.action_select_child = (
            qtutils.add_action(self, 'Select Child',
                               self.select_child,
                               QtCore.Qt.Key_K))

        self.action_select_child = (
            qtutils.add_action(self, 'Select Nth Child',
                               self.select_nth_child,
                               'Shift+K'))

        sig = signals.commits_selected
        notifier.add_observer(sig, self.commits_selected)

    def clear(self):
        self.scene().clear()
        self.selection_list = []
        self.items.clear()
        self.x_offsets.clear()
        self.x_max = 0
        self.y_min = 0
        self.commits = []

    def zoom_in(self):
        self.scale_view(1.5)

    def zoom_out(self):
        self.scale_view(1.0/1.5)

    def commits_selected(self, commits):
        if self.selecting:
            return
        self.clicked = commits and commits[0] or None
        self.select([commit.sha1 for commit in commits])

    def contextMenuEvent(self, event):
        self.context_menu_event(event)

    def select(self, sha1s):
        """Select the item for the SHA-1"""
        self.scene().clearSelection()
        for sha1 in sha1s:
            try:
                item = self.items[sha1]
            except KeyError:
                continue
            item.blockSignals(True)
            item.setSelected(True)
            item.blockSignals(False)
            item_rect = item.sceneTransform().mapRect(item.boundingRect())
            self.ensureVisible(item_rect)

    def selected_item(self):
        """Return the currently selected item"""
        selected_items = self.selectedItems()
        if not selected_items:
            return None
        return selected_items[0]

    def selectedItems(self):
        """Return the currently selected items"""
        return self.scene().selectedItems()

    def get_item_by_generation(self, commits, criteria_fn):
        """Return the item for the commit matching criteria"""
        if not commits:
            return None
        generation = None
        for commit in commits:
            if (generation is None or
                    criteria_fn(generation, commit.generation)):
                sha1 = commit.sha1
                generation = commit.generation
        try:
            return self.items[sha1]
        except KeyError:
            return None

    def oldest_item(self, commits):
        """Return the item for the commit with the oldest generation number"""
        return self.get_item_by_generation(commits, lambda a, b: a > b)

    def newest_item(self, commits):
        """Return the item for the commit with the newest generation number"""
        return self.get_item_by_generation(commits, lambda a, b: a < b)

    def create_patch(self):
        items = self.selectedItems()
        if not items:
            return
        selected_commits = self.sort_by_generation([n.commit for n in items])
        sha1s = [c.sha1 for c in selected_commits]
        all_sha1s = [c.sha1 for c in self.commits]
        cola.notifier().broadcast(signals.format_patch, sha1s, all_sha1s)

    def select_parent(self):
        """Select the parent with the newest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self.newest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        self.ensureVisible(parent_item.mapRectToScene(parent_item.boundingRect()))

    def select_oldest_parent(self):
        """Select the parent with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self.oldest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        self.ensureVisible(parent_item.mapRectToScene(parent_item.boundingRect()))

    def select_child(self):
        """Select the child with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        child_item = self.oldest_item(selected_item.commit.children)
        if child_item is None:
            return
        selected_item.setSelected(False)
        child_item.setSelected(True)
        self.ensureVisible(child_item.mapRectToScene(child_item.boundingRect()))

    def select_nth_child(self):
        """Select the Nth child with the newest generation number (N > 1)"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        if len(selected_item.commit.children) > 1:
            children = selected_item.commit.children[1:]
        else:
            children = selected_item.commit.children
        child_item = self.newest_item(children)
        if child_item is None:
            return
        selected_item.setSelected(False)
        child_item.setSelected(True)
        self.ensureVisible(child_item.mapRectToScene(child_item.boundingRect()))

    def view_fit(self):
        """Fit selected items into the viewport"""

        items = self.scene().selectedItems()
        if not items:
            rect = self.scene().itemsBoundingRect()
        else:
            x_min = sys.maxint
            y_min = sys.maxint
            x_max = -sys.maxint
            ymax = -sys.maxint
            for item in items:
                pos = item.pos()
                item_rect = item.boundingRect()
                x_off = item_rect.width()
                y_off = item_rect.height()
                x_min = min(x_min, pos.x())
                y_min = min(y_min, pos.y())
                x_max = max(x_max, pos.x()+x_off)
                ymax = max(ymax, pos.y()+y_off)
            rect = QtCore.QRectF(x_min, y_min, x_max-x_min, ymax-y_min)
        adjust = Commit.width
        rect.setX(rect.x() - adjust)
        rect.setY(rect.y() - adjust)
        rect.setHeight(rect.height() + adjust)
        rect.setWidth(rect.width() + adjust)
        self.fitInView(rect, QtCore.Qt.KeepAspectRatio)
        self.scene().invalidate()

    def save_selection(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        elif QtCore.Qt.ShiftModifier != event.modifiers():
            return
        self.selection_list = self.selectedItems()

    def restore_selection(self, event):
        if QtCore.Qt.ShiftModifier != event.modifiers():
            return
        for item in self.selection_list:
            item.setSelected(True)

    def handle_event(self, event_handler, event):
        self.update()
        self.save_selection(event)
        event_handler(self, event)
        self.restore_selection(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MidButton:
            pos = event.pos()
            self.mouse_start = [pos.x(), pos.y()]
            self.saved_matrix = QtGui.QMatrix(self.matrix())
            self.is_panning = True
            return
        if event.button() == QtCore.Qt.RightButton:
            event.ignore()
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.pressed = True
        self.handle_event(QtGui.QGraphicsView.mousePressEvent, event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self.is_panning:
            self.pan(event)
            return
        self.last_mouse[0] = pos.x()
        self.last_mouse[1] = pos.y()
        self.handle_event(QtGui.QGraphicsView.mouseMoveEvent, event)

    def set_selecting(self, selecting):
        self.selecting = selecting

    def mouseReleaseEvent(self, event):
        self.pressed = False
        if event.button() == QtCore.Qt.MidButton:
            self.is_panning = False
            return
        self.handle_event(QtGui.QGraphicsView.mouseReleaseEvent, event)
        self.selection_list = []

    def pan(self, event):
        pos = event.pos()
        dx = pos.x() - self.mouse_start[0]
        dy = pos.y() - self.mouse_start[1]

        if dx == 0 and dy == 0:
            return

        rect = QtCore.QRect(0, 0, abs(dx), abs(dy))
        delta = self.mapToScene(rect).boundingRect()

        tx = delta.width()
        if dx < 0.0:
            tx = -tx

        ty = delta.height()
        if dy < 0.0:
            ty = -ty

        matrix = QtGui.QMatrix(self.saved_matrix).translate(tx, ty)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def wheelEvent(self, event):
        """Handle Qt mouse wheel events."""
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self.wheel_zoom(event)
        else:
            self.wheel_pan(event)

    def wheel_zoom(self, event):
        """Handle mouse wheel zooming."""
        zoom = math.pow(2.0, event.delta() / 512.0)
        factor = (self.matrix()
                        .scale(zoom, zoom)
                        .mapRect(QtCore.QRectF(0.0, 0.0, 1.0, 1.0))
                        .width())
        if factor < 0.014 or factor > 42.0:
            return
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.zoom = zoom
        self.scale(zoom, zoom)

    def wheel_pan(self, event):
        """Handle mouse wheel panning."""

        if event.delta() < 0:
            s = -133.
        else:
            s = 133.
        pan_rect = QtCore.QRectF(0.0, 0.0, 1.0, 1.0)
        factor = 1.0 / self.matrix().mapRect(pan_rect).width()

        if event.orientation() == QtCore.Qt.Vertical:
            matrix = self.matrix().translate(0, s * factor)
        else:
            matrix = self.matrix().translate(s * factor, 0)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def scale_view(self, scale):
        factor = (self.matrix().scale(scale, scale)
                               .mapRect(QtCore.QRectF(0, 0, 1, 1))
                               .width())
        if factor < 0.07 or factor > 100:
            return
        self.zoom = scale

        adjust_scrollbars = True
        scrollbar = self.verticalScrollBar()
        if scrollbar:
            value = scrollbar.value()
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            distance = value - min_
            nonzero_range = float(range_) != 0.0
            if nonzero_range:
                scrolloffset = distance/float(range_)
            else:
                adjust_scrollbars = False

        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.scale(scale, scale)

        scrollbar = self.verticalScrollBar()
        if scrollbar and adjust_scrollbars:
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            value = min_ + int(float(range_) * scrolloffset)
            scrollbar.setValue(value)

    def add_commits(self, commits):
        """Traverse commits and add them to the view."""
        self.commits.extend(commits)
        scene = self.scene()
        for commit in commits:
            item = Commit(commit, self.notifier)
            self.items[commit.sha1] = item
            for ref in commit.tags:
                self.items[ref] = item
            scene.addItem(item)

        self.layout_commits(commits)
        self.link(commits)

    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        for commit in commits:
            try:
                commit_item = self.items[commit.sha1]
            except KeyError:
                # TODO - Handle truncated history viewing
                pass
            for parent in commit.parents:
                try:
                    parent_item = self.items[parent.sha1]
                except KeyError:
                    # TODO - Handle truncated history viewing
                    continue
                edge = Edge(parent_item, commit_item)
                scene.addItem(edge)

    def layout_commits(self, nodes):
        positions = self.position_nodes(nodes)
        for sha1, (x, y) in positions.items():
            item = self.items[sha1]
            item.setPos(x, y)

    def position_nodes(self, nodes):
        positions = {}

        x_max = self.x_max
        y_min = self.y_min
        x_off = self.x_off
        y_off = self.y_off
        x_offsets = self.x_offsets

        for node in nodes:
            generation = node.generation
            sha1 = node.sha1

            if len(node.children) > 1:
                # This is a fan-out so sweep over child generations and
                # shift them to the right to avoid overlapping edges
                child_gens = [c.generation for c in node.children]
                maxgen = reduce(max, child_gens)
                mingen = reduce(min, child_gens)
                if maxgen > mingen:
                    for g in xrange(generation+1, maxgen):
                        x_offsets[g] += x_off

            if len(node.parents) == 1:
                # Align nodes relative to their parents
                parent_gen = node.parents[0].generation
                parent_off = x_offsets[parent_gen]
                x_offsets[generation] = max(parent_off-x_off,
                                            x_offsets[generation])

            cur_xoff = x_offsets[generation]
            next_xoff = cur_xoff
            next_xoff += x_off
            x_offsets[generation] = next_xoff

            x_pos = cur_xoff
            y_pos = -generation * y_off
            positions[sha1] = (x_pos, y_pos)

            x_max = max(x_max, x_pos)
            y_min = min(y_min, y_pos)


        self.x_max = x_max
        self.y_min = y_min

        return positions

    def update_scene_rect(self):
        y_min = self.y_min
        x_max = self.x_max
        self.scene().setSceneRect(-Commit.width*3/4,
                                  y_min-self.y_off/2,
                                  x_max + int(self.x_off * 1.1),
                                  abs(y_min)+self.y_off)

    def sort_by_generation(commits):
        commits.sort(cmp=lambda a, b: cmp(a.generation, b.generation))
        return commits
