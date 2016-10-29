# encoding: utf-8
from __future__ import division, absolute_import, unicode_literals
import platform
import webbrowser
import sys

import qtpy
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import core
from .. import resources
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import version
from ..i18n import N_
from . import defs


def about_dialog():
    """Launches the Help -> About dialog"""
    view = AboutView(qtutils.active_window())
    view.show()
    return view


class ExpandingTabBar(QtWidgets.QTabBar):
    """A TabBar with tabs that expand to fill the empty space

    The setExpanding(True) method does not work in practice because
    it respects the OS style.  We override the style by implementing
    tabSizeHint() so that we can specify the size explicitly.

    """

    def tabSizeHint(self, tab_index):
        size = super(ExpandingTabBar, self).tabSizeHint(tab_index)
        size.setWidth(self.parent().width() / self.count() - 1)
        return size


class AboutView(QtWidgets.QDialog):
    """Provides the git-cola 'About' dialog"""

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.setWindowTitle(N_('About git-cola'))
        self.setWindowModality(Qt.WindowModal)

        # Top-most large icon
        logo_pixmap = icons.cola().pixmap(defs.huge_icon, defs.large_icon)

        self.logo_label = QtWidgets.QLabel()
        self.logo_label.setPixmap(logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignCenter)

        self.logo_text_label = QtWidgets.QLabel()
        self.logo_text_label.setText('Git Cola')
        self.logo_text_label.setAlignment(Qt.AlignLeft | Qt.AlignCenter)

        font = self.logo_text_label.font()
        font.setPointSize(defs.logo_text)
        self.logo_text_label.setFont(font)

        self.text = qtutils.textbrowser(text=copyright_text())
        self.version = qtutils.textbrowser(text=version_text())
        self.authors = qtutils.textbrowser(text=authors_text())
        self.translators = qtutils.textbrowser(text=translators_text())

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setTabBar(ExpandingTabBar(self.tabs))
        self.tabs.addTab(self.text, N_('About'))
        self.tabs.addTab(self.version, N_('Version'))
        self.tabs.addTab(self.authors, N_('Authors'))
        self.tabs.addTab(self.translators, N_('Translators'))

        self.close_button = qtutils.close_button()
        self.close_button.setDefault(True)

        self.logo_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                        self.logo_label, self.logo_text_label,
                                        qtutils.STRETCH)

        self.button_layout = qtutils.hbox(defs.spacing, defs.margin,
                                          qtutils.STRETCH, self.close_button)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.logo_layout,
                                        self.tabs,
                                        self.button_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.close_button, self.accept)

        self.resize(defs.scale(600), defs.scale(720))


def copyright_text():
    return """
Git Cola: The highly caffeinated Git GUI

Copyright (C) 2007-2016 David Aguilar and contributors

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License
version 2 as published by the Free Software Foundation.

This program is distributed in the hope that it will
be useful, but WITHOUT ANY WARRANTY; without even the
implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the
GNU General Public License along with this program.
If not, see http://www.gnu.org/licenses/.

"""


def version_text():
    git_version = version.git_version()
    cola_version = version.version()
    python_path = sys.executable
    python_version = sys.version
    qt_version = qtpy.QT_VERSION
    qtpy_version = qtpy.__version__
    pyqt_api_name = qtpy.API_NAME
    if qtpy.PYQT5 or qtpy.PYQT4:
        pyqt_api_version = qtpy.PYQT_VERSION
    elif qtpy.PYSIDE:
        pyqt_api_version = qtpy.PYSIDE_VERSION
    else:
        pyqt_api_version = 'unknown'

    platform_version = platform.platform()

    return N_("""
        <br>
            Git Cola version %(cola_version)s
        <ul>
            <li> %(platform_version)s
            <li> Python (%(python_path)s) %(python_version)s
            <li> Git %(git_version)s
            <li> Qt %(qt_version)s
            <li> QtPy %(qtpy_version)s
            <li> %(pyqt_api_name)s %(pyqt_api_version)s
        </ul>
    """) % locals()


def link(url, text, palette=None):
    if palette is None:
        palette = QtGui.QPalette()

    color = palette.color(QtGui.QPalette.Foreground)
    rgb = 'rgb(%s, %s, %s)' % (color.red(), color.green(), color.blue())

    return ("""
        <a style="font-style: italic; text-decoration: none; color: %(rgb)s;"
            href="%(url)s">
            %(text)s
        </a>
    """ % locals())

