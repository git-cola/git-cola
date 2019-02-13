===========
git-cola(1)
===========

SYNOPSIS
========
git cola [options] [sub-command]

DESCRIPTION
===========
git cola is a sleek and powerful Git GUI.

OPTIONS
=======

--amend
-------
Start `git cola` in amend mode.

--prompt
--------
Prompt for a Git repository.  Defaults to the current directory.

-r, --repo <path>
-----------------
Open the Git repository at `<path>`.  Defaults to the current directory.

-s, --status-filter <filter>
----------------------------
Apply the path filter to the status widget.

--version
---------
Print the `git cola` version and exit.

-h, --help
----------
Show usage and optional arguments.

--help-commands
---------------
Show available sub-commands.

SUB-COMMANDS
============

am
--
Apply patches.

archive
-------
Export tarballs from Git.

branch
------
Create branches.

browse
------
Browse tracked files.

config
------
Configure settings.

dag
---
Start the `git dag` Git history browser.

diff
----
Diff changed files.

fetch
-----
Fetch history from remote repositories.

grep
----
Use `git grep` to search for content.

merge
-----
Merge branches.

pull
----
Fetch and merge remote branches.

push
----
Push branches to remotes.

rebase
------
Start an interactive rebase.

remote
------
Create and edit remotes.

search
------
Search for commits.

stash
-----
Stash uncommitted modifications.

tag
---
Create tags.

version
-------
Print the `git cola` version.

CONFIGURE YOUR EDITOR
=====================
The editor used by `Ctrl-e` is configured from the Preferences screen.
The environment variable `$VISUAL` is consulted when no editor has been
configured.

*ProTip*: Configuring your editor to `gvim -f -p` will open multiple tabs
when editing files.  `gvim -f -o` uses splits.

`git cola` is {vim, emacs, textpad, notepad++}-aware.
When you select a line in the `grep` screen and press any of
`Enter`, `Ctrl-e`, or the `Edit` button, you are taken to that exact line.

The editor preference is saved in the `gui.editor` variable using
`git config <http://git-scm.com/docs/git-config>`_.

KEYBOARD SHORTCUTS
==================
`git cola` has many useful keyboard shortcuts.

You can see the available shortcuts by pressing the ``?`` key,
choosing ``Help -> Keyboard shortcuts`` from the main menu,
or by consulting the `git cola keyboard shortcuts reference <https://git-cola.github.io/share/doc/git-cola/hotkeys.html>`_.

TOOLS
=====
The `git cola` interface is composed of various cooperating tools.
Double-clicking a tool opens it in its own subwindow.
Dragging it around moves and places it within the window.

Tools can be hidden and rearranged however you like.
`git cola` carefully remembers your window layout and restores
it the next time it is launched.

The `Control-{1, 2, 3, ...}` hotkey gives focus to a specific tool.
A hidden tool can be re-opened using the `Tools` menu or
the `Shift+Control-{1, 2, 3, ...}` shortcut keys.

The Diff editor can be focused with `Ctrl-j`.
the Status tool can be focused with `Ctrl-k`.
the Commit tool can be focused with `Ctrl-l`.

.. _status:

STATUS
======
The `Status` tool provides a visual analog to the
`git status <http://git-scm.com/docs/git-status>`_ command.

`Status` displays files that are `modified` relative to the staging area,
`staged` for the next commit, `unmerged` files from an in-progress merge,
and files that are `untracked` to git.

These are the same categories one sees when running
`git status <http://git-scm.com/docs/git-status>`_
on the command line.

You can navigate through the list of files using keyboard arrows as well
as the ergonomical and vim-like `j` and `k` shortcut keys.

There are several convenient ways to interact with files in the `Status` tool.

Selecting a file displays its diff in the :ref:`Diff` viewer.
Double-clicking a file stages its contents, as does the
the `Ctrl-s` shortcut key.

`Ctrl-e` opens selected files in the conifgured editor, and
`Ctrl-d` opens selected files using `git difftool <http://git-scm.com/docs/git-difftool>`_

Additional actions can be performed using the right-click context menu.

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
Add to the staging area using `git add <http://git-scm.com/docs/git-add>`_
Marks unmerged files as resolved.

Launch Editor
~~~~~~~~~~~~~
Launches the configured visual text editor

Launch Difftool
~~~~~~~~~~~~~~~
Visualize changes using `git difftool`.

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
`git reset <http://git-scm.com/docs/git-reset>`_

