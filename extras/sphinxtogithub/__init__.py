"""Script for preparing the html output of the Sphinx documentation system for
github pages. """

VERSION = (1, 1, 0, 'dev')

__version__ = '.'.join(map(str, VERSION[:-1]))
__release__ = '.'.join(map(str, VERSION))
__author__ = 'Michael Jones'
__contact__ = 'http://github.com/michaeljones'
__homepage__ = 'http://github.com/michaeljones/sphinx-to-github'
__docformat__ = 'restructuredtext'

from .sphinxtogithub import DirectoryHandler
from .sphinxtogithub import DirHelper
from .sphinxtogithub import FileHandler
from .sphinxtogithub import FileSystemHelper
from .sphinxtogithub import ForceRename
from .sphinxtogithub import HandlerFactory
from .sphinxtogithub import Layout
from .sphinxtogithub import LayoutFactory
from .sphinxtogithub import OperationsFactory
from .sphinxtogithub import Remover
from .sphinxtogithub import Replacer
from .sphinxtogithub import VerboseRename
from .sphinxtogithub import setup
from .sphinxtogithub import sphinx_extension
