# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals
import platform
import webbrowser
import sys

import qtpy
from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy import QtWidgets

from ..i18n import N_
from .. import core
from .. import resources
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import version
from . import defs


def about_dialog(context):
    """Launches the Help -> About dialog"""
    view = AboutView(context, qtutils.active_window())
    view.show()
    return view


class ExpandingTabBar(QtWidgets.QTabBar):
    """A TabBar with tabs that expand to fill the empty space

    The setExpanding(True) method does not work in practice because
    it respects the OS style.  We override the style by implementing
    tabSizeHint() so that we can specify the size explicitly.

    """

    def tabSizeHint(self, tab_index):
        width = self.parent().width() / max(1, self.count()) - 1
        size = super(ExpandingTabBar, self).tabSizeHint(tab_index)
        size.setWidth(width)
        return size


class ExpandingTabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(ExpandingTabWidget, self).__init__(parent)
        self.setTabBar(ExpandingTabBar(self))

    def resizeEvent(self, event):
        """Forward resize events to the ExpandingTabBar"""
        # Qt does not resize the tab bar when the dialog is resized
        # so manually forward resize events to the tab bar.
        width = event.size().width()
        height = self.tabBar().height()
        self.tabBar().resize(width, height)
        return super(ExpandingTabWidget, self).resizeEvent(event)


class AboutView(QtWidgets.QDialog):
    """Provides the git-cola 'About' dialog"""

    def __init__(self, context, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.context = context
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
        self.version = qtutils.textbrowser(text=version_text(context))
        self.authors = qtutils.textbrowser(text=authors_text())
        self.translators = qtutils.textbrowser(text=translators_text())

        self.tabs = ExpandingTabWidget()
        self.tabs.addTab(self.text, N_('About'))
        self.tabs.addTab(self.version, N_('Version'))
        self.tabs.addTab(self.authors, N_('Authors'))
        self.tabs.addTab(self.translators, N_('Translators'))

        self.close_button = qtutils.close_button()
        self.close_button.setDefault(True)

        self.logo_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.logo_label,
            self.logo_text_label,
            qtutils.STRETCH,
        )

        self.button_layout = qtutils.hbox(
            defs.spacing, defs.margin, qtutils.STRETCH, self.close_button
        )

        self.main_layout = qtutils.vbox(
            defs.no_margin,
            defs.spacing,
            self.logo_layout,
            self.tabs,
            self.button_layout,
        )
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.close_button, self.accept)

        self.resize(defs.scale(600), defs.scale(720))


