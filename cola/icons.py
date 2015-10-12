"""The only file where icon filenames are mentioned"""

import mimetypes
import os

from PyQt4 import QtGui

from cola import qtcompat
from cola import resources
from cola.compat import ustr
from cola.decorators import memoize


KNOWN_FILE_MIME_TYPES = [
    ('text',    'file-code.svg'),
    ('image',   'file-media.svg'),
    ('python',  'file-code.svg'),
    ('ruby',    'file-code.svg'),
    ('shell',   'file-code.svg'),
    ('perl',    'file-code.svg'),
    ('octet',   'file-binary.svg'),
]

KNOWN_FILE_EXTENSIONS = {
    '.java':    'file-code.svg',
    '.groovy':  'file-code.svg',
    '.cpp':     'file-code.svg',
    '.c':       'file-code.svg',
    '.h':       'file-code.svg',
    '.cxx':     'file-code.svg',
}


def install():
    icon_dir = resources.icon_dir()
    qtcompat.add_search_path('icons', icon_dir)


def name_from_basename(basename):
    """Prefix the basename with "icons:" so that git-cola's icons are found

    "icons" is registered with Qt's resource system during install().

    """
    return 'icons:' + basename


@memoize
def from_name(name):
    """Return a QIcon from an absolute filename or "icons:basename.svg" name"""
    return QtGui.QIcon(name)


def icon(basename):
    """Given a basename returns a QIcon from the corresponding cola icon"""
    return from_name(name_from_basename(basename))


@memoize
def from_theme(name, fallback=None):
    """Grab an icon from the current theme with a fallback

    Support older versions of Qt checking for fromTheme's availability.

    """
    if hasattr(QtGui.QIcon, 'fromTheme'):
        base, ext = os.path.splitext(name)
        if fallback:
            qicon = QtGui.QIcon.fromTheme(base, icon(fallback))
        else:
            qicon = QtGui.QIcon.fromTheme(base)
        if not qicon.isNull():
            return qicon
    return icon(fallback or name)


def basename_from_filename(filename):
    """Returns an icon name based on the filename"""
    mimetype = mimetypes.guess_type(filename)[0]
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


def mkicon(icon, default=None):
    if icon is None and default is not None:
        icon = default()
    elif icon and isinstance(icon, (str, ustr)):
        icon = QtGui.QIcon(icon)
    return icon


@memoize
def from_style(key):
    """Maintain a cache of standard icons and return cache entries."""
    style = QtGui.QApplication.instance().style()
    return style.standardIcon(key)


def status(filename, deleted, staged, untracked):
    if deleted:
        icon_name = 'circle-slash-red.svg'
    elif staged:
        icon_name = 'staged.svg'
    elif untracked:
        icon_name = 'question-plain.svg'
    else:
        icon_name = basename_from_filename(filename)
    return icon_name


# Icons creators and SVG file references

def add():
    return from_theme('list-add', fallback='plus.svg')


def branch():
    return icon('git-branch.svg')


def check_name():
    return name_from_basename('check.svg')


def close():
    return icon('x.svg')


def cola():
    return from_theme('git-cola.svg')


def compare():
    return icon('git-compare.svg')


def configure():
    return from_theme('configure', fallback='gear.svg')


def copy():
    return from_theme('edit-copy.svg')


def default_app():
    return icon('telescope.svg')


def dot_name():
    return name_from_basename('primitive-dot.svg')


def download():
    return icon('file-download.svg')


def discard():
    return icon('trashcan.svg')

# folder vs directory: directory is opaque, folder is just an outline
# directory is used for the File Browser, where more contrast with the file
# icons are needed.

def folder():
    return icon('folder.svg')

def directory():
    return icon('file-directory.svg')


def diff():
    return icon('diff.svg')


def edit():
    return icon('pencil.svg')


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


def modified_name():
    return name_from_basename('modified.svg')


def new():
    return icon('folder-new.svg')


def ok():
    return icon('check.svg')


def open_directory():
    return icon('folder.svg')


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


def save():
    return icon('desktop-download.svg')


def search():
    return icon('search.svg')


def select_all():
    return from_theme('edit-select-all.svg')


def staged():
    return icon('staged.svg')


def staged_name():
    return name_from_basename('staged.svg')


def sync():
    return icon('sync.svg')


def tag():
    return icon('tag.svg')


def undo():
    return from_theme('edit-undo', fallback='edit-undo.svg')


def unfold():
    return icon('unfold.svg')


def visualize():
    return icon('eye.svg')


def upstream_name():
    return name_from_basename('upstream.svg')


def zoom_fit_best():
    return from_theme('zoom-fit-best.svg')


def zoom_in():
    return from_theme('zoom-in.svg')


def zoom_out():
    return from_theme('zoom-out.svg')
