"""The only file where icon filenames are mentioned"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os

from qtpy import QtGui
from qtpy import QtWidgets

from . import core
from . import qtcompat
from . import resources
from .compat import ustr
from .i18n import N_


KNOWN_FILE_MIME_TYPES = [
    ('text', 'file-code.svg'),
    ('image', 'file-media.svg'),
    ('octet', 'file-binary.svg'),
]

KNOWN_FILE_EXTENSIONS = {
    '.bash': 'file-code.svg',
    '.c': 'file-code.svg',
    '.cpp': 'file-code.svg',
    '.css': 'file-code.svg',
    '.cxx': 'file-code.svg',
    '.h': 'file-code.svg',
    '.hpp': 'file-code.svg',
    '.hs': 'file-code.svg',
    '.html': 'file-code.svg',
    '.java': 'file-code.svg',
    '.js': 'file-code.svg',
    '.ksh': 'file-code.svg',
    '.lisp': 'file-code.svg',
    '.perl': 'file-code.svg',
    '.pl': 'file-code.svg',
    '.py': 'file-code.svg',
    '.rb': 'file-code.svg',
    '.rs': 'file-code.svg',
    '.sh': 'file-code.svg',
    '.zsh': 'file-code.svg',
}


def install(themes):
    for theme in themes:
        icon_dir = resources.icon_dir(theme)
        qtcompat.add_search_path('icons', icon_dir)


def icon_themes():
    return (
        (N_('Default'), 'default'),
        (N_('Dark Theme'), 'dark'),
        (N_('Light Theme'), 'light'),
    )


def name_from_basename(basename):
    """Prefix the basename with "icons:" so that git-cola's icons are found

    "icons" is registered with Qt's resource system during install().

    """
    return 'icons:' + basename


def from_name(name):
    """Return a QIcon from an absolute filename or "icons:basename.svg" name"""
    return QtGui.QIcon(name)


def icon(basename):
    """Given a basename returns a QIcon from the corresponding cola icon"""
    return from_name(name_from_basename(basename))


def from_theme(name, fallback=None):
    """Grab an icon from the current theme with a fallback

    Support older versions of Qt checking for fromTheme's availability.

    """
    if hasattr(QtGui.QIcon, 'fromTheme'):
        base, _ = os.path.splitext(name)
        if fallback:
            qicon = QtGui.QIcon.fromTheme(base, icon(fallback))
        else:
            qicon = QtGui.QIcon.fromTheme(base)
        if not qicon.isNull():
            return qicon
    return icon(fallback or name)


def basename_from_filename(filename):
    """Returns an icon name based on the filename"""
    mimetype = core.guess_mimetype(filename)
    if mimetype is not None:
        mimetype = mimetype.lower()
        for filetype, icon_name in KNOWN_FILE_MIME_TYPES:
            if filetype in mimetype:
                return icon_name
    extension = os.path.splitext(filename)[1]
    return KNOWN_FILE_EXTENSIONS.get(extension.lower(), 'file-text.svg')


def from_filename(filename):
    basename = basename_from_filename(filename)
    return from_name(name_from_basename(basename))


def mkicon(value, default=None):
    if value is None and default is not None:
        value = default()
    elif value and isinstance(value, (str, ustr)):
        value = QtGui.QIcon(value)
    return value


def from_style(key):
    """Maintain a cache of standard icons and return cache entries."""
    style = QtWidgets.QApplication.instance().style()
    return style.standardIcon(key)


def status(filename, deleted, is_staged, untracked):
    if deleted:
        icon_name = 'circle-slash-red.svg'
    elif is_staged:
        icon_name = 'staged.svg'
    elif untracked:
        icon_name = 'question-plain.svg'
    else:
        icon_name = basename_from_filename(filename)
    return icon_name


# Icons creators and SVG file references


def three_bars():
    return icon('three-bars.svg')


def add():
    return from_theme('list-add', fallback='plus.svg')


def alphabetical():
    return from_theme('view-sort', fallback='a-z-order.svg')


def branch():
    return icon('git-branch.svg')


def check_name():
    return name_from_basename('check.svg')


def cherry_pick():
    return icon('git-commit.svg')


def close():
    return icon('x.svg')


def cola():
    return icon('git-cola.svg')


def commit():
    return icon('document-save-symbolic.svg')


def compare():
    return icon('git-compare.svg')


def configure():
    return icon('gear.svg')


def cut():
    return from_theme('edit-cut', fallback='edit-cut.svg')


def copy():
    return from_theme('edit-copy', fallback='edit-copy.svg')


def paste():
    return from_theme('edit-paste', fallback='edit-paste.svg')


def delete():
    return from_theme('edit-delete', fallback='trashcan.svg')


def default_app():
    return icon('telescope.svg')


def dot_name():
    return name_from_basename('primitive-dot.svg')


def download():
    return icon('file-download.svg')


def discard():
    return from_theme('delete', fallback='trashcan.svg')


# folder vs directory: directory is opaque, folder is just an outline
# directory is used for the File Browser, where more contrast with the file
# icons are needed.


def folder():
    return from_theme('folder', fallback='folder.svg')


def directory():
    return from_theme('folder', fallback='file-directory.svg')


def diff():
    return icon('diff.svg')


def edit():
    return from_theme('document-edit', fallback='pencil.svg')


def ellipsis():
    return icon('ellipsis.svg')


def external():
    return icon('link-external.svg')


def file_code():
    return icon('file-code.svg')


def file_text():
    return icon('file-text.svg')


def file_zip():
    return icon('file-zip.svg')


def fold():
    return icon('fold.svg')


def merge():
    return icon('git-merge.svg')


def modified():
    return icon('modified.svg')


def modified_name():
    return name_from_basename('modified.svg')


def move_down():
    return from_theme('go-previous', fallback='arrow-down.svg')


def move_up():
    return from_theme('go-next', fallback='arrow-up.svg')


def new():
    return from_theme('list-add', fallback='folder-new.svg')


def ok():
    return from_theme('checkmark', fallback='check.svg')


def open_directory():
    return from_theme('folder', fallback='folder.svg')


def partial_name():
    return name_from_basename('partial.svg')


def pull():
    return icon('repo-pull.svg')


def push():
    return icon('repo-push.svg')


def question():
    return icon('question.svg')


def remove():
    return from_theme('list-remove', fallback='circle-slash.svg')


def repo():
    return icon('repo.svg')


def reverse_chronological():
    return icon('last-first-order.svg')


def save():
    return from_theme('document-save', fallback='desktop-download.svg')


def search():
    return from_theme('search', fallback='search.svg')


def select_all():
    return from_theme('edit-select-all', fallback='edit-select-all')


def staged():
    return icon('staged.svg')


def staged_name():
    return name_from_basename('staged.svg')


def star():
    return icon('star.svg')


def sync():
    return icon('sync.svg')


def tag():
    return icon('tag.svg')


def undo():
    return from_theme('edit-undo', fallback='edit-undo.svg')


def redo():
    return from_theme('edit-redo', fallback='edit-redo.svg')


def style_dialog_apply():
    return from_style(QtWidgets.QStyle.SP_DialogApplyButton)


def style_dialog_discard():
    return from_style(QtWidgets.QStyle.SP_DialogDiscardButton)


def style_dialog_reset():
    return from_style(QtWidgets.QStyle.SP_DialogResetButton)


def unfold():
    return icon('unfold.svg')


def visualize():
    return icon('eye.svg')


def upstream_name():
    return name_from_basename('upstream.svg')


def zoom_fit_best():
    return from_theme('zoom-fit-best', fallback='zoom-fit-best.svg')


def zoom_in():
    return from_theme('zoom-in', fallback='zoom-in.svg')


def zoom_out():
    return from_theme('zoom-out', fallback='zoom-out.svg')
