.. _unreleased:

Latest Release
==============

:ref:`v2.2.1 <v2.2.1>` is the latest stable release.

Unreleased Topics
=================

Usability, bells and whistles
-----------------------------

* The Interactive Rebase feature now works on Windows!

  https://github.com/git-cola/git-cola/issues/463

* The `diff` editor now understands vim-style `hjkl` navigation hotkeys.

  https://github.com/git-cola/git-cola/issues/476

* The `Rename branch` menu action is now disabled in empty repositories.

  https://github.com/git-cola/git-cola/pull/475

  https://github.com/git-cola/git-cola/issues/459

* `git cola` now checks unmerged files for conflict markers before
  staging them.  This feature can be disabled in the preferences.

  https://github.com/git-cola/git-cola/issues/464

Fixes
-----

* Diff syntax highlighting was improved to handle more edge cases
  and false positives.

  https://github.com/git-cola/git-cola/pull/467

* Setting commands in the interactive rebase editor was fixed.

  https://github.com/git-cola/git-cola/issues/472

* git-cola no longer clobbers the Ctrl+Backspace text editing shortcut
  in the commit message editor.

  https://github.com/git-cola/git-cola/issues/453

Development version
===================

Clone the git-cola repo to get the latest development version:

``git clone git://github.com/git-cola/git-cola.git``
