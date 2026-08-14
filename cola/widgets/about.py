import platform
import sys
import webbrowser

import qtpy
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import core
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import resources
from .. import utils
from .. import version
from ..i18n import N_
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
        width = self.parent().width() // max(2, self.count()) - 1
        size = super().tabSizeHint(tab_index)
        size.setWidth(width)
        return size


class ExpandingTabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(ExpandingTabBar(self))

    def resizeEvent(self, event):
        """Forward resize events to the ExpandingTabBar"""
        # Qt does not resize the tab bar when the dialog is resized
        # so manually forward resize events to the tab bar.
        width = event.size().width()
        height = self.tabBar().height()
        self.tabBar().resize(width, height)
        return super().resizeEvent(event)


class AboutView(QtWidgets.QDialog):
    """Provides the git-cola 'About' dialog"""

    def __init__(self, context, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.context = context
        self.setWindowTitle(N_('About git-cola'))
        self.setWindowModality(Qt.WindowModal)

        # Top-most large icon
        self.logo_label = qtutils.pixmap_label(icons.cola(), defs.huge_icon)
        self.logo_label.setAlignment(Qt.AlignCenter)

        self.logo_text_label = qtutils.label(text='Git Cola')
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

Copyright (C) 2007-2024 David Aguilar and contributors

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
    python_path = sys.executable
    python_version = sys.version
    qt_version = qtpy.QT_VERSION
    qtpy_version = qtpy.__version__
    pyqt_api_name = qtpy.API_NAME
    if (
        getattr(qtpy, 'PYQT6', False)
        or getattr(qtpy, 'PYQT5', False)
        or getattr(qtpy, 'PYQT4', False)
    ):
        pyqt_api_version = qtpy.PYQT_VERSION
    elif qtpy.PYSIDE:
        pyqt_api_version = qtpy.PYSIDE_VERSION
    else:
        pyqt_api_version = 'unknown'

    platform_version = platform.platform()

    scope = {
        'cola_version': cola_version,
        'git_version': git_version,
        'platform_version': platform_version,
        'pyqt_api_name': pyqt_api_name,
        'pyqt_api_version': pyqt_api_version,
        'python_path': python_path,
        'python_version': python_version,
        'qt_version': qt_version,
        'qtpy_version': qtpy_version,
    }

    return (
        N_(
            """
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
    """
        )
        % scope
    )


def mailto(email, text, palette):
    return qtutils.link(f'mailto:{email}', text, palette) + '<br>'


def render_authors(authors):
    """Render a list of author details into rich text html"""
    for x in authors:
        x.setdefault('email', '')

    entries = [
        (
            """
        <p>
            <strong>{name}</strong><br>
            <em>{title}</em><br>
            {email}
        </p>
    """.format(
                **author
            )
        )
        for author in authors
    ]

    return ''.join(entries)


def contributors_text(authors, prelude='', epilogue=''):
    author_text = render_authors(authors)
    scope = {'author_text': author_text, 'epilogue': epilogue, 'prelude': prelude}

    return """
        {prelude}
        {author_text}
        {epilogue}
    """.format(
        **scope
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
        # vim :read! ./todo/generate-about
        {
            'name': 'David Aguilar',
            'title': N_('Maintainer (since 2007) and developer'),
            'email': mailto('davvid@gmail.com', contact, palette),
        },
        {'name': 'Daniel Harding', 'title': N_('Developer')},
        {'name': 'Efimov Vasily', 'title': N_('Developer')},
        {
            'name': 'Ｖ字龍(Vdragon)',
            'title': N_('Developer'),
            'email': mailto('Vdragon.Taiwan@gmail.com', contact, palette),
        },
        {'name': 'Ahrirg', 'title': N_('Developer')},
        {'name': 'Kurt McKee', 'title': N_('Developer')},
        {'name': 'Guillaume de Bure', 'title': N_('Developer')},
        {'name': 'Povilas Kanapickas', 'title': N_('Developer')},
        {'name': 'Javier Rodriguez Cuevas', 'title': N_('Developer')},
        {'name': 'Uri Okrent', 'title': N_('Developer')},
        {'name': 'Ville Skyttä', 'title': N_('Developer')},
        {'name': 'Alex Chernetz', 'title': N_('Developer')},
        {'name': 'xhl', 'title': N_('Developer')},
        {'name': 'Thomas Kluyver', 'title': N_('Developer')},
        {'name': 'Andreas Sommer', 'title': N_('Developer')},
        {'name': 'nakanoi', 'title': N_('Developer')},
        {'name': 'Szymon Judasz', 'title': N_('Developer')},
        {'name': 'jm4R', 'title': N_('Developer')},
        {'name': 'Minarto Margoliono', 'title': N_('Developer')},
        {'name': 'Stanislaw Halik', 'title': N_('Developer')},
        {'name': '林博仁(Buo-ren Lin)', 'title': N_('Developer')},
        {'name': 'Katsuhiko Takahashi', 'title': N_('Developer')},
        {'name': 'Igor Galarraga', 'title': N_('Developer')},
        {'name': 'Luke Horwell', 'title': N_('Developer')},
        {'name': 'Virgil Dupras', 'title': N_('Developer')},
        {'name': 'Barry Roberts', 'title': N_('Developer')},
        {'name': 'wsdfhjxc', 'title': N_('Developer')},
        {'name': 'Guo Yunhe', 'title': N_('Developer')},
        {'name': 'malpas', 'title': N_('Developer')},
        {'name': 'Matthias Mailänder', 'title': N_('Developer')},
        {'name': 'cclauss', 'title': N_('Developer')},
        {'name': 'Benjamin Somers', 'title': N_('Developer')},
        {'name': 'Josh Taylor', 'title': N_('Developer')},
        {'name': 'Max Harmathy', 'title': N_('Developer')},
        {'name': 'Stefan Naewe', 'title': N_('Developer')},
        {'name': 'Victor Nepveu', 'title': N_('Developer')},
        {'name': 'Benedict Lee', 'title': N_('Developer')},
        {'name': 'Filip Danilović', 'title': N_('Developer')},
        {'name': 'Nanda Lopes', 'title': N_('Developer')},
        {'name': 'NotSqrt', 'title': N_('Developer')},
        {'name': 'Pavel Rehak', 'title': N_('Developer')},
        {'name': 'Steffen Prohaska', 'title': N_('Developer')},
        {'name': 'Thomas Kiley', 'title': N_('Developer')},
        {'name': 'Tim Brown', 'title': N_('Developer')},
        {'name': 'Chris Stefano', 'title': N_('Developer')},
        {'name': 'Floris Lambrechts', 'title': N_('Developer')},
        {'name': 'Martin Gysel', 'title': N_('Developer')},
        {'name': 'Michael Geddes', 'title': N_('Developer')},
        {'name': 'Rustam Safin', 'title': N_('Developer')},
        {'name': 'abid1998', 'title': N_('Developer')},
        {'name': 'Alex Gulyás', 'title': N_('Developer')},
        {'name': 'David Martínez Martí', 'title': N_('Developer')},
        {'name': 'Hualiang Xie', 'title': N_('Developer')},
        {'name': 'Ihor', 'title': N_('Developer')},
        {'name': 'Jan Kurella', 'title': N_('Developer')},
        {'name': 'Justin Lecher', 'title': N_('Developer')},
        {'name': 'Kai Krakow', 'title': N_('Developer')},
        {'name': 'Karl Bielefeldt', 'title': N_('Developer')},
        {'name': 'Marco Costalba', 'title': N_('Developer')},
        {'name': 'Michael Baumgartner', 'title': N_('Developer')},
        {'name': 'Michael Homer', 'title': N_('Developer')},
        {'name': 'Mithil Poojary', 'title': N_('Developer')},
        {'name': 'Sven Claussner', 'title': N_('Developer')},
        {'name': 'Victor Gambier', 'title': N_('Developer')},
        {'name': 'bsomers', 'title': N_('Developer')},
        {'name': 'legasik21', 'title': N_('Developer')},
        {'name': 'mmargoliono', 'title': N_('Developer')},
        {'name': 'v.paritskiy', 'title': N_('Developer')},
        {'name': 'vanderkoort', 'title': N_('Developer')},
        {'name': 'wm4', 'title': N_('Developer')},
        {'name': '0xflotus', 'title': N_('Developer')},
        {'name': 'AJ Bagwell', 'title': N_('Developer')},
        {'name': 'Adrien be', 'title': N_('Developer')},
        {'name': 'Alexander Preißner', 'title': N_('Developer')},
        {'name': 'Andrej', 'title': N_('Developer')},
        {'name': 'Arnaud Henry', 'title': N_('Developer')},
        {'name': 'Arthur Coelho', 'title': N_('Developer')},
        {'name': 'Audrius Karabanovas', 'title': N_('Developer')},
        {'name': 'Axel Heider', 'title': N_('Developer')},
        {'name': 'Barrett Lowe', 'title': N_('Developer')},
        {'name': 'Ben Boeckel', 'title': N_('Developer')},
        {'name': 'Bob van der Linden', 'title': N_('Developer')},
        {'name': 'Boerje Sewing', 'title': N_('Developer')},
        {'name': 'Boris W', 'title': N_('Developer')},
        {'name': 'Bruno Cabral', 'title': N_('Developer')},
        {'name': 'Charles', 'title': N_('Developer')},
        {'name': 'Christoph Erhardt', 'title': N_('Developer')},
        {'name': 'Clément Pit--Claudel', 'title': N_('Developer')},
        {'name': 'Daniel Haskin', 'title': N_('Developer')},
        {'name': 'Daniel King', 'title': N_('Developer')},
        {'name': 'Daniel Pavel', 'title': N_('Developer')},
        {'name': 'DasaniT', 'title': N_('Developer')},
        {'name': 'Dave Cottlehuber', 'title': N_('Developer')},
        {'name': 'David Schwörer', 'title': N_('Developer')},
        {'name': 'David Zumbrunnen', 'title': N_('Developer')},
        {'name': 'George Vasilakos', 'title': N_('Developer')},
        {'name': 'Ilya Tumaykin', 'title': N_('Developer')},
        {'name': 'Iulian Udrea', 'title': N_('Developer')},
        {'name': 'Jake Biesinger', 'title': N_('Developer')},
        {'name': 'Jakub Szymański', 'title': N_('Developer')},
        {'name': 'Jamie Pate', 'title': N_('Developer')},
        {'name': 'Jean-Francois Dagenais', 'title': N_('Developer')},
        {'name': 'Joachim Lusiardi', 'title': N_('Developer')},
        {'name': 'Karthik Manamcheri', 'title': N_('Developer')},
        {'name': 'Kelvie Wong', 'title': N_('Developer')},
        {'name': 'Klaas Neirinck', 'title': N_('Developer')},
        {'name': 'Kyle', 'title': N_('Developer')},
        {'name': 'Laszlo Boszormenyi (GCS)', 'title': N_('Developer')},
        {'name': 'Maciej Filipiak', 'title': N_('Developer')},
        {'name': 'Maicon D. Filippsen', 'title': N_('Developer')},
        {'name': 'Markus Heidelberg', 'title': N_('Developer')},
        {'name': 'Matthew E. Levine', 'title': N_('Developer')},
        {'name': 'Md. Mahbub Alam', 'title': N_('Developer')},
        {'name': 'Mikhail Terekhov', 'title': N_('Developer')},
        {'name': 'Niel Buys', 'title': N_('Developer')},
        {'name': 'Oleg', 'title': N_('Developer')},
        {'name': 'Ori shalhon', 'title': N_('Developer')},
        {'name': 'Paul Hildebrandt', 'title': N_('Developer')},
        {'name': 'Paul Weingardt', 'title': N_('Developer')},
        {'name': 'Paulo Fidalgo', 'title': N_('Developer')},
        {'name': 'Petr Gladkikh', 'title': N_('Developer')},
        {'name': 'Philip Stark', 'title': N_('Developer')},
        {'name': 'Radek Postołowicz', 'title': N_('Developer')},
        {'name': 'Rainer Müller', 'title': N_('Developer')},
        {'name': 'Ricardo J. Barberis', 'title': N_('Developer')},
        {'name': 'Rolando Espinoza', 'title': N_('Developer')},
        {'name': 'Sabri Ünal', 'title': N_('Developer')},
        {'name': "Samsul Ma'arif", 'title': N_('Developer')},
        {'name': 'Sebastian Brass', 'title': N_('Developer')},
        {'name': 'Sergei Dyshel', 'title': N_('Developer')},
        {'name': 'Simon Peeters', 'title': N_('Developer')},
        {'name': 'Stephen', 'title': N_('Developer')},
        {'name': 'Tim Gates', 'title': N_('Developer')},
        {'name': 'Vaibhav Sagar', 'title': N_('Developer')},
        {'name': 'Ved Vyas', 'title': N_('Developer')},
        {'name': 'VishnuSanal', 'title': N_('Developer')},
        {'name': 'Voicu Hodrea', 'title': N_('Developer')},
        {'name': 'WNguyen14', 'title': N_('Developer')},
        {'name': 'Wesley Wong', 'title': N_('Developer')},
        {'name': 'William Wira', 'title': N_('Developer')},
        {'name': 'Wolfgang Ocker', 'title': N_('Developer')},
        {'name': 'Zhang Han', 'title': N_('Developer')},
        {'name': 'akhilsayshi', 'title': N_('Developer')},
        {'name': 'beauxq', 'title': N_('Developer')},
        {'name': 'bensmrs', 'title': N_('Developer')},
        {'name': 'lcjh', 'title': N_('Developer')},
        {'name': 'lefairy', 'title': N_('Developer')},
        {'name': 'melkecelioglu', 'title': N_('Developer')},
        {'name': 'ochristi', 'title': N_('Developer')},
        {'name': 'senique', 'title': N_('Developer')},
        {'name': 'yael levi', 'title': N_('Developer')},
        {'name': 'Łukasz Wojniłowicz', 'title': N_('Developer')},
    )
    bug_url = 'https://github.com/git-cola/git-cola/issues'
    bug_link = qtutils.link(bug_url, bug_url)
    scope = {'bug_link': bug_link}
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
        # vim :read! ./todo/generate-about --translators
        {
            'name': 'Ｖ字龍(Vdragon)',
            'title': N_('Traditional Chinese (Taiwan) translation'),
            'email': mailto('Vdragon.Taiwan@gmail.com', contact, palette),
        },
        {'name': 'Pavel Rehak', 'title': N_('Czech translation')},
        {'name': 'Samuel Amen Ague', 'title': N_('French translation')},
        {'name': 'Victorhck', 'title': N_('Spanish translation')},
        {'name': 'Łukasz Wojniłowicz', 'title': N_('Polish translation')},
        {'name': 'Vitor Lobo', 'title': N_('Brazilian translation')},
        {'name': 'Zhang Han', 'title': N_('Simplified Chinese translation')},
        {'name': 'fu7mu4', 'title': N_('Japanese translation')},
        {'name': 'Igor Kopach', 'title': N_('Ukrainian translation')},
        {
            'name': '林博仁(Buo-ren Lin)',
            'title': N_('Traditional Chinese (Taiwan) translation'),
        },
        {'name': 'Gyuris Gellért', 'title': N_('Hungarian translation')},
        {'name': 'Barış ÇELİK', 'title': N_('Turkish translation')},
        {'name': 'Efimov Vasily', 'title': N_('Translation')},
        {'name': 'Guo Yunhe', 'title': N_('Simplified Chinese translation')},
        {'name': 'Luke Horwell', 'title': N_('Translation')},
        {'name': 'Minarto Margoliono', 'title': N_('Indonesian translation')},
        {'name': 'PushKK', 'title': N_('Russian translation')},
        {'name': 'Rafael Nascimento', 'title': N_('Brazilian translation')},
        {'name': 'Rafael Reuber', 'title': N_('Brazilian translation')},
        {'name': 'Shun Sakai', 'title': N_('Japanese translation')},
        {'name': 'Sven Claussner', 'title': N_('German translation')},
        {'name': 'Vaiz', 'title': N_('Russian translation')},
        {'name': 'adlgrbz', 'title': N_('Turkish translation')},
        {'name': 'Balázs Meskó', 'title': N_('Translation')},
        {'name': 'Joachim Lusiardi', 'title': N_('German translation')},
        {'name': 'K.T.', 'title': N_('Japanese translation')},
        {'name': 'Kai Krakow', 'title': N_('German translation')},
        {'name': 'Kisaragi Hiu', 'title': N_('Japanese translation')},
        {'name': 'Louis Rousseau', 'title': N_('French translation')},
        {'name': 'Mickael Albertus', 'title': N_('French translation')},
        {
            'name': 'Peter Dave Hello',
            'title': N_('Traditional Chinese (Taiwan) translation'),
        },
        {'name': 'Pilar Molina Lopez', 'title': N_('Spanish translation')},
        {'name': 'Sabri Ünal', 'title': N_('Turkish translation')},
        {'name': "Samsul Ma'arif", 'title': N_('Indonesian translation')},
        {'name': 'Stanislav', 'title': N_('Translation')},
        {'name': 'Tomo Dote', 'title': N_('Translation')},
        {'name': 'YAMAMOTO Kenyu', 'title': N_('Translation')},
        {'name': 'Zeioth', 'title': N_('Spanish translation')},
        {'name': 'balping', 'title': N_('Hungarian translation')},
        {'name': 'p-bo', 'title': N_('Czech translation')},
        {'name': 'தமிழ் நேரம்', 'title': N_('Translation')},
    )

    bug_url = 'https://github.com/git-cola/git-cola/issues'
    bug_link = qtutils.link(bug_url, bug_url)
    scope = {'bug_link': bug_link}

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
    hotkeys_html = resources.data_path(N_('hotkeys.html'))
    if utils.is_win32():
        hotkeys_url = 'file:///' + hotkeys_html.replace('\\', '/')
    else:
        hotkeys_url = 'file://' + hotkeys_html
    if not core.isfile(hotkeys_html):
        hotkeys_url = 'https://git-cola.gitlab.io/share/doc/git-cola/hotkeys.html'
        hotkeys_html = None
    try:
        from qtpy import QtWebEngineWidgets
    except (ImportError, qtpy.PythonQtError):
        # Redhat disabled QtWebKit in their Qt build but don't punish the users
        webbrowser.open_new_tab(hotkeys_url)
        return

    parent = qtutils.active_window()
    widget = QtWidgets.QDialog(parent)
    widget.setWindowModality(Qt.WindowModal)
    widget.setWindowTitle(N_('Shortcuts'))

    web = QtWebEngineWidgets.QWebEngineView()
    if hotkeys_html:
        with open(hotkeys_html, encoding='utf-8') as hotkeys_file:
            html = hotkeys_file.read()
        if utils.is_darwin():
            html = html.replace('Ctrl', 'Cmd')
        web.setHtml(html)
    else:
        web.setUrl(QtCore.QUrl(hotkeys_url))

    layout = qtutils.hbox(defs.no_margin, defs.spacing, web)
    widget.setLayout(layout)
    widget.resize(800, min(parent.height(), 600))
    qtutils.add_action(
        widget, N_('Close'), widget.accept, hotkeys.QUESTION, *hotkeys.ACCEPT
    )
    widget.show()
    widget.exec_()
