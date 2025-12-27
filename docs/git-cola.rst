========
git-cola
========

SYNOPSIS
========

``git cola [options] [sub-command]``


DESCRIPTION
===========

Git Cola is a sleek and powerful Git GUI.


OPTIONS
=======

``--amend``
-----------

Start `git cola` in amend mode.

``--prompt``
------------

Prompt for a Git repository.  Defaults to the current directory.

``-r, --repo <path>``
---------------------

Open the Git repository at `<path>`.  Defaults to the current directory.

``-s, --status-filter <filter>``
--------------------------------

Apply the path filter to the status widget.

``--version``
-------------

Print the `git cola` version and exit.

``-h, --help``
--------------

Show usage and optional arguments.

``--help-commands``
-------------------

Show available sub-commands.


SUB-COMMANDS
============

Run ``git cola --help-commands`` to list all sub-commands.

The following sub-commands can be launched directly from the command-line.
For example, ``git cola diff`` will launch the ``diff`` sub-command.

am
--

Apply patches. This sub-command is named after the ``git am`` command.
``git cola am`` is an entry point for the ``File > Patches > Apply Patches...``
main menu action.

archive
-------

Export tarballs from Git. ``git cola archive`` is an entry point for the
``File > Save As Tarball/Zip...`` main menu action.

branch
------

Create branches. ``git cola branch`` is an entry point for the ``Branch > Create...``
main menu action.

browse
------

Browse tracked files. ``git cola browse`` is an entry point for the
``View > File Browser...`` main menu action.

config
------

Configure settings. ``git cola config`` is an entry point for the
``File > Preferences`` main menu action.

dag
---

Start the ``git dag`` Git history browser. ``git cola dag`` is an entry point for the
``View > DAG...`` main menu action and can also be launched as ``git dag`` command.

diff
----

Diff changed files. ``git cola diff`` is an entry point for the ``Diff > Expression...``
main menu action.

fetch
-----

Fetch history from remote repositories. ``git cola fetch`` is an entry point for the
``Actions > Fetch...`` main menu action.

grep
----

Use `git grep` to search for content. ``git cola grep`` is an entry point for the
``Actions > Grep`` main menu action.

merge
-----

Merge branches. ``git cola merge`` is an entry point for the ``Actions > Merge...``
main menu action.

open
----

Launch the "Quick Open" dialog to open bookmarked and recently-opened repositories.

pull
----

Fetch and merge remote branches. ``git cola pull`` is an entry point for the
``Actions > Pull...`` main menu action.

push
----

Push branches to remotes. ``git cola push`` is an entry point for the
``Actions > Push...`` main menu action.

rebase
------

Start an interactive rebase. ``git cola rebase`` is an entry point for the
``Rebase > Start Interactive Rebase...`` main menu action.

remote
------

Create and edit remotes. ``git cola remote`` is an entry point for the
``File > Edit Remotes...`` main menu action.

search
------

Search for commits. ``git cola search`` is an entry point for the
``Actions > Search...`` main menu action.

stash
-----

Stash uncommitted modifications. ``git cola stash`` is an entry point for the
``Actions > Stash...`` main menu action.

tag
---

Create tags. ``git cola tag`` is an entry point for the ``Actions > Create Tag...``
main menu action.

version
-------

Print the Git Cola version. ``git cola version`` displays has options for printing
the current version in different formats. Version details about Git Cola and its
dependencies can also be found in the ``Help > About`` dialog's ``Version`` tab.


CONFIGURE YOUR EDITOR
=====================

The editor used by `Ctrl-e` is configured from the Preferences screen.

The following environment variables are consulted when no editor is configured.
If defined, the first of these variables is used:

* `GIT_VISUAL`
* `VISUAL`
* `GIT_EDITOR`
* `EDITOR`

The `*VISUAL` variables are consulted before the `*EDITOR` variables so that you can
configure a graphical editor independently of the editor used by the Git CLI.

*Pro Tip*: Configuring your editor to `gvim -f -p` will open multiple tabs
when editing files.  `gvim -f -o` uses splits.

`git cola` is {vim, emacs, textpad, notepad++}-aware.
When you select a line in the diff or grep screens and press any of
`Enter`, `Ctrl-e`, or the `Edit` button, you are taken to that exact line.

The editor preference is saved in the `gui.editor` variable using
`git config <https://git-scm.com/docs/git-config>`_.

The following are some recommend editor configurations.

* Neovim + Neovim-Qt

.. sourcecode:: sh

   git config --global core.editor nvim
   git config --global gui.editor 'nvim-qt --nofork'

* Vim + gvim

.. sourcecode:: sh

   git config --global core.editor vim
   git config --global gui.editor 'gvim -f'

* Sublime Text

.. sourcecode:: sh

   git config --global gui.editor 'subl --wait'


KEYBOARD SHORTCUTS
==================

`git cola` has many useful keyboard shortcuts.

Many of `git cola`'s editors understand vim-style hotkeys, e.g. `{h,j,k,l}`
for navigating in the diff, status, grep, and file browser widgets.

