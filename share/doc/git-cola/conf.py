# -*- coding: utf-8 -*-
import os
import sys

try:
    import sphinx_rtd_theme
except ImportError:
    sphinx_rtd_theme = None

# Add the cola source directory to sys.path
abspath = os.path.abspath(os.path.realpath(__file__))
docdir = os.path.dirname(os.path.dirname(abspath))
srcdir = os.path.dirname(os.path.dirname(docdir))
extrasdir = os.path.join(srcdir, 'extras')
sys.path.insert(1, extrasdir)

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinxtogithub',
]
if sphinx_rtd_theme:
    extensions.append('sphinx_rtd_theme')

templates_path = ['_templates']
source_suffix = '.rst'
source_encoding = 'utf-8'
master_doc = 'index'

project = 'git-cola'
copyright = '2007-2020, David Aguilar and contributors'
authors = 'David Aguilar and contributors'

versionfile = os.path.join(srcdir, 'cola', '_version.py')
scope = {}
with open(versionfile) as f:
    exec (f.read(), scope)

# The short X.Y version.
version = scope['VERSION']
# The full version, including alpha/beta/rc tags.
release = version

exclude_trees = ['_build']
add_function_parentheses = True
pygments_style = 'default'

if sphinx_rtd_theme:
    html_theme = 'sphinx_rtd_theme'
html_theme_path = ['_themes']
html_static_path = ['_static']
html_show_sourcelink = True
htmlhelp_basename = 'git-cola-doc'

man_pages = [
    ('git-cola', 'git-cola', 'The highly caffeinated Git GUI', authors, '1'),
    ('git-dag', 'git-dag', 'The sleek and powerful Git history browser', authors, '1'),
]

# Sphinx 4.0 creates sub-directories for each man section.
# Disable this feature for consistency across Sphinx versions.
man_make_section_directory = False

latex_documents = [
    (
        'index',
        'git-cola.tex',
        'git-cola Documentation',
        'David Aguilar and contributors',
        'manual',
    ),
]
