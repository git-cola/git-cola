.. _unreleased:

Latest Release
==============

:ref:`v2.4 <v2.4>` is the latest stable release.

Development version
===================

Clone the git-cola repo to get the latest development version:

``git clone git://github.com/git-cola/git-cola.git``

Unreleased Topics
=================

Usability, bells and whistles
-----------------------------

* The icon for untracked files was adjusted to better differentiate
  between files and the "Untracked" header.

  https://github.com/git-cola/git-cola/issues/509

* Ctrl+O was added as a hotkey for opening repositories.

  https://github.com/git-cola/git-cola/pull/507

* `git dag` now uses consistent edge colors across updates.

  https://github.com/git-cola/git-cola/issues/512

* `git cola`'s Bookmarks widget can now be used to set a "Default Repository".
  Under the hood, we set the `cola.defaultrepo` configuration variable.
  The default repository is used whenever `git cola` is launched outside of
  a Git repostiory.  When unset, or when set to a bogus value, `git cola`
  will still prompt for a repository.

  https://github.com/git-cola/git-cola/issues/513

* `git cola`'s Russian and Spanish translations were improved.

  https://github.com/git-cola/git-cola/pull/514

  https://github.com/git-cola/git-cola/pull/515

* `git dag` now allows selecting non-contiguous ranges in the log widget.

  https://github.com/git-cola/git-cola/issues/468