def mailto(email, text, palette):
    return link('mailto:%s' % email, text, palette) + '<br>'


def render_authors(authors):
    """Render a list of author details into richtext html"""
    for x in authors:
        x.setdefault('email', '')

    entries = [("""
        <p>
            <strong>%(name)s</strong><br>
            <em>%(title)s</em><br>
            %(email)s
        </p>
    """ % author) for author in authors]

    return ''.join(entries)


def contributors_text(authors, epilogue=''):
    author_text = render_authors(authors)

    bug_url = 'https://github.com/git-cola/git-cola/issues'
    bug_link = link(bug_url, bug_url)

    return N_("""
        <br>
        Please use %(bug_link)s to report issues.
        <br>

        %(author_text)s
        %(epilogue)s
    """) % locals()


def authors_text():
    palette = QtGui.QPalette()
    email_text = N_('Email contributor')
    authors = (
        dict(name='David Aguilar',
             title=N_('Maintainer (since 2007) and developer'),
             email=mailto('davvid@gmail.com', email_text, palette)),
        # The names listed here are listed in the same order as
        # `git shortlog --summary --numbered --no-merges`
        # Please submit a pull request if you would like to include your
        # email address in the about screen.
        # See the `generate-about` script in the "todo" branch.
        # vim :read! ./Meta/generate-about
        dict(name='Daniel Harding', title=N_('Developer')),
        dict(name='Ｖ字龍(Vdragon)', title=N_('Developer')),
        dict(name='Guillaume de Bure', title=N_('Developer')),
        dict(name='Alex Chernetz', title=N_('Developer')),
        dict(name='Uri Okrent', title=N_('Developer')),
        dict(name='Thomas Kluyver', title=N_('Developer')),
        dict(name='Minarto Margoliono', title=N_('Developer')),
        dict(name='Andreas Sommer', title=N_('Developer')),
        dict(name='Stanislaw Halik', title=N_('Developer')),
        dict(name='Igor Galarraga', title=N_('Developer')),
        dict(name='Virgil Dupras', title=N_('Developer')),
        dict(name='Barry Roberts', title=N_('Developer')),
        dict(name='Stefan Naewe', title=N_('Developer')),
        dict(name='Ville Skyttä', title=N_('Developer')),
        dict(name='Benedict Lee', title=N_('Developer')),
        dict(name='Steffen Prohaska', title=N_('Developer')),
        dict(name='Michael Geddes', title=N_('Developer')),
        dict(name='Rustam Safin', title=N_('Developer')),
        dict(name='David Martínez Martí', title=N_('Developer')),
        dict(name='Justin Lecher', title=N_('Developer')),
        dict(name='Karl Bielefeldt', title=N_('Developer')),
        dict(name='Marco Costalba', title=N_('Developer')),
        dict(name='Michael Homer', title=N_('Developer')),
        dict(name='Sven Claussner', title=N_('Developer')),
        dict(name='v.paritskiy', title=N_('Developer')),
        dict(name='Adrien be', title=N_('Developer')),
        dict(name='Audrius Karabanovas', title=N_('Developer')),
        dict(name='Ben Boeckel', title=N_('Developer')),
        dict(name='Boris W', title=N_('Developer')),
        dict(name='Charles', title=N_('Developer')),
        dict(name='Clément Pit--Claudel', title=N_('Developer')),
        dict(name='Daniel Haskin', title=N_('Developer')),
        dict(name='Daniel King', title=N_('Developer')),
        dict(name='Daniel Pavel', title=N_('Developer')),
        dict(name='David Zumbrunnen', title=N_('Developer')),
        dict(name='George Vasilakos', title=N_('Developer')),
        dict(name='Ilya Tumaykin', title=N_('Developer')),
        dict(name='Iulian Udrea', title=N_('Developer')),
        dict(name='Jake Biesinger', title=N_('Developer')),
        dict(name='Jamie Pate', title=N_('Developer')),
        dict(name='Karthik Manamcheri', title=N_('Developer')),
        dict(name='Kelvie Wong', title=N_('Developer')),
        dict(name='Maciej Filipiak', title=N_('Developer')),
        dict(name='Maicon D. Filippsen', title=N_('Developer')),
        dict(name='Markus Heidelberg', title=N_('Developer')),
        dict(name='Matthew E. Levine', title=N_('Developer')),
        dict(name='Md. Mahbub Alam', title=N_('Developer')),
        dict(name='Mikhail Terekhov', title=N_('Developer')),
        dict(name='Paul Hildebrandt', title=N_('Developer')),
        dict(name='Paul Weingardt', title=N_('Developer')),
        dict(name='Paulo Fidalgo', title=N_('Developer')),
        dict(name='Philip Stark', title=N_('Developer')),
        dict(name='Rolando Espinoza', title=N_('Developer')),
        dict(name="Samsul Ma'arif", title=N_('Developer')),
        dict(name='Sebastian Brass', title=N_('Developer')),
        dict(name='Sebastian Schuberth', title=N_('Developer')),
        dict(name='Vaibhav Sagar', title=N_('Developer')),
        dict(name='Ved Vyas', title=N_('Developer')),
        dict(name='Voicu Hodrea', title=N_('Developer')),
        dict(name='Wesley Wong', title=N_('Developer')),
        dict(name='Wolfgang Ocker', title=N_('Developer')),
        dict(name='ZH', title=N_('Developer')),
        dict(name='aj-bagwell', title=N_('Developer')),
    )
    return contributors_text(authors)