Launch Merge Tool
~~~~~~~~~~~~~~~~~
Resolve conflicts using `git mergetool <http://git-scm.com/docs/git-mergetool>`_.

Delete File(s)
~~~~~~~~~~~~~~
Delete untracked files from the filesystem.

Add to .gitignore
~~~~~~~~~~~~~~~~~
Adds untracked files to to the .gitignore file.

.. _diff:

DIFF
====
The diff viewer/editor displays diffs for selected files.
Additions are shown in green and removals are displayed in light red.
Extraneous whitespace is shown with a pure-red background.

Right-clicking in the diff provides access to additional actions
that use either the cursor location or text selection.

Staging content for commit
--------------------------
The ``@@`` patterns denote a new diff hunk.  Selecting lines of diff
and using the `Stage Selected Lines` command will stage just the selected
lines.  Clicking within a diff hunk and selecting `Stage Diff Hunk` stages the
entire patch diff hunk.

The corresponding opposite commands can be performed on staged files as well,
e.g. staged content can be selectively removed from the index when we are
viewing diffs for staged content.

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
The `Sign Off` button adds a standard::

    Signed-off-by: A. U. Thor <a.u.thor@example.com>

line to the bottom of the commit message.

Invoking this action is equivalent to passing the ``-s`` option
to `git commit <http://git-scm.com/docs/git-commit>`_.

Commit
------
The commit button runs
`git commit <http://git-scm.com/docs/git-commit>`_.
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
`git log <http://git-scm.com/docs/git-log>`_
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
`git commit <http://git-scm.com/docs/git-commit>`_ and
`git merge <http://git-scm.com/docs/git-merge>`_.

This option's default value can be configured using the `cola.signcommits`
configuration variable.

Prepare Commit Message
----------------------
The ``Commit -> Prepare Commit Message`` action or `Ctrl-Shift-Return` keyboard shortcut
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

BRANCHES
========

The `Branches` tool provides a visual tree to navigate through the branches.
The tree has three main nodes `Local Branch`, `Remote Branch` and `Tags`.
Branches are grouped by their name divided by the character '/'.Ex::

    branch/feature/foo
    branch/feature/bar
    branch/doe

Will produce::

    branch
        - doe
        + feature
            - bar
            - foo

Current branch will display a star icon. If current branch has commits
ahead/behind it will display an up/down arrow with its number.

Actions
-------
Various actions are available through the right-click context menu.
Different actions are available depending of selected branch status.

Checkout
~~~~~~~~
The checkout action runs
`git checkout [<branchname>] <https://git-scm.com/docs/git-checkout>`_.

Merge in current branch
~~~~~~~~~~~~~~~~~~~~~~~
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
Use the ``File -> Apply Patches`` menu item to begin applying patches.

Dragging and dropping patches onto the `git cola` interface
adds the patches to the list of patches to apply using
`git am <http://git-scm.com/docs/git-am>`_.

You can drag either a set of patches or a directory containing patches.
Patches can be sorted using in the interface and are applied in the
same order as is listed in the list.

When a directory is dropped `git cola` walks the directory
tree in search of patches.  `git cola` sorts the list of
patches after they have all been found.  This allows you
to control the order in which patchs are applied by placing
patchsets into alphanumerically-sorted directories.

CUSTOM WINDOW SETTINGS
======================
`git cola` remembers modifications to the layout and arrangement
of tools within the `git cola` interface.  Changes are saved
and restored at application shutdown/startup.

`git cola` can be configured to not save custom layouts by unsetting
the `Save Window Settings` option in the `git cola` preferences.

CONFIGURATION VARIABLES
=======================
These variables can be set using `git config` or from the settings.

cola.blameviewer
----------------
The command used to blame files.  Defaults to `git gui blame`.

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
Specifies an additional dictionary for `git cola` to use in its spell checker.
This should be configured to the path of a newline-separated list of words.

cola.expandtab
--------------
Expand tabs into spaces in the commit message editor.  When set to `true`,
`git cola` will insert a configurable number of spaces when tab is pressed.
The number of spaces is determined by `cola.tabwidth`.
Defaults to `false`.

cola.fileattributes
-------------------
Enables per-file gitattributes encoding support when set to `true`.
This tells `git cola` to honor the configured encoding when displaying
and applying diffs.

cola.fontdiff
-------------
Specifies the font to use for `git cola`'s diff display.