def copyright_text():
    return """
Git Cola: The highly caffeinated Git GUI

Copyright (C) 2007-2020 David Aguilar and contributors

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


def version_text(context):
    git_version = version.git_version(context)
    cola_version = version.version()
    build_version = version.build_version()
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

    # Only show the build version if _build_version.py exists
    if build_version:
        build_version = '(%s)' % build_version
    else:
        build_version = ''

    scope = dict(
        cola_version=cola_version,
        build_version=build_version,
        git_version=git_version,
        platform_version=platform_version,
        pyqt_api_name=pyqt_api_name,
        pyqt_api_version=pyqt_api_version,
        python_path=python_path,
        python_version=python_version,
        qt_version=qt_version,
        qtpy_version=qtpy_version,
    )

    return (
        N_(
            """
        <br>
            Git Cola version %(cola_version)s %(build_version)s
        <ul>
            <li> %(platform_version)s
            <li> Python (%(python_path)s) %(python_version)s
            <li> Git %(git_version)s
            <li> Qt %(qt_version)s
            <li> QtPy %(qtpy_version)s
            <li> %(pyqt_api_name)s %(pyqt_api_version)s
        </ul>
    """
        )
        % scope
    )


def link(url, text, palette=None):
    if palette is None:
        palette = QtGui.QPalette()

    color = palette.color(QtGui.QPalette.Foreground)
    rgb = 'rgb(%s, %s, %s)' % (color.red(), color.green(), color.blue())
    scope = dict(rgb=rgb, text=text, url=url)

    return (
        """
        <a style="font-style: italic; text-decoration: none; color: %(rgb)s;"
            href="%(url)s">
            %(text)s
        </a>
    """
        % scope
    )


def mailto(email, text, palette):
    return link('mailto:%s' % email, text, palette) + '<br>'


def render_authors(authors):
    """Render a list of author details into richtext html"""
    for x in authors:
        x.setdefault('email', '')

    entries = [
        (
            """
        <p>
            <strong>%(name)s</strong><br>
            <em>%(title)s</em><br>
            %(email)s
        </p>
    """
            % author
        )
        for author in authors
    ]

    return ''.join(entries)


def contributors_text(authors, prelude='', epilogue=''):
    author_text = render_authors(authors)
    scope = dict(author_text=author_text, epilogue=epilogue, prelude=prelude)

    return (
        """
        %(prelude)s
        %(author_text)s
        %(epilogue)s
    """
        % scope
    )


def authors_text():
    palette = QtGui.QPalette()
    contact = N_('Email contributor')
    authors = (
        # The names listed here are listed in the same order as
        # `git shortlog --summary --numbered --no-merges`
        # Please submit a pull request if you would like to include your
        # email address in the about screen.
        # See the `generate-about` script in the "todo" branch.
        # vim :read! ./Meta/generate-about
        dict(
            name='David Aguilar',
            title=N_('Maintainer (since 2007) and developer'),
            email=mailto('davvid@gmail.com', contact, palette),
        ),
        dict(name='Daniel Harding', title=N_('Developer')),
        dict(
            name='Ｖ字龍(Vdragon)',
            title=N_('Developer'),
            email=mailto('Vdragon.Taiwan@gmail.com', contact, palette),
        ),
        dict(name='Efimov Vasily', title=N_('Developer')),
        dict(name='Guillaume de Bure', title=N_('Developer')),
        dict(name='Uri Okrent', title=N_('Developer')),
        dict(name='Javier Rodriguez Cuevas', title=N_('Developer')),
        dict(name='Alex Chernetz', title=N_('Developer')),
        dict(name='xhl', title=N_('Developer')),
        dict(name='Andreas Sommer', title=N_('Developer')),
        dict(name='Thomas Kluyver', title=N_('Developer')),
        dict(name='Minarto Margoliono', title=N_('Developer')),
        dict(name='Ville Skyttä', title=N_('Developer')),
        dict(name='Szymon Judasz', title=N_('Developer')),
        dict(name='jm4R', title=N_('Developer')),
        dict(name='Stanislaw Halik', title=N_('Developer')),
        dict(name='Igor Galarraga', title=N_('Developer')),
        dict(name='Virgil Dupras', title=N_('Developer')),
        dict(name='wsdfhjxc', title=N_('Developer')),
        dict(name='Barry Roberts', title=N_('Developer')),
        dict(name='林博仁(Buo-ren Lin)', title=N_('Developer')),
        dict(name='Guo Yunhe', title=N_('Developer')),
        dict(name='cclauss', title=N_('Developer')),
        dict(name='Stefan Naewe', title=N_('Developer')),
        dict(name='Victor Nepveu', title=N_('Developer')),
        dict(name='Pavel Rehak', title=N_('Developer')),
        dict(name='Benedict Lee', title=N_('Developer')),
        dict(name='Tim Brown', title=N_('Developer')),
        dict(name='Steffen Prohaska', title=N_('Developer')),
        dict(name='Filip Danilović', title=N_('Developer')),
        dict(name='NotSqrt', title=N_('Developer')),
        dict(name='Michael Geddes', title=N_('Developer')),
        dict(name='Rustam Safin', title=N_('Developer')),
        dict(name='Justin Lecher', title=N_('Developer')),
        dict(name='Alex Gulyás', title=N_('Developer')),
        dict(name='David Martínez Martí', title=N_('Developer')),
        dict(name='Hualiang Xie', title=N_('Developer')),
        dict(name='Kai Krakow', title=N_('Developer')),
        dict(name='Karl Bielefeldt', title=N_('Developer')),
        dict(name='Marco Costalba', title=N_('Developer')),
        dict(name='Michael Homer', title=N_('Developer')),
        dict(name='Sebastian Schuberth', title=N_('Developer')),
        dict(name='Sven Claussner', title=N_('Developer')),
        dict(name='Victor Gambier', title=N_('Developer')),
        dict(name='bsomers', title=N_('Developer')),
        dict(name='real', title=N_('Developer')),
        dict(name='v.paritskiy', title=N_('Developer')),
        dict(name='vanderkoort', title=N_('Developer')),
        dict(name='wm4', title=N_('Developer')),
        dict(name='Audrius Karabanovas', title=N_('Developer')),
        dict(name='Matthew E. Levine', title=N_('Developer')),
        dict(name='Matthias Mailänder', title=N_('Developer')),
        dict(name='Md. Mahbub Alam', title=N_('Developer')),
        dict(name='Jakub Szymański', title=N_('Developer')),
        dict(name='ochristi', title=N_('Developer')),
        dict(name='Miguel Boekhold', title=N_('Developer')),
        dict(name='MiguelBoekhold', title=N_('Developer')),
        dict(name='Mikhail Terekhov', title=N_('Developer')),
        dict(name='Jake Biesinger', title=N_('Developer')),
        dict(name='Iulian Udrea', title=N_('Developer')),
        dict(name='Paul Hildebrandt', title=N_('Developer')),
        dict(name='Paul Weingardt', title=N_('Developer')),
        dict(name='Paulo Fidalgo', title=N_('Developer')),
        dict(name='Ilya Tumaykin', title=N_('Developer')),
        dict(name='Petr Gladkikh', title=N_('Developer')),
        dict(name='Philip Stark', title=N_('Developer')),
        dict(name='Radek Postołowicz', title=N_('Developer')),
        dict(name='Rainer Müller', title=N_('Developer')),
        dict(name='Ricardo J. Barberis', title=N_('Developer')),
        dict(name='Rolando Espinoza', title=N_('Developer')),
        dict(name='George Vasilakos', title=N_('Developer')),
        dict(name="Samsul Ma'arif", title=N_('Developer')),
        dict(name='Sebastian Brass', title=N_('Developer')),
        dict(name='Arthur Coelho', title=N_('Developer')),
        dict(name='Simon Peeters', title=N_('Developer')),
        dict(name='Felipe Morales', title=N_('Developer')),
        dict(name='David Zumbrunnen', title=N_('Developer')),
        dict(name='David Schwörer', title=N_('Developer')),
        dict(name='Stephen', title=N_('Developer')),
        dict(name='Andrej', title=N_('Developer')),
        dict(name='Daniel Pavel', title=N_('Developer')),
        dict(name='Daniel King', title=N_('Developer')),
        dict(name='Daniel Haskin', title=N_('Developer')),
        dict(name='Clément Pit--Claudel', title=N_('Developer')),
        dict(name='Vaibhav Sagar', title=N_('Developer')),
        dict(name='Ved Vyas', title=N_('Developer')),
        dict(name='Adrien be', title=N_('Developer')),
        dict(name='Charles', title=N_('Developer')),
        dict(name='Boris W', title=N_('Developer')),
        dict(name='Ben Boeckel', title=N_('Developer')),
        dict(name='Voicu Hodrea', title=N_('Developer')),
        dict(name='Wesley Wong', title=N_('Developer')),
        dict(name='Wolfgang Ocker', title=N_('Developer')),
        dict(name='Zhang Han', title=N_('Developer')),
        dict(name='beauxq', title=N_('Developer')),
        dict(name='Jamie Pate', title=N_('Developer')),
        dict(name='Jean-Francois Dagenais', title=N_('Developer')),
        dict(name='Joachim Lusiardi', title=N_('Developer')),
        dict(name='0xflotus', title=N_('Developer')),
        dict(name='AJ Bagwell', title=N_('Developer')),
        dict(name='Barrett Lowe', title=N_('Developer')),
        dict(name='Karthik Manamcheri', title=N_('Developer')),
        dict(name='Kelvie Wong', title=N_('Developer')),
        dict(name='Kyle', title=N_('Developer')),
        dict(name='Maciej Filipiak', title=N_('Developer')),
        dict(name='Maicon D. Filippsen', title=N_('Developer')),
        dict(name='Markus Heidelberg', title=N_('Developer')),
    )
    bug_url = 'https://github.com/git-cola/git-cola/issues'
    bug_link = link(bug_url, bug_url)
    scope = dict(bug_link=bug_link)
    prelude = (
        N_(
            """
        <br>
        Please use %(bug_link)s to report issues.
        <br>
    """
        )
        % scope
    )

    return contributors_text(authors, prelude=prelude)


def translators_text():
    palette = QtGui.QPalette()
    contact = N_('Email contributor')

    translators = (
        # See the `generate-about` script in the "todo" branch.
        # vim :read! ./Meta/generate-about --translators
        dict(
            name='Ｖ字龍(Vdragon)',
            title=N_('Traditional Chinese (Taiwan) translation'),
            email=mailto('Vdragon.Taiwan@gmail.com', contact, palette),
        ),
        dict(name='Pavel Rehak', title=N_('Czech translation')),
        dict(name='Zhang Han', title=N_('Simplified Chinese translation')),
        dict(name='Victorhck', title=N_('Spanish translation')),
        dict(name='Vitor Lobo', title=N_('Brazilian translation')),
        dict(name='Igor Kopach', title=N_('Ukranian translation')),
        dict(name='Łukasz Wojniłowicz', title=N_('Polish translation')),
        dict(name='Rafael Nascimento', title=N_('Brazilian translation')),
        dict(name='Barış ÇELİK', title=N_('Turkish translation')),
        dict(name='Minarto Margoliono', title=N_('Indonesian translation')),
        dict(name='Sven Claussner', title=N_('German translation')),
        dict(name='Shun Sakai', title=N_('Japanese translation')),
        dict(name='Vaiz', title=N_('Russian translation')),
        dict(name='adlgrbz', title=N_('Turkish translation')),
        dict(name='fu7mu4', title=N_('Japanese translation')),
        dict(name='Guo Yunhe', title=N_('Simplified Chinese translation')),
        dict(name="Samsul Ma'arif", title=N_('Indonesian translation')),
        dict(name='Gyuris Gellért', title=N_('Hungarian translation')),
        dict(name='Joachim Lusiardi', title=N_('German translation')),
        dict(name='Kai Krakow', title=N_('German translation')),
        dict(name='Louis Rousseau', title=N_('French translation')),
        dict(name='Mickael Albertus', title=N_('French translation')),
        dict(
            name='Peter Dave Hello',
            title=N_('Traditional Chinese (Taiwan) translation'),
        ),
        dict(name='Pilar Molina Lopez', title=N_('Spanish translation')),
        dict(name='Rafael Reuber', title=N_('Brazilian translation')),
        dict(name='Sabri Ünal', title=N_('Turkish translation')),
        dict(name='Balázs Meskó', title=N_('Translation')),
        dict(name='Zeioth', title=N_('Spanish translation')),
        dict(name='balping', title=N_('Hungarian translation')),
        dict(name='p-bo', title=N_('Czech translation')),
        dict(
            name='林博仁(Buo-ren Lin)',
            title=N_('Traditional Chinese (Taiwan) translation'),
        ),
    )

    bug_url = 'https://github.com/git-cola/git-cola/issues'
    bug_link = link(bug_url, bug_url)
    scope = dict(bug_link=bug_link)

    prelude = (
        N_(
            """
        <br>
            Git Cola has been translated into different languages thanks
            to the help of the individuals listed below.

        <br>
        <p>
            Translation is approximate.  If you find a mistake,
            please let us know by opening an issue on Github:
        </p>

        <p>
            %(bug_link)s
        </p>

        <br>
        <p>
            We invite you to participate in translation by adding or updating
            a translation and opening a pull request.
        </p>

        <br>

    """
        )
        % scope
    )
    return contributors_text(translators, prelude=prelude)


def show_shortcuts():
    hotkeys_html = resources.doc(N_('hotkeys.html'))
    try:
        from qtpy import QtWebEngineWidgets  # pylint: disable=all
    except (ImportError, qtpy.PythonQtError):
        # redhat disabled QtWebKit in their qt build but don't punish the users
        webbrowser.open_new_tab('file://' + hotkeys_html)
        return

    html = core.read(hotkeys_html)

    parent = qtutils.active_window()
    widget = QtWidgets.QDialog(parent)
    widget.setWindowModality(Qt.WindowModal)
    widget.setWindowTitle(N_('Shortcuts'))

    web = QtWebEngineWidgets.QWebEngineView()
    web.setHtml(html)

    layout = qtutils.hbox(defs.no_margin, defs.spacing, web)
    widget.setLayout(layout)
    widget.resize(800, min(parent.height(), 600))
    qtutils.add_action(
        widget, N_('Close'), widget.accept, hotkeys.QUESTION, *hotkeys.ACCEPT
    )
    widget.show()
    widget.exec_()
