.. _unreleased:

Latest Release
==============

:ref:`v2.1.2 <v2.1.2>` is the latest stable release.

Unreleased Topics
=================

* The stash viewer now uses ``git show --no-ext-diff`` to avoid running
  user-configured diff tools.

* Double-click will now choose a commit in the "Select commit" dialog.

* `git cola` has a feature that reads `.git/MERGE_MSG` and friends for the
  commit message when a merge is in-progress.  Upon refresh, `git cola` will
  now detect when a merge has completed and reset the commit message back to
  its previous state.  It is only reset if the editor contains a message
  that was read from the file and has not been manually edited by the user.

* The commit message editor's context menu now has a "Clear..." action for
  clearing the message across both the summary and description fields.

* `git cola` now uses the `setsid()` system call to ensure that the
  `GIT_ASKPASS` and `SSH_ASKPASS` helper programs are used when pushing
  changes using `git`.  The askpass helpers will now be used even when
  `git cola` is launched from a terminal.

  The behavior without `setsid()` is that `git cola` can appear to hang while
  pushing changes.  The hang happens when `git` prompts the user for a
  password using the terminal, but the user never sees the prompt.  `setsid()`
  detaches the terminal, which ensures that the askpass helpers are used.

  https://github.com/git-cola/git-cola/issues/218

  https://github.com/git-cola/git-cola/issues/262

  https://github.com/git-cola/git-cola/issues/377

* `git dag`'s file list tool was updated to properly handle unicode paths.

* `gnome-terminal` is no longer used by default when `cola.terminal` is unset.
  It is broken, as was detailed in #456.

  https://github.com/git-cola/git-cola/issues/456

* Traditional Chinese (Taiwan) translation updates.

* The interactive rebase feature was not always setting `$GIT_EDITOR`
  to the value of `gui.editor`, thus there could be instances where rebase
  will seem to not stop, or hang, when performing "reword" actions.

  We now set the `$GIT_EDITOR` environment variable when performing the
  "Continue", "Skip", and "Edit Todo" rebase actions so that the correct
  editor is used during the rebase.

  https://github.com/git-cola/git-cola/issues/445

* The system theme's icons are now used whereever possible.

  https://github.com/git-cola/git-cola/pull/458

Development version
===================

Clone the git-cola repo to get the latest development version:

``git clone git://github.com/git-cola/git-cola.git``
