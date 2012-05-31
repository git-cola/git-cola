=====
Tools
=====
The `git cola` interface is composed of various cooperating tools.
Double-clicking a tool opens it in its own subwindow.
Dragging it around moves and places it within the window.

Tools can be hidden and rearranged however you like.
`git cola` carefully remembers your window layout and restores
it the next time it is launched.

A hidden tool can be re-opened using the `Tools` menu as well
as the `Alt-1,2,3,...`, shortcut keys.

.. _status:

Status
======
The `Status` tool provides a visual analog to the
`git status <http://schacon.github.com/git/git-status.html>`_ command.

`Status` displays files that are `modified` relative to the staging area,
`staged` for the next commit, `unmerged` files from an in-progress merge,
and files that are `untracked` to git.

These are the same categories one sees when running
`git status <http://schacon.github.com/git/git-status.html>`_
on the command line.

You can navigate through the list of files using keyboard arrows as well
as the ergonomical and vim-like `j` and `k` shortcut keys.

There are several convenient ways to interact with files in the `Status` tool.
Selecting a file displays its diff in the :ref:`Diff <diff>` viewer.
Double-clicking a file stages its contents, as does the
the `Ctrl-s` shortcut key.

`Ctrl-e` opens selected files in the conifgured `$EDITOR`, and
`Ctrl-d` opens selected files using
`git difftool <http://schacon.github.com/git/git-difftool.html>`_.

Additional actions can be performed using the right-click context menu.

Configuring your $EDITOR
------------------------
The editor used by `Ctrl-e` is configured from the Preferences screen.
The environment variables `$VISUAL` and `$EDITOR` are used when no editor
has been configured.

The editor preference is saved in the `gui.editor` variable using
`git config <http://schacon.github.com/git/git-config.html>`_.

*ProTip* -- Setting `gvim -p` as your configured editor opens
multiple files using tabs (and `gvim -o` uses splits).

`git cola` is {vim, emacs, textpad, notepad++}-aware.
When you select a line in the `grep` screen and press any of
`Enter`, `Ctrl-e`, or the "Edit" button, you are taken to that exact line.

Actions
-------
Clicking the `Staged` folder shows a diffstat for the index.

Clicking the `Modified` folder shows a diffstat for the worktree.

Clicking individual files sends diffs to the `Diff Display`.

Double-clicking individual files adds and removes their content from the index.

Various actions that are available through the right-click context menu.
Different actions are available depending a file's status.

Staged Files
~~~~~~~~~~~~
Unstage Selected
    Remove from the index/staging area with
    `git reset <http://schacon.github.com/git/git-reset.html>`_

Launch Editor
    Launch the configured visual editor

Launch Difftool
    Visualize changes with
    `git difftool <http://schacon.github.com/git/git-difftool.html>`_

Revert Unstaged Edits
    Throw away unstaged edits.

Modified Files
~~~~~~~~~~~~~~
Stage Selected
    Add to the staging area with
    `git add <http://schacon.github.com/git/git-add.html>`_

Launch Editor
    Launches the configured visual text editor

Launch Difftool
    Visualize changes relative to the index with
    `git difftool <http://schacon.github.com/git/git-difftool.html>`_

Revert Unstaged Edits
    Reverts unstaged content by checking out selected paths
    from the index/staging area

Revert Uncommited Edits
    Throws away uncommitted edits


Unmerged Files
~~~~~~~~~~~~~~
Launch Merge Tool
    Resolve conflicts using
    `git mergetool <http://schacon.github.com/git/git-mergetool.html>`_

Stage Selected
    Mark as resolved using
    `git add <http://schacon.github.com/git/git-add.html>`_

Launch Editor
    Launch the configured visual text editor


Untracked Files
~~~~~~~~~~~~~~~
Stage Selected
    Add to the index/staging area with
    `git add <http://schacon.github.com/git/git-add.html>`_

Launch Editor
    Launch the configured visual text editor

Delete File(s)
    Delete files from the filesystem

Add to .gitignore
	Adds file/files to GIT ignore list for untracked files

.. _diff:

Diff
====
The diff viewer/editor displays diffs for selected files.
Additions are shown in green and removals are displayed in light red.
Extraneous whitespace is shown with a pure-red background.

Right-clicking in the diff provides access to additional actions
that use either the cursor location or text selection.

Staging content for commit
--------------------------
The ``@@`` patterns denote a new diff region.  Selecting lines of diff
and using the `Stage Selected` command will stage just the selected lines.
Clicking within a diff region and selecting `Stage Section` stages the
entire patch region.

The corresponding opposite commands can be performed on staged files as well,
e.g. staged content can be selectively removed from the index when we are
viewing diffs for staged content.

Commit Message Editor
=====================
The `git cola` commit message editor is a simple text widget
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
to `git commit <http://schacon.github.com/git/git-commit.html>`_.


Commit
------
The commit button runs
`git commit <http://schacon.github.com/git/git-commit.html>`_.
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
`git log <http://schacon.github.com/git/git-log.html>`_
is a great tool but long lines mess up its formatting for everyone else,
so please be mindful when writing commit messages.


Amend Last Commit
-----------------
Clicking on `Amend Last Commit` makes `git cola` amend the previous commit
instead of creating a new one.  `git cola` loads the previous commit message
into the commit message editor when this option is selected.

The `Status` tool will display all of the changes for the amended commit.