def translators_text():
    palette = QtGui.QPalette()
    contact = N_('Email contributor')
    email = lambda addr: mailto(addr, contact, palette)

    translators = (
        dict(name='Barış ÇELİK',
             email=email('bariscelikweb@gmail.com'),
             title=N_('Turkish translation')),
        dict(name='Łukasz Wojniłowicz',
             email=email('lukasz.wojnilowicz@gmail.com'),
             title=N_('Polish translation')),
        dict(name='Minarto Margoliono',
             email=email('lie.r.min.g@gmail.com'),
             title=N_('Indonesian translation')),
        dict(name='Peter Dave Hello',
             title=N_('Traditional Chinese (Taiwan) translation')),
        dict(name='Pilar Molina Lopez',
             email=email('pilarmolinalopez@gmail.com'),
             title=N_('Spanish translation')),
        dict(name="Samsul Ma'arif",
             email=email('samsul@samsul.web.id'),
             title=N_('Indonesian translation')),
        dict(name='Sven Claussner',
             email=email('sclaussner@src.gnome.org'),
             title=N_('German translation')),
        dict(name='Vaiz',
             email=email('vaizerd@gmail.com'),
             title=N_('Russian translation')),
        dict(name='Ｖ字龍(Vdragon)',
             email=email('Vdragon.Taiwan@gmail.com'),
             title=N_('Traditional Chinese (Taiwan) translation')),
        dict(name='Vitor Lobo',
             email=email('lobocode@gmail.com'),
             title=N_('Brazilian translation')),
        dict(name='Zhang Han',
             email=email('zhanghan@gmx.cn'),
             title=N_('Chinese translation')),
        dict(name='Zeioth',
             email=email('Zeioth@hotmail.com'),
             title=N_('Spanish translation')),
    )
    return contributors_text(translators)


def show_shortcuts():
    hotkeys_html = resources.doc(N_('hotkeys.html'))
    try:
        from qtpy import QtWebEngineWidgets
    except ImportError:
        # redhat disabled QtWebKit in their qt build but don't punish the users
        webbrowser.open_new_tab('file://' + hotkeys_html)
        return

    html = core.read(hotkeys_html)

    parent = qtutils.active_window()
    widget = QtWidgets.QDialog()
    widget.setWindowModality(Qt.WindowModal)
    widget.setWindowTitle(N_('Shortcuts'))

    web = QtWebEngineWidgets.QWebEngineView(parent)
    web.setHtml(html)

    layout = qtutils.hbox(defs.no_margin, defs.spacing, web)
    widget.setLayout(layout)
    widget.resize(800, min(parent.height(), 600))
    qtutils.add_action(widget, N_('Close'), widget.accept,
                       hotkeys.QUESTION, *hotkeys.ACCEPT)
    widget.show()
    widget.exec_()