cola.hidpi
-------------
Specifies the High DPI displays scale factor. Set `0` to automatically scaled.
Setting value between 0 and 1 is undefined.
This option requires at least Qt 5.6 to work.
See `Qt QT_SCALE_FACTOR documentation <https://doc.qt.io/qt-5/highdpi.html>`_
for more information.

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
`git config --add cola.icontheme $theme`.

This setting can be overridden by the `GIT_COLA_ICON_THEME` environment
variable, which can specify multiple themes using a colon-separated value.

The icon theme can also be specified by passing `--icon-theme=<theme>` on the
command line, once for each icon theme, in the order that they should be
searched.  This can be used to override a subset of the icons, and fallback
to the built-in icons for the remainder.

cola.inotify
------------
Set to `false` to disable file system change monitoring.  Defaults to `true`,
but also requires either Linux with inotify support or Windows with `pywin32`
installed for file system change monitoring to actually function.

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

cola.maxrecent
--------------
`git cola` caps the number of recent repositories to avoid cluttering
the start and recent repositories menu.  The maximum number of repositories to
remember is controlled by `cola.maxrecent` and defaults to `8`.

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

cola.tabwidth
-------------
The number of columns occupied by a tab character.  Defaults to 8.

cola.terminal
-------------
The command to use when launching commands within a graphical terminal.

`cola.terminal` defaults to `xterm -e` when unset.
e.g. when opening a shell, `git cola` will run `xterm -e $SHELL`.

If either `gnome-terminal`, `xfce4-terminal`, or `konsole` are installed
then they will be preferred over `xterm` when `cola.terminal` is unset.

cola.textwidth
--------------
The number of columns used for line wrapping.
Tabs are counted according to `cola.tabwidth`.

cola.theme
--------------
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

If unset, or set wrong value, then the default style will be
used. The `default` theme is generated by Qt internal engine and should look
most native but may look noticeable differently on various systems. The flat
themes on the other hand should look similar (but not identical) on various
systems.

The GUI theme can also be specified by passing `--theme=<name>` on the
command line.

cola.turbo
----------
Set to `true` to enables "turbo" mode.  "Turbo" mode disables some
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
e.g. `gvim -f -p`.

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

GIT_COLA_ICON_THEME
-------------------
When set in the environment, `GIT_COLA_ICON_THEME` overrides the
theme specified in the `cola.icontheme` configuration.
Read the section on `cola.icontheme` above for more details.

GIT_COLA_SCALE
--------------
.. Important:: `GIT_COLA_SCALE` should not be used with newer versions of Qt.

    Set `QT_AUTO_SCREEN_SCALE_FACTOR` to `1` and Qt will automatically
    scale the interface to the correct size based on the display DPI.
    This option is also available by setting `cola.hidpi` configuration.

    See the `Qt High DPI documentation <https://doc.qt.io/qt-5/highdpi.html>`_
    for more details.

`git cola` can be made to scale its interface for HiDPI displays.
When defined, `git cola` will scale icons, radioboxes, and checkboxes
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
Show only unmerged branches in the revprompt subdialog. This is useful for
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
See http://qt-project.org/doc/qt-4.8/qkeysequence.html#QKeySequence-2
for more details about the supported values.

Avoid creating shortcuts that conflict with existing built-in `git cola`
shortcuts.  Creating a conflict will result in no action when the shortcut
is used.

SETTING UP GPG FOR SIGNED COMMITS
=================================
When creating signed commits `gpg` will attempt to read your password from the
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

Once this has been setup then you will need to reload your gpg-agent config.::

    echo RELOADAGENT | gpg-connect-agent

If you see the following output::

    OK

Then the daemon is already running, and you do not need to start it yourself.

If it is not running, eval the output of `gpg-agent --daemon` in your shell
prior to launching `git cola`.::

    eval $(gpg-agent --daemon)
    git cola

WINDOWS NOTES
=============

Git Installation
----------------
If Git is installed in a custom location, e.g. not installed in `C:/Git` or
Program Files, then the path to Git must be configured by creating a file in
your home directory `~/.config/git-cola/git-bindir` that points to your git
installation.  e.g.::

    C:/Tools/Git/bin

LINKS
=====

Git Cola's Git Repository
-------------------------
https://github.com/git-cola/git-cola/

Git Cola Homepage
-----------------
https://git-cola.github.io/

Mailing List
------------
https://groups.google.com/group/git-cola