`{d,u}` move down/up one half page at a time (similar to vim's `ctrl-{d,u}`).
The `space` and `shift-space` hotkeys are mapped to the same operations.

`Shift-{j,k,d,u,f,b,page-up,page-down,left,right,up,down}` can be be used in
the diff editor to select lines while navigating.

`s` is a useful hotkey in the diff editor.  It stages/unstages the current
selection when a selection is present.  When nothing is selected, the
diff hunk at the current text cursor position is staged.  This makes it very
easy to review changes by selecting good hunks with `s` while navigating down
and over hunks that are not going to be staged.

`Ctrl-u` in the diff editor reverts unstaged edits, and respects the
selection.  This is useful for selectively reverted edits from the worktree.
This same hotkey reverts the entire file when used from the status tool.

`Ctrl-s` in the diff editor and status tools stages/unstages the entire file.

You can see the available shortcuts by pressing pressing the ``?`` key,
choosing ``Help > Keyboard shortcuts`` from the main menu,
or by consulting the `git cola keyboard shortcuts reference <https://git-cola.github.io/share/doc/git-cola/hotkeys.html>`_.


TOOLS
=====

The `git cola` interface is composed of various cooperating tools.
Double-clicking a tool opens it in its own subwindow.
Dragging it around moves and places it within the main window.

Tools can be hidden and rearranged however you like.
`git cola` carefully remembers your window layout and restores
it the next time it is launched.

The `Control-{1, 2, 3, ...}` hotkey gives focus to a specific tool.
A hidden tool can be re-opened using the `Tools` menu or
the `Shift+Control-{1, 2, 3, ...}` shortcut keys.

The Diff editor can be focused with `Ctrl-j`.
The Status tool can be focused with `Ctrl-k`.
The Commit tool can be focused with `Ctrl-l`.


.. _status:

STATUS
======

The `Status` tool provides a visual analog to the
`git status <https://git-scm.com/docs/git-status>`_ command.

`Status` displays files that are `modified` relative to the staging area,
`staged` for the next commit, `unmerged` files from an in-progress merge,
and files that are `untracked` to git.

These are the same categories one sees when running
`git status <https://git-scm.com/docs/git-status>`_
on the command line.

You can navigate through the list of files using keyboard arrows as well
as the ergonomic and vim-like `j` and `k` shortcut keys.

There are several convenient ways to interact with files in the `Status` tool.

Selecting a file displays its diff in the `Diff` viewer.
Double-clicking a file stages its contents, as does the `Ctrl-s` shortcut key.

`Ctrl-e` opens selected files in the configured editor, and
`Ctrl-d` opens selected files using `git difftool <https://git-scm.com/docs/git-difftool>`_

Additional actions can be performed using the right-click context menu.

Drag and Drop
-------------

Files can be dragged from the `Status` tool onto other applications.

Some terminals will treat a drag with multiple files by separating them with newlines,
which is less amenable for pasting command-line arguments.

To avoid this issue, hold down `Alt / Option` when dragging from the `Status` tool.
The drag and drop payload will no longer contain local file URLs -- it will contain
plain text that is amenable for use on a command-line.

Note: if drag and drop is not working and you are on Wayland then you may
need to ``export QT_QPA_PLATFORM=wayland`` in your environment.

Actions
-------

Clicking the `Staged` folder shows a diffstat for the index.

Clicking the `Modified` folder shows a diffstat for the worktree.

Clicking individual files sends diffs to the `Diff Display`.

Double-clicking individual files adds and removes their content from the index.

Various actions are available through the right-click context menu.
Different actions are available depending a file's status.

Stage Selected
~~~~~~~~~~~~~~

Add to the staging area using `git add <https://git-scm.com/docs/git-add>`_
Marks unmerged files as resolved.

Launch Editor
~~~~~~~~~~~~~

Launches the configured visual text editor

Launch Difftool
~~~~~~~~~~~~~~~

Visualize changes using ``git difftool``.

Revert Unstaged Edits
~~~~~~~~~~~~~~~~~~~~~

Reverts unstaged content by checking out selected paths
from the index/staging area

Revert Uncommitted Edits
~~~~~~~~~~~~~~~~~~~~~~~~

Throws away uncommitted edits

Unstage Selected
~~~~~~~~~~~~~~~~

Remove from the index/staging area with
`git reset <https://git-scm.com/docs/git-reset>`_

Launch Merge Tool
~~~~~~~~~~~~~~~~~

Resolve conflicts using `git mergetool <https://git-scm.com/docs/git-mergetool>`_.

Delete File(s)
~~~~~~~~~~~~~~

Delete untracked files from the filesystem.

Add to .gitignore
~~~~~~~~~~~~~~~~~

Adds untracked files to to the ``.gitignore`` file.


.. _diff:

DIFF
====

The diff viewer/editor displays diffs for selected files.
Additions are shown in green and removals are displayed in light red.
Extraneous whitespace is shown with a pure-red background.

Right-clicking in the diff provides access to additional actions
that use either the cursor location or text selection.

The "Copy Diff" action at ``Alt + Shift + C`` copies the selected lines to the
clipboard. The ``+``, ``-`` and `` `` diff line prefixes are stripped from each line
when copying diffs using the "Copy Diff" action.

Staging content for commit
--------------------------

The ``@@`` patterns denote a new diff hunk.  Selecting lines of diff
and using the `Stage Selected Lines` command will stage just the selected
lines.  Clicking within a diff hunk and selecting `Stage Diff Hunk` stages the
entire patch diff hunk.

The corresponding opposite commands can be performed on staged files as well,
e.g. staged content can be selectively removed from the index when we are
viewing diffs for staged content.

Diff Against Commit (Diff Mode)
-------------------------------

*Diff Mode* allows you to selectively unstage and revert edits from arbitrary commits
so that you can bring these edits back into your worktree.

You can use the diff editor to unstage edits against arbitrary commits by using the
``Diff > Against Commit... (Diff Mode)`` menu action.

You can exit *Diff Mode* by clicking on the red circle-slash icon on the Status
widget, by using the ``Diff > Exit Diff mode`` menu action, or by clicking in
an empty area in the `Status` tool.


COMMIT MESSAGE EDITOR
=====================

The commit message editor is a simple text widget
for entering commit messages.

You can navigate between the `Subject` and `Extended description...`
fields using the keyboard arrow keys.

Pressing enter when inside the `Subject` field jumps down to the
extended description field.

The `Options` button menu to the left of the subject field
provides access to the additional actions.

The `Ctrl+i` keyboard shortcut adds a standard "Signed-off-by: " line,
and `Ctrl+Enter` creates a new commit using the commit message and
staged content.

Sign Off
--------

The `Sign Off` button adds a sign-off to the bottom of the commit message::

    Signed-off-by: A. U. Thor <a.u.thor@example.com>

Invoking this action is equivalent to passing the ``-s`` option
to `git commit <https://git-scm.com/docs/git-commit>`_.

Signing-off on commits is a common practice in projects that use
`Developer Certificate of Origin <https://developercertificate.org/>`_
attestations in their contribution process.

Commit
------

The commit button runs
`git commit <https://git-scm.com/docs/git-commit>`_.
The contents of the commit message editor is provided as the commit message.

Only staged files are included in the commit -- this is the same behavior
as running ``git commit`` on the command-line.

Line and Column Display
-----------------------

The current line and column number is displayed by the editor.
E.g. a ``5,0`` display means that the cursor is located at
line five, column zero.

The display changes colors when lines get too long.
Yellow indicates the safe boundary for sending patches to a mailing list
while keeping space for inline reply markers.

Orange indicates that the line is starting to run a bit long and should
break soon.

Red indicates that the line is running up against the standard
80-column limit for commit messages.

Keeping commit messages less than 76-characters wide is encouraged.
`git log <https://git-scm.com/docs/git-log>`_
is a great tool but long lines mess up its formatting for everyone else,
so please be mindful when writing commit messages.

Amend Last Commit
-----------------

Clicking on `Amend Last Commit` makes `git cola` amend the previous commit
instead of creating a new one.  `git cola` loads the previous commit message
into the commit message editor when this option is selected.

The `Status` tool will display all of the changes for the amended commit.

Create Signed Commit
--------------------

Tell `git commit` and `git merge` to sign commits using GPG.

Using this option is equivalent to passing the ``--gpg-sign`` option to
`git commit <https://git-scm.com/docs/git-commit>`_ and
`git merge <https://git-scm.com/docs/git-merge>`_.

This option's default value can be configured using the `cola.signcommits`
configuration variable.

Prepare Commit Message
----------------------

The ``Commit > Prepare Commit Message`` action or `Ctrl-Shift-Return` keyboard shortcut
runs the `cola-prepare-commit-msg` hook if it is available in `.git/hooks/`.
This is a `git cola`-specific hook that takes the same parameters
as Git's `prepare-commit-msg hook <https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks>`_

The hook is passed the path to `.git/GIT_COLA_MSG` as the first argument and the hook is expected to write
an updated commit message to specified path.  After running this action, the
commit message editor is updated with the new commit message.

To override the default path to this hook set the
`cola.prepareCommitMessageHook` `git config` variable to the path to the
hook script.  This is useful if you would like to use a common hook
across all repositories.

Set Commit Date
---------------

The tool menu's "Set Commit Date" action displays a dialog that lets you set the
commit time for the next commit. Once enabled, the checkbox next to the menu action will
be checked.

The commit date option is disabled once a commit is performed.

Set Commit Author
-----------------

The tool menu's "Set Commit Author" action displays a dialog that lets you set the
commit author for the next commit. Once enabled, the checkbox next to the menu action
will be checked.

This setting persists across commits. Clear the tool menu's checkbox to disable the action.


BRANCHES
========

The `Branches` tool provides a visual tree to navigate branches.
The tree has three main sections: `Local Branches`, `Remote Branches` and `Tags`.
Branches are grouped by their name divided by the character ``/``.
For example, in a repo with the following list of branches::

    branch/doe
    branch/feature/foo
    branch/feature/bar

The branches widget will display the following hierarchy::

    branch
        - doe
        + feature
            - bar
            - foo

The current branch is decorated with a star icon.
If the current branch has commits ahead or behind the remote then an up or down
arrow will be displayed alongside a number showing the number of commits.

Actions
-------

Various actions are available through the right-click context menu.
Different actions are available depending on the selected branch's status.

Checkout
~~~~~~~~

The checkout action runs
`git checkout [<branchname>] <https://git-scm.com/docs/git-checkout>`_.

Merge into current branch
~~~~~~~~~~~~~~~~~~~~~~~~~

The merge action runs
`git merge --no-commit [<branchname>] <https://git-scm.com/docs/git-merge>`_.

Pull
~~~~

The pull action runs
`git pull --no-ff [<remote>] [<branchname>] <https://git-scm.com/docs/git-pull>`_.

Push
~~~~

The push action runs
`git push [<remote>] [<branchname>] <https://git-scm.com/docs/git-push>`_.

Rename Branch
~~~~~~~~~~~~~

The rename branch action runs
`git branch -M [<branchname>] <https://git-scm.com/docs/git-push>`_.

Delete Branch
~~~~~~~~~~~~~

The delete branch branch action runs
`git branch -D [<branchname>] <https://git-scm.com/docs/git-branch>`_.

Delete Remote Branch
~~~~~~~~~~~~~~~~~~~~

The remote branch action runs
`git push --delete [<remote>] [<branchname>] <https://git-scm.com/docs/git-push>`_.


APPLY PATCHES
=============

Use the ``File > Apply Patches`` menu item to begin applying patches.

Dragging and dropping patches onto the `git cola` interface
adds the patches to the list of patches to apply using
`git am <https://git-scm.com/docs/git-am>`_.

You can drag either a set of patches or a directory containing patches.
Patches can be sorted using in the interface and are applied in the
same order as is listed in the list.

When a directory is dropped `git cola` walks the directory
tree in search of patches.  `git cola` sorts the list of
patches after they have all been found.  This allows you
to control the order in which patches are applied by placing
patch sets into alphanumerically-sorted directories.


STASH
=====

Use the ``git cola stash`` sub-command or the ``Actions > Stash...`` menu action
to open the `Stash` tool.

Stashing is a quick way of removing changes from your worktree so that you
can restore the changes later. You can learn about the use cases for stashes in the
`git stash documentation <https://git-scm.com/docs/git-stash#_description>`_.

The list on the left displays all of your saved stashes.

Selecting a stash from the list allows you to `Rename`, `Apply`, `Pop`, or
`Drop` the content from the selected stash.

The `Save` button saves uncommitted content from your worktree to a new stash.

The content to stash is controlled by the `Keep Index` and `Save Index` options.
By default, all uncommitted changes, including staged content, will be saved to
the stash and removed from your working copy.

Options
-------

* `Keep Index`: Stash everything that has not been staged.
  Only content in the *Modified* state will be saved to the stash.
  Staged content will not be stashed.

* `Save Index`: Only stash the content that has been staged.
  Only content in the *Staged* state will be saved to the stash.
  Modified content will not be stashed.


WORKFLOW FAQ
============

* How do I stash some but not all modified files / lines?

  There are two ways of stashing a subset of changes.

  You can either *Stage* the content you want to keep un-stashed,
  or you can *Stage* the content that you want to stash away.

  * **Method 1: Stage the content that you want to keep.**

    This method is analogous to the ``git stash --keep-index`` option.

    1) Stage the content that you want to keep using the `Diff` and `Status` tools.

    2) Launch the `Stash` tool.

    3) Enable the `Keep Index` option and `Save` the stash.

    Modified changes will be stashed away.
    Staged changes will remain in your worktree.

  * **Method 2: Stage the content that you want to stash.**

    This workflow is unique to Git Cola. There is currently no equivalent
    Git builtin command for stashing the staging area.

    1) Stage the content that you want to stash using the `Diff` and `Status` tools.

    2) Launch the `Stash` tool.

    3) Enable the `Stash Index`` option and `Save` the stash.

    Staged changes will be stashed away.
    Modified changes will remain in your worktree.


CUSTOM WINDOW SETTINGS
======================

`git cola` remembers modifications to the layout and arrangement
of tools within the `git cola` interface.  Changes are saved
and restored at application shutdown/startup.

`git cola` can be configured to not save custom layouts by disabling
the `Save Window Settings` option in the `git cola` preferences.

You can save your current layout configuration to ``*.layout`` files
using the ``View > Layouts > Save Layout`` menu action.

You can load arbitrary layout files using the ``View > Layouts > Load Layout``
menu action.

By default, layouts are saved to the ``~/.config/git-cola/layouts`` directory.
Layouts saved to this directory will appear in the ``View > Layouts`` menu
for quick loading and switching of layouts.


DARK MODE AND WINDOW MANAGER THEMES
===================================

Git Cola contains a ``default`` theme which follows the current Qt style and a
handful of built-in color themes.  See :ref:`cola_theme` for more details.

To use icons appropriate for a dark application theme, configure
``git config --global cola.icontheme dark`` to use the dark icon theme.
See :ref:`cola_icontheme` for more details.

On macOS, using the ``default`` theme will automatically inherit "Dark Mode"
color themes when configured via System Preferences.  You will need to
configure the dark icon theme as noted above when dark mode is enabled.

On Linux, you may want Qt to follow the Window manager theme by configuring it
to do so using the ``qt5ct`` Qt5 configuration tool.  Install ``qt5ct`` on
Debian/Ubuntu systems to make this work.::

    sudo apt install qt5ct

Once installed, update your `~/.bash_profile` to activate ``qt5ct``::

    # Use the style configured using the qt5ct tool
    export QT_QPA_PLATFORMTHEME=qt5ct

This only work with the `default` theme.  The other themes replace the color
palette with theme-specific colors.

Some systems may require that you override `QT_STYLE_OVERRIDE` in order to
use a dark theme or to better interact with the Desktop environment.
Some systems provide a theme that you can install::

    sudo apt-get install adwaita-qt

You can activate the theme using the following environment variable::

    # Override the default theme to adwaita-dark
    export QT_STYLE_OVERRIDE=adwaita-dark

`QT_STYLE_OVERRIDE` may already be set in your Desktop Environment, so check that
variable for reference if you get unexpected hangs when launching `git-cola` or
when the default theme does not follow the desktop's theme on Linux.

If you don't want to set this variable globally then you can set it when launching
cola from the command-line::

    QT_STYLE_OVERRIDE=adwaita-dark git cola

The following is a user-contributed custom `git-cola.desktop` file that can be used to
launch Git Cola with these settings preset for you::

    [Desktop Entry]
    Name=Git Cola (dark)
    Comment=The highly caffeinated Git GUI
    TryExec=git-cola
    Exec=env QT_STYLE_OVERRIDE=adwaita-dark git-cola --prompt --icon-theme dark
    Icon=git-cola
    StartupNotify=true
    Terminal=false
    Type=Application
    Categories=Development;RevisionControl;
    X-KDE-SubstituteUID=false

You may also want to customize the diff colors when using a dark theme::

    git config --global cola.color.add 86c19f
    git config --global cola.color.remove c07067

Please see `#760 <https://github.com/git-cola/git-cola/issues/760>`_ for more details.

