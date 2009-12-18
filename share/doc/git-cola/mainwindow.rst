===========
Main Window
===========
This image shows the main `git-cola` interface.

.. figure:: images/cola-macosx.png
    :align: center

    `git-cola` running on Mac OSX

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

