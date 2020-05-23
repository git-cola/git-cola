"""Script for preparing the html output of the Sphinx documentation system for
github pages. """
# flake8: noqa
from __future__ import absolute_import, division, unicode_literals

VERSION = (1, 1, 0, 'dev')

__version__ = ".".join(map(str, VERSION[:-1]))
__release__ = ".".join(map(str, VERSION))
__author__ = "Michael Jones"
__contact__ = "http://github.com/michaeljones"
__homepage__ = "http://github.com/michaeljones/sphinx-to-github"
__docformat__ = "restructuredtext"

from .sphinxtogithub import (
    setup,
    sphinx_extension,
    LayoutFactory,
    Layout,
    DirectoryHandler,
    VerboseRename,
    ForceRename,
    Remover,
    FileHandler,
    Replacer,
    DirHelper,
    FileSystemHelper,
    OperationsFactory,
    HandlerFactory,
)
