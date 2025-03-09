=======
git-dag
=======

SYNOPSIS
========

``git dag [options] [<revision-range>] [[--] [<path>...]]``


DESCRIPTION
===========

`git-dag` is an advanced Git history visualizer that presents ``git log``'s
powerful features in an easy to use graphical interface.


OPTIONS
=======

``<revision-range>``
--------------------

Show only commits in the specified revision range.
When no ``<revision-range>`` is specified, it defaults to ``HEAD``
(i.e. the whole history leading to the current commit).

``origin..HEAD`` specifies all the commits reachable from the current commit
(i.e.  ``HEAD``), but not from ``origin``.

For a complete list of ways to spell ``<revision-range>``, see the Specifying Ranges
section of `gitrevisions(7) <https://git-scm.com/docs/gitrevisions>`_
(``man gitrevisions``).

``--prompt``
------------

Prompt for a Git repository instead of using the current directory.

``-r, --repo <path>``
---------------------

Open the git repository located at ``<path>``.
Defaults to the current directory.

``--version``
-------------

Print the version number and exit.

``-h, --help``
--------------

Show usage and optional arguments.


Log Arguments
=============

The ``Log`` text field allows you to pass arguments to `git log`.
This can be used to filter the displayed history, for example
entering `main -- Makefile` will display only commits on the
`main` branch that touch the `Makefile`.

The `Log` text field lets you interactively edit and replace the
``[<revision-range>] [[--] [<path>...]]`` arguments that were initially
specified on the command-line.


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
