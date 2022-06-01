==========
git-dag(1)
==========

SYNOPSIS
========
git dag [options] [<since>..<until>] [[--] [<path>...]]

DESCRIPTION
===========
`git-dag` is a powerful Git history visualizer.
`git-dag` presents powerful `git log` features in a simple-to-use
graphical interface.

OPTIONS
=======

--prompt
--------
Prompt for a Git repository instead of using the current directory.

-r, --repo <path>
-----------------
Run `git dag` on the git repository in `<path>`.
Defaults to the current directory.

--version
---------
Print the `git dag` version and exit.

-h, --help
----------
Show usage and optional arguments.

Log Options
===========
The `Log` prompt allows you to pass arguments to `git log`.
This can be used to filter the displayed history, for example
entering `main -- Makefile` will display only commits on the
`main` branch that touch the `Makefile`.

CONTEXT-MENU ACTIONS
====================
The right-click menu can be used to perform various actions.
All actions operate on the selected commit.

You can create branches and tags, cherry-pick commits, save patches,
export tarballs, and grab files from older commits using the context menu.

DIFF COMMITS
============
You can diff arbitrary commits.  Select a single commit in either the list
view or the graph view and then right-click on a second commit.

A menu will appear allowing you to diff the two commits.

SHORTCUTS
=========
You can run commands using dedicated shortcuts. Select a single commit
and then press `Ctrl-Alt-c` to copy sha1 or `Ctrl-d` to run diff tool.

You can read more about hotkeys from 'keyboard shortcuts' window or context menu.

CONFIGURATION VARIABLES
=======================

log.date
--------
Set the default date-time format for the 'Date' field.
Setting a value for log.date is similar to using `git log`'s
`--date` option.  Possible values are `relative`, `local`,
`default`, `iso`, `rfc`, and `short`; see git-log(1) for details.