Custom Themes
-------------

To create your own custom theme for Git Cola just create a QSS file and put it in
``~/.config/themes/``. You can add as many files as you want. Each file will become
an option in ``Menu > File > Preferences > Appearance > GUI theme``.

Some examples can be found here `Qt Style Sheets Examples <https://doc.qt.io/qt-5/stylesheet-examples.html>`_.


CONFIGURATION VARIABLES
=======================

These variables can be set using `git config` or from the settings.

cola.aspell.enabled
-------------------

Set to `true` to enable support for ``aspell`` spellcheck dictionaries.
When `false`, spellcheck dictionaries are read from ``/usr/share/dict/words``
by default. When `true` Git Cola will run ``aspell dump master --lang=$lang``
for each of the installed languages to gather words.
Defaults to `false`.

cola.aspell.lang
----------------

Configure the language names that are queried using ``aspell``. For example,
``git config --global --add cola.aspell.lang en_US`` will make it so that
only the ``en_US`` language is used.

This is a multi-valued configuration value.
``git config --global --add cola.aspell.lang $lang`` can be run once for each language
to specify multiple languages to use.

When unset, all of the two-letter language names from the output of
``aspell dicts`` will be used.

cola.autodetectproxy
--------------------

Set to `false` to disable auto-configuration of HTTP proxy settings based on
the configured Gnome and KDE Desktop Environment proxy settings.
The core Git `http.proxy` configuration overrides this value.
Defaults to `true`.

