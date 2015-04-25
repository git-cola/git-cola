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

Clone the git-cola repo to get the latest development version:

``git clone git://github.com/git-cola/git-cola.git``
