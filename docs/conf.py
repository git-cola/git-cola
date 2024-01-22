import os
import sys

try:
    import furo
except ImportError:
    furo = None
try:
    import sphinx_rtd_theme
except ImportError:
    sphinx_rtd_theme = None
try:
    import rst.linker as rst_linker
except ImportError:
    rst_linker = None

# Add the source tree and extras/ to sys.path.
srcdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
extrasdir = os.path.join(srcdir, 'extras')
sys.path.insert(0, srcdir)
sys.path.insert(1, extrasdir)

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinxtogithub',
]

master_doc = 'index'
html_theme = 'default'

# {package_url} can be provided py jaraco.packaging.sphinx but we
# expand the value manually to avoid the dependency.
package_url = 'https://gitlab.com/git-cola/git-cola'

project = 'Git Cola'

# Link dates and other references in the changelog
if rst_linker is not None:
    extensions += ['rst.linker']

link_files = {
    '../CHANGES.rst': dict(
        using=dict(GH='https://github.com', package_url=package_url),
        replace=[
            dict(
                pattern=r'(Issue #|\B#)(?P<issue>\d+)',
                url='{package_url}/issues/{issue}',
            ),
            dict(
                pattern=r'(?m:^((?P<scm_version>v?\d+(\.\d+){1,2}))\n[-=]+\n)',
                with_scm='{text}\n{rev[timestamp]:%d %b %Y}\n',
            ),
            dict(
                pattern=r'PEP[- ](?P<pep_number>\d+)',
                url='https://www.python.org/dev/peps/pep-{pep_number:0>4}/',
            ),
        ],
    )
}

# Be strict about any broken references
nitpicky = True

# Preserve authored syntax for defaults
autodoc_preserve_defaults = True

# Get the version from cola/_version.py.
versionfile = os.path.join(srcdir, 'cola', '_version.py')
scope = {}
with open(versionfile) as f:
    exec(f.read(), scope)

version = scope['VERSION']  # The short X.Y version.
release = version  # The full version, including alpha/beta/rc tags.

authors = 'David Aguilar and contributors'
man_pages = [
    ('git-cola', 'git-cola', 'The highly caffeinated Git GUI', authors, '1'),
    ('git-dag', 'git-dag', 'The sleek and powerful Git history browser', authors, '1'),
]

# Sphinx 4.0 creates sub-directories for each man section.
# Disable this feature for consistency across Sphinx versions.
man_make_section_directory = False


# furo overwrites "_static/pygments.css" so we monkey-patch
# "def _overwrite_pygments_css()" to use "static/pygments.css" instead.
def _overwrite_pygments_css(app, exception):
    """Replacement for furo._overwrite_pygments_css to handle sphinxtogithub"""
    if exception is not None:
        return
    assert app.builder
    with open(
        os.path.join(app.builder.outdir, 'static', 'pygments.css'),
        'w',
        encoding='utf-8',
    ) as f:
        f.write(furo.get_pygments_stylesheet())


# Enable custom themes.
if furo is not None and hasattr(furo, '_overwrite_pygments_css'):
    furo._overwrite_pygments_css = _overwrite_pygments_css
    html_theme = 'furo'
elif sphinx_rtd_theme is not None:
    extensions += ['sphinx_rtd_theme']
    html_theme = 'sphinx_rtd_theme'
