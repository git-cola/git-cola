==========
User Guide
==========

* :ref:`Introduction <intro>`
* :ref:`Main Window <mainwindow>`
* :ref:`Shortcut Keys <shortcuts>`


.. _intro:

Introduction
============
`git-cola` is a powerful GUI for `git` that gives you an easy way to
interact with git repositories.


.. _mainwindow:

Main Window
===========
This image shows the main `git-cola` interface.

.. figure:: images/cola-macosx.png

    git-cola running on Mac OSX

1. Repository Status
--------------------

The repository status view displays paths that git detects as either
staged for the next commit (`Staged`),
modified relative to the staging area (`Modified`), or
an unresolved file from a merge (`Unmerged`).

A file can be staged or unstaged by either double-clicking on its name or
single-clicking on its icon.  Right-clicking on an entry displays additional
actions that can be performed such as launching `git-difftool` or
`git-mergetool`.

2. Diff View
------------

The diff view displays diffs for selected files.
Additions are shown in green and removals are displayed in light red.
Extraneous whitespace is shown in a pure red background.

Right-clicking in the diff view provides access to additional actions
that can operate on the cursor location or selection.

3. Diff Hunks
-------------

The `@@` diff headers divide each diff region.  Selecting specific lines
and using the `Stage / Unstage Selected` actions will operate on that
subset of the diff.  Clicking within a diff region and selecting
the `Stage / Unstage Hunk` action will operate on the entire region
within the diff header.


.. _shortcuts:

Main Shortcut Keys
==================
* :command:`h` -- Stage/unstage hunk at text cursor position
* :command:`s` -- Stage/unstage selection
* :command:`ctrl-b` -- Create branch
* :command:`alt-b` -- Checkout branch
* :command:`ctrl-d` -- Diffstat the most recent commit
* :command:`ctrl-e` -- Export patches
* :command:`ctrl-p` -- Cherry-pick
* :command:`ctrl-r` -- Rescan/refresh repository status
* :command:`alt-a` -- Stage all modified files
* :command:`alt-u` -- Stage all untracked files
* :command:`alt-t` -- Stage selected files
* :command:`shift-alt-s` -- Stash dialog


Classic View Shortcut Keys
==========================
* :command:`h` -- Move to parent/collapse
* :command:`j` -- Move down
* :command:`k` -- Move up
* :command:`l` -- Expand directory
* :command:`ctrl-e` -- Launch Editor
* :command:`ctrl-s` -- Stage Selected
* :command:`ctrl-u` -- Unstage Selected
* :command:`shift-ctrl-h` -- View History
* :command:`ctrl-d` -- View Diff (`git difftool <path>`)
* :command:`shift-ctrl-d` -- Diff Against Predecessor
* :command:`ctrl-z` -- Revert uncommitted changes (`git checkout HEAD <path>...`)