cola.autocompletepaths
----------------------

Set to `false` to disable auto-completion of filenames in completion widgets.
This can speed up operations when working in large repositories.
Defaults to `true`.

cola.autoloadCommitTemplate
---------------------------

Set to `true` to automatically load the commit template in the commit message
editor If the commit.template variable has not been configured, raise the
corresponding error.
Defaults to `false`.

cola.blameviewer
----------------

The command used to blame files.  Defaults to `git gui blame`.

cola.blockcursor
----------------

Whether to use a "block" cursor in diff editors. The block cursor is easier to
see compared to a line cursor. Set to `false` to use a thin "line" cursor.
Defaults to `true`.

cola.boldfonts
--------------

Use bold fonts throughout the entire interface to increase usability on small screens.
Defaults to `false`.

cola.boldheaders
----------------

Whether to use bold headers on a dark background instead of italics in the Status tool.
Defaults to `false`.

cola.browserdockable
--------------------

Whether to create a dock widget with the `Browser` tool.
Defaults to `false` to speedup startup time.

cola.checkconflicts
-------------------

Inspect unmerged files for conflict markers before staging them.
This feature helps prevent accidental staging of unresolved merge conflicts.
Defaults to `true`.

cola.defaultrepo
----------------

`git cola`, when run outside of a Git repository, prompts the user for a
repository.  Set `cola.defaultrepo` to the path of a Git repository to make
`git cola` attempt to use that repository before falling back to prompting
the user for a repository.

cola.dictionary
---------------

Specifies additional dictionaries for `git cola` to use in its spell checker.
This should be configured to the path of a newline-separated list of words.
``*.dic`` dictionary files used by ``hunspell`` are also supported.

By default, `git cola` searches for `dict/words` and `dict/propernames` dictionary
files in `~/.local/share` and `$XDG_DATA_DIRS`.

If `$XDG_DATA_DIRS` is undefined or set to an empty value then `/usr/local/share` and
`/usr/share` are searched for dictionary files.

Dictionary files are newline-separated and contain one word per line.
Dictionary files must be UTF-8 encoded.

If you have multiple dictionaries that you would like `git cola` to use then
you can specify multiple dictionaries using ``git config --global --add``.
``cola.dictionary`` is a configuration value that can contain multiple values.

.. sourcecode:: sh

   git config --global --add cola.dictionary /path/to/dictionary1
   git config --global --add cola.dictionary /path/to/dictionary2

Users on Debian-based systems can install additional ``hunspell`` dictionary
files to make them available in ``/usr/share/hunspell/*.dic``. For example,
to install the Spanish dictionary, run:

.. sourcecode:: sh

   sudo apt install hunspell-es

cola.enablepopups
-----------------

Actions such as "Fetch", "Push", "Pull", "Sync" and "Sync Out" display desktop
notifications on Linux when either the `notify2` or `notifypy` modules are installed.
The message are logged to the Console otherwise.

Messages are displayed using popup dialogs when ``cola.enablepopups`` is set to ``true``.
Defaults to `false`.

cola.expandtab
--------------

Expand tabs into spaces in the commit message editor.  When set to `true`,
`git cola` will insert a configurable number of spaces when tab is pressed.
The number of spaces is determined by `cola.tabwidth`.
Defaults to `false`.

cola.gravatar
-------------

Use the `gravatar.com` service to lookup icons for author emails.
Gravatar icons work by sending an MD5 hash of an author's email to `gravatar.com`
when requesting an icon. Warning: this feature can leak information.
Network requests to `gravatar.com` are disabled when set to `false`.
Defaults to `true`.

cola.fileattributes
-------------------

Enables per-file gitattributes encoding and binary file support.
This tells `git cola` to honor the configured encoding when displaying
and applying diffs.

A `.gitattributes` file can set the ``binary`` attribute in order to force
specific untracked paths to be treated as binary files when diffing.
Binary files are displayed using a hex-dump display.

.. sourcecode:: sh

   # Treat *.exr files as binary files.
   *.exr binary

cola.fontdiff
-------------

Specifies the font to use for `git cola`'s diff display.

cola.fontsize
-------------

Specifies the font size that is used for the Status, Submodules, Branches, Recent, and
Favorites widgets.

cola.hidpi
----------

Specifies the High DPI displays scale factor. Set `0` to automatically scaled.
Setting value between 0 and 1 is undefined.
This option requires at least Qt 5.6 to work.
See `Qt QT_SCALE_FACTOR documentation <https://doc.qt.io/qt-5/highdpi.html>`_
for more information.

.. _cola_icontheme:

cola.icontheme
--------------

Specifies the icon themes to use throughout `git cola`. The theme specified
must be the name of the subdirectory containing the icons, which in turn must
be placed in the inside the main "icons" directory in `git cola`'s
installation prefix.

If unset, or set either "light" or "default", then the default style will be
used.  If set to "dark" then the built-in "dark" icon theme, which is
suitable for a dark window manager theme, will be used.

If set to an absolute directory path then icons in that directory will be used.
This value can be set to multiple values using,
``git config --add cola.icontheme $theme``.

This setting can be overridden by the `GIT_COLA_ICON_THEME` environment
variable, which can specify multiple themes using a colon-separated value.

The icon theme can also be specified by passing ``--icon-theme=<theme>`` on the
command line, once for each icon theme, in the order that they should be
searched.  This can be used to override a subset of the icons, and fallback
to the built-in icons for the remainder.

cola.imagediff.[extension]
--------------------------

Enable image diffs for the specified file extension.  For example, configuring
`git config --global cola.imagediff.svg false` will disable use of the visual
image diff for `.svg` files in all repos until is is explicitly toggled on.
Defaults to `true`.

cola.inotify
------------

Set to `false` to disable file system change monitoring.  Defaults to `true`,
but also requires either Linux with inotify support or Windows with `pywin32`
installed for file system change monitoring to actually function.

cola.inotifydelay
-----------------

How long to wait, in milliseconds, between file system change notifications.
Defaults to `888`.

cola.refreshonfocus
-------------------

Set to `true` to automatically refresh when `git cola` gains focus.  Defaults
to `false` because this can cause a pause whenever switching to `git cola` from
another application.

cola.linebreak
--------------

Whether to automatically break long lines while editing commit messages.
Defaults to `true`.  This setting is configured using the `Preferences`
dialog, but it can be toggled for one-off usage using the commit message
editor's options sub-menu.

cola.logdate
------------

Set the default date-time mode for the DAG display. This value is
passed to `git log --date=<format>`.
See `git log(1) <https://git-scm.com/docs/git-log#Documentation/git-log.txt---dateltformatgt>`_
for more details.

cola.maxrecent
--------------

`git cola` caps the number of recent repositories to avoid cluttering
the start and recent repositories menu.  The maximum number of repositories to
remember is controlled by `cola.maxrecent` and defaults to `8`.

cola.mousezoom
--------------

Controls whether zooming text using Ctrl + MouseWheel scroll is enabled.
Set to ``false`` to disable scrolling with the mouse wheel.
Defaults to ``true``.

cola.notifyonpush
-----------------

Enable desktop notifications when commits are pushed using the "Push" dialog.
Set to ``true`` to enable desktop notifications.
Defaults to ``false``.

cola.dragencoding
-----------------

`git cola` encodes paths dragged from its widgets into `utf-16` when adding
them to the drag-and-drop mime data (specifically, the `text/x-moz-url` entry).
`utf-16` is used to make `gnome-terminal` see the right paths, but other
terminals may expect a different encoding.  If you are using a terminal that
expects a modern encoding, e.g. `terminator`, then set this value to `utf-8`.

cola.readsize
-------------

`git cola` avoids reading large binary untracked files.
The maximum size to read is controlled by `cola.readsize`
and defaults to `2048`.

cola.resizebrowsercolumns
-------------------------

`git cola` will automatically resize the file browser columns as folders are
expanded/collapsed when ``cola.resizebrowsercolumns`` is set to `true`.

cola.patchesdirectory
---------------------

The default directory to use when exporting patches. Relative paths are treated
as being relative to the current repository. Absolute paths are used as-is.
Defaults to `patches`.

cola.safemode
-------------

The "Stage" button in the `git cola` Actions panel stages all files when it is
activated and no files are selected.  This can be problematic if it is
accidentally triggered after carefully preparing the index with staged
changes.  "Safe Mode" is enabled by setting `cola.safemode` to `true`.
When enabled, `git cola` will do nothing when "Stage" is activated without a
selection.  Defaults to `false`.

cola.savewindowsettings
-----------------------

`git cola` will remember its window settings when set to `true`.
Window settings and X11 sessions are saved in `$HOME/.config/git-cola`.

cola.showpath
-------------

`git cola` displays the absolute path of the repository in the window title.
This can be disabled by setting `cola.showpath` to `false`.
Defaults to `true`.

cola.signcommits
----------------

`git cola` will sign commits by default when set `true`. Defaults to `false`.
See the section below on setting up GPG for more details.

cola.startupmode
----------------

Control how the list of repositories is displayed in the startup dialog.
Set to `list` to view the list of repositories as a list, or `folder` to view
the list of repositories as a collection of folder icons.
Defaults to `list`.

cola.statusindent
-----------------

Set to `true` to indent files in the Status widget.  Files in the `Staged`,
`Modified`, etc. categories will be grouped in a tree-like structure.
Defaults to `false`.

cola.statusshowtotals
---------------------

Set to `true` to display files counts in the Status widget's category titles.
Defaults to `false`.

cola.sync
---------

Set to `false` to disable calling `os.fdatasync()`  / `os.fdata()` when saving
settings. Defaults to `true`, which means that these functions are called when windows
are closed and their settings are saved.

cola.tabwidth
-------------

The number of columns occupied by a tab character.  Defaults to 8.

cola.terminal
-------------

The command to use when launching commands within a graphical terminal.

`cola.terminal` defaults to `xterm -e` when unset.
e.g. when opening a shell, `git cola` will run `xterm -e $SHELL`.

`git cola` has built-in support for `xterm`, `gnome-terminal`, `konsole`.
If either `gnome-terminal`, `xfce4-terminal`, or `konsole` are installed
then they will be preferred over `xterm` when `cola.terminal` is unset.

The table below shows the built-in values that are used for the respective
terminal.  You can force the use of a specific terminal by configuring cola
accordingly.

cola.terminalshellquote
-----------------------

Some terminal require that the command string get passed as a string.
For example, ``xfce4-terminal -e "git difftool"`` requires shell quoting,
whereas ``gnome-terminal -- git difftool`` does not.

You should not need to set this variable for the built-in terminals
cola knows about -- it will behave correctly without configuration.
For example, when not configured, cola already knows that xfce4-terminal
requires shell quoting.

This configuration variable is for custom terminals outside of the builtin set.
The table below shows the builtin configuration.

.. code-block:: text

    Terminal            cola.terminal           cola.terminalshellquote
    --------            -------------           -----------------------
    gnome-terminal      "gnome-terminal --"     false
    konsole             "konsole -e"            false
    xfce4-terminal      "xfce4-terminal -e"     true
    xterm               "xterm -e"              false


cola.textwidth
--------------

The number of columns used for line wrapping.
Tabs are counted according to `cola.tabwidth`.

.. _cola_theme:

cola.theme
----------

Specifies the GUI theme to use throughout `git cola`. The theme specified
must be one of the following values:

* `default` – default Qt theme, may appear different on various systems
* `flat-dark-blue`
* `flat-dark-green`
* `flat-dark-grey`
* `flat-dark-red`
* `flat-light-blue`
* `flat-light-green`
* `flat-light-grey`
* `flat-light-red`

If unset, or set to an invalid value, then the default style will be
used. The `default` theme is generated by Qt internal engine and should look
native but may look noticeably different on different platforms. The flat
themes on the other hand should look similar (but not identical) on various
systems.

The GUI theme can also be specified by passing ``--theme=<name>`` on the
command line.

cola.turbo
----------

Set to `true` to enable "turbo" mode.  "Turbo" mode disables some
features that can slow things down when operating on huge repositories.
"Turbo" mode will skip loading Git commit messages, author details, status
information, and commit date details in the `File Browser` tool.
Defaults to `false`.

cola.color.text
---------------

The default diff text color, in hexadecimal #RRGGBB notation.
Defaults to "#030303"::

    git config cola.color.text '#030303'

cola.color.add
--------------

The default diff "add" background color, in hexadecimal #RRGGBB notation.
Defaults to "#d2ffe4"::

    git config cola.color.add '#d2ffe4'

cola.color.remove
-----------------

The default diff "remove" background color, in hexadecimal #RRGGBB notation.
Defaults to "#fee0e4"::

    git config cola.color.remove '#fee0e4'

cola.color.header
-----------------

The default diff header text color, in hexadecimal #RRGGBB notation.
Defaults to "#bbbbbb"::

    git config cola.color.header '#bbbbbb'

cola.updateindex
----------------

Git's index is refreshed during application startup. You can disable this behavior by
configuring ``cola.updateindex`` to ``false``. This is useful in some scenarios such as
when accessing Git repositories over a Samba share. If you have this enabled then you
can use the ``ctrl-r`` "Refresh" action to force the index to be refreshed instead.
Defaults to ``true``.

cola.verbosity
--------------

Increase the verbosity of the Console tool by logging ``git`` commands with a ``[git]``
prefix when set to a value of ``1`` or higher. This setting allows users to more easily
discover which ``git`` commands are being run under the hood.
Defaults to ``0``.

commit.cleanup
--------------

Configure whether commit messages should be stripped of whitespace and comments.

Valid values are ``strip``, ``whitespace``, ``verbatim``, ``scissors`` or ``default``.

The ``default`` mode uses the ``whitespace`` mode when committing through Git Cola
and the ``strip`` mode when committing using the ``git commit`` command-line.

* ``strip`` - Strip leading and trailing empty lines, trailing whitespace,
  commentary and collapse consecutive empty lines.

* ``whitespace`` - Same as strip except ``# commentary`` is not removed.
  This is the ``default`` behavior when committing through `Git Cola`.

* ``verbatim`` - Do not change the message at all.

* ``scissors`` - Same as whitespace except that everything from (and including)
  the line found below is truncated, if the message is to be edited.
  "#" can be customized with ``core.commentChar``::

    # ------------------------ >8 ------------------------
    Scissor-lines and all following lines are removed.

Changing the mode to ``whitespace`` can be useful when you always want to keep
lines that begin with comment character ``#`` in your log message, even when
committing using the command-line ``git commit``.

On the contrary, if you always want to always strip comments, even when
committing through Git Cola, then configure ``commit.cleanup`` to ``strip``.

Please see the `git commit cleanup mode documentation
<https://git-scm.com/docs/git-commit#Documentation/git-commit.txt---cleanupltmodegt>`_
for more details.

core.commentChar
----------------

Commit messages can contain comments that start with this character.
Defaults to ``#``.

Please see the `git config documentation
<https://git-scm.com/docs/git-config#Documentation/git-config.txt-corecommentChar>`_
for more details.

core.hooksPath
--------------

Hooks are programs you can place in a hooks directory to trigger actions at
certain points in git’s execution. Hooks that don’t have the executable bit
set are ignored.

By default the hooks directory is ``$GIT_DIR/hooks``, but that can
be changed via the ``core.hooksPath`` configuration variable

The ``cola-prepare-commit-msg`` hook functionality and Cola's Git LFS
detection honors this configuration.

Please see the `git hooks documentation <https://git-scm.com/docs/githooks>`_
for more details.

gui.diffcontext
---------------

The number of diff context lines to display.

gui.displayuntracked
--------------------

`git cola` avoids showing untracked files when set to `false`.

gui.editor
----------

The default text editor to use is defined in `gui.editor`.
The config variable overrides the VISUAL environment variable.
Defaults to `gvim -f -p`.

gui.historybrowser
------------------

The history browser to use when visualizing history.
Defaults to `gitk`.

diff.tool
---------

The default diff tool to use.

merge.tool
----------

The default merge tool to use.

user.email
----------

Your email address to be recorded in any newly created commits.
Can be overridden by the 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_EMAIL', and
'EMAIL' environment variables.

user.name
---------

Your full name to be recorded in any newly created commits.
Can be overridden by the 'GIT_AUTHOR_NAME' and 'GIT_COMMITTER_NAME'
environment variables.


ENVIRONMENT VARIABLES
=====================

GIT_ASKPASS
-----------

Specify the OpenSSH `askpass` program to use when prompting for credentials.
This environment variable has the highest priority when specifying an `askpass` program.

The ``SSH_ASKPASS`` environment variable is considered alongside ``GIT_ASKPASS``
nd  has the 2nd-highest priority.

See `Git's askpass documentation <https://git-scm.com/docs/gitcredentials.html#_requesting_credentials>`_
for more details.

Debian users can either ``sudo apt install ssh-askpass-gnome`` or
``sudo apt install ksshaskpass`` to install a suitable askpass credential helper.
When installed, these programs will be used by default when the environment variables
have not been set.

If no `askpass` program can be found then cola's builtin `ssh-askpass`
program will by used, but using an external program is highly encouraged.

GIT_COLA_ICON_THEME
-------------------

When set in the environment, `GIT_COLA_ICON_THEME` overrides the
theme specified in the `cola.icontheme` configuration.
Read :ref:`cola_icontheme` for more details.

GIT_COLA_SCALE
--------------

.. Important:: `GIT_COLA_SCALE` should not be used with newer versions of Qt.

    Set `QT_AUTO_SCREEN_SCALE_FACTOR` to `1` and Qt will automatically
    scale the interface to the correct size based on the display DPI.
    This option is also available by setting `cola.hidpi` configuration.

    See the `Qt High DPI documentation <https://doc.qt.io/qt-5/highdpi.html>`_
    for more details.

`git cola` can be made to scale its interface for HiDPI displays.
When defined, `git cola` will scale icons, radio buttons, and checkboxes
according to the scale factor.  The default value is `1`.
A good value is `2` for high-resolution displays.

Fonts are not scaled, as their size can already be set in the settings.

GIT_COLA_TRACE
--------------

When defined, `git cola` logs `git` commands to stdout.
When set to `full`, `git cola` also logs the exit status and output.
When set to `trace`, `git cola` logs to the `Console` widget.

VISUAL
------

Specifies the default editor to use.
This is ignored when the `gui.editor` configuration variable is defined.

LANGUAGE SETTINGS
=================

`git cola` automatically detects your language and presents some
translations when available.  This may not be desired, or you
may want `git cola` to use a specific language.

You can make `git cola` use an alternative language by creating a
`~/.config/git-cola/language` file containing the standard two-letter
gettext language code, e.g. "en", "de", "ja", "zh", etc.::

    mkdir -p ~/.config/git-cola &&
    echo en >~/.config/git-cola/language

Alternatively you may also use LANGUAGE environmental variable to temporarily
change `git cola`'s language just like any other gettext-based program.  For
example to temporarily change `git cola`'s language to English::

    LANGUAGE=en git cola

To make `git cola` use the zh_TW translation with zh_HK, zh, and en as a
fallback.::

    LANGUAGE=zh_TW:zh_HK:zh:en git cola


CUSTOM GUI ACTIONS
==================

`git cola` allows you to define custom GUI actions by setting `git config`
variables.  The "name" of the command appears in the "Actions" menu.

guitool.<name>.cmd
------------------

Specifies the shell command line to execute when the corresponding item of the
Tools menu is invoked. This option is mandatory for every tool. The command is
executed from the root of the working directory, and in the environment it
receives the name of the tool as GIT_GUITOOL, the name of the currently
selected file as FILENAME, and the name of the current branch as CUR_BRANCH
(if the head is detached, CUR_BRANCH is empty).

If ``<name>`` contains slashes (``/``) then the leading part of the name,
up until the final slash, is treated like a path of sub-menus under which the
actions will be created.

For example, configuring ``guitool.Commands/Util/echo.cmd`` creates a
``Commands`` menu inside the top-level ``Actions`` menu, a ``Util`` menu
inside the ``Commands`` menu and an ``echo`` action inside the ``Commands``
sub-menu.

guitool.<name>.background
-------------------------

Run the command in the background (similar to editing and difftool actions).
This avoids blocking the GUI.  Setting `background` to `true` implies
`noconsole` and `norescan`.

guitool.<name>.needsfile
------------------------

Run the tool only if a diff is selected in the GUI. It guarantees that
FILENAME is not empty.

guitool.<name>.noconsole
------------------------

Run the command silently, without creating a window to display its output.

guitool.<name>.norescan
-----------------------

Don’t rescan the working directory for changes after the tool finishes
execution.

guitool.<name>.confirm
----------------------

Show a confirmation dialog before actually running the tool.

guitool.<name>.argprompt
------------------------

Request a string argument from the user, and pass it to the tool through the
ARGS environment variable. Since requesting an argument implies confirmation,
the confirm option has no effect if this is enabled. If the option is set to
true, yes, or 1, the dialog uses a built-in generic prompt; otherwise the
exact value of the variable is used.

guitool.<name>.revprompt
------------------------

Request a single valid revision from the user, and set the REVISION
environment variable. In other aspects this option is similar to argprompt,
and can be used together with it.

guitool.<name>.revunmerged
--------------------------

Show only unmerged branches in the revprompt sub-dialog. This is useful for
tools similar to merge or rebase, but not for things like checkout or reset.

guitool.<name>.title
--------------------

Specifies the title to use for the prompt dialog.
Defaults to the tool name.

guitool.<name>.prompt
---------------------

Specifies the general prompt string to display at the top of the dialog,
before subsections for argprompt and revprompt.
The default value includes the actual command.

guitool.<name>.shortcut
-----------------------

Specifies a keyboard shortcut for the custom tool.

The value must be a valid string understood by the `QAction::setShortcut()` API.
See https://doc.qt.io/qt-6/qkeysequence.html#toString
for more details about the supported values.

Avoid creating shortcuts that conflict with existing built-in `git cola`
shortcuts.  Creating a conflict will result in no action when the shortcut
is used.


SETTING UP CREDENTIAL HELPERS
=============================

Git has robust support for automatically handling credentials.

The recommended approach is to use SSH keys and an SSH agent, but any of the core Git
Credentials helpers will get used automatically by Git Cola.

See https://git-scm.com/doc/credential-helpers for more details.


SETTING UP GPG FOR SIGNED COMMITS
=================================

When creating signed commits, `gpg` will attempt to read your password from the
terminal from which `git cola` was launched.
The way to make this work smoothly is to use a GPG agent so that you can avoid
needing to re-enter your password every time you commit.

This also gets you a graphical passphrase prompt instead of getting prompted
for your password in the terminal.

Install gpg-agent and friends
-----------------------------

On Mac OS X, you may need to `brew install gpg-agent` and install the
`Mac GPG Suite <https://gpgtools.org/macgpg2/>`_.

On Linux use your package manager to install gnupg2,
gnupg-agent and pinentry-qt, e.g.::

    sudo apt-get install gnupg2 gnupg-agent pinentry-qt

On Linux, you should also configure Git so that it uses gpg2 (gnupg2),
otherwise you will get errors mentioning, "unable to open /dev/tty".
Set Git's `gpg.program` to `gpg2`::

    git config --global gpg.program gpg2

Configure gpg-agent and a pin-entry program
-------------------------------------------

On Mac OS X, edit `~/.gnupg/gpg.conf` to include the line,::

    use-agent

This is typically not needed on Linux, where `gpg2` is used, as
this is the default value when using `gpg2`.

Next, edit `~/.gnupg/gpg-agent.conf` to contain a pinentry-program line
pointing to the pinentry program for your platform.

The following example `~/.gnupg/gpg-agent.conf` shows how to use
pinentry-gtk-2 on Linux::

    pinentry-program /usr/bin/pinentry-gtk-2
    default-cache-ttl 3600

This following example `.gnupg/gpg-agent.conf` shows how to use MacGPG2's
pinentry app on On Mac OS X::

    pinentry-program /usr/local/MacGPG2/libexec/pinentry-mac.app/Contents/MacOS/pinentry-mac
    default-cache-ttl 3600
    enable-ssh-support
    use-standard-socket

Once this has been set up then you will need to reload your gpg-agent config::

    echo RELOADAGENT | gpg-connect-agent

If you see the following output::

    OK

Then the daemon is already running, and you do not need to start it yourself.

If it is not running, eval the output of ``gpg-agent --daemon`` in your shell
prior to launching `git cola`.::

    eval $(gpg-agent --daemon)
    git cola


SHELL COMPLETIONS
=================

Git Cola provides shell completions for zsh and bash.
The completion scripts and instructions are included in Git Cola's
`contrib` directory.

* `Shell completion scripts <https://gitlab.com/git-cola/git-cola/-/tree/main/contrib>`_

* `Setup instructions <https://gitlab.com/git-cola/git-cola/-/blob/main/contrib/README.md>`_


MACOS NOTES
===========

A ``git-cola.app`` bundle can be built using ``garden macos/app``.
See the ``garden.yaml`` file for more details.

Older versions of the ``git-cola.app`` may have caused macOS to launch Git Cola using
Rosetta even though Python is arm64 native. This is a macOS / Apple bug.

A stub ``git-cola-macos`` binary is now provided in ``git-cola.app/Contents/MacOS``
as a workaround to prevent this behavior.

If you launched an older version of the ``git-cola.app`` bundle you may have encountered
this macOS bug:

https://apple.stackexchange.com/questions/457171/shell-script-application-bundle-prompts-for-rosetta-installation

Per the discussion above, you can clear the buggy cache using this command::

    /usr/libexec/PlistBuddy -c 'Delete :"Architectures for arm64":com.justroots.git-cola' \
    ~/Library/Preferences/com.apple.LaunchServices/com.apple.LaunchServices.plist

Reboot after running this command and Git Cola should launch natively without Rosetta.


WINDOWS NOTES
=============

Git Installation
----------------

If Git is installed in a custom location, e.g. not installed in `C:/Git` or
Program Files, then the path to Git must be configured by creating a file in
your home directory `~/.config/git-cola/git-bindir` that points to your git
installation, e.g.::

    C:/Tools/Git/bin

SSH Agents for Key-based Authentication
---------------------------------------

You may need to setup ssh-agent in order to use SSH key-based authentication
on Windows. It has been reported that starting OpenSSH agent in
Windows Services and adding the key using Powershell are necessary in order
to get things working.

Please see the following links for more details.

https://stackoverflow.com/questions/18683092/how-to-run-ssh-add-on-windows

Samba
-----

Core Git has issues when operating over a Samba file share. This can lead
to ``.git/index.lock`` lingering around and preventing ``git`` commands from
working correctly.

To avoid these issues, operate on repositories from a local filesystem.


FIPS SECURITY MODE
==================

`FIPS Security Mode <https://github.com/python/cpython/issues/53462>`_
is available in newer versions of Python. These include Python 3.9+ and the
patched Python 3.6 used by CentOS8/RHEL8 (and possibly others).

Git Cola uses the ``hashlib.md5`` function and adheres to the FIPS security
mode when available. Git Cola does not use the MD5 value for security purposes.
MD5 is used only for the purposes of implementing the ``cola/gravatar.py``
Gravatar client.


LINKS
=====

Git Cola's Git Repository
-------------------------
* `Primary repository <https://gitlab.com/git-cola/git-cola/>_`.
* `Mirror repository <https://github.com/git-cola/git-cola/>_`.


Git Cola Homepage
-----------------

https://git-cola.gitlab.io/
