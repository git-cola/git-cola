git-cola v1.4.1.2
=================

Usability, bells and whistles
-----------------------------
* It is now possible to checkout from the index as well
  as from `HEAD`.  This corresponds to the
  `Removed Unstaged Changes` action in the `Repository Status` tool.
* The `remote` dialogs (fetch, push, pull) are now slightly
  larger by default.
* Added more user documentation.  We now include many links to
  external git resources.

Fixes
-----
* Fixed a missing ``import`` when showing `right-click` actions
  for unmerged files in the `Repository Status` tool.
* ``git update-index --refresh`` is no longer run everytime
  ``git cola version`` is run.

Packaging
---------
* The ``Makefile`` will now conditionally include a ``config.mak``
  file located at the root of the project.  This allows for user
  customizations such as changes to the ``$prefix`` variable
  to be stored in a file so that custom settings do not need to
  be specified every time on the command-line.
* The build scripts no longer require a ``.git`` directory to
  generate the ``builtin_version.py`` module.  The release tarballs
  now include a ``version`` file at the root of the project which
  is used in lieu of having the Git repository available.
  This allows for ``make clean && make`` to function outside of
  a Git repository.
* Added maintainer's ``make dist`` target to the ``Makefile``.


git-cola v1.4.1.1
=================

Usability, bells and whistles
-----------------------------
* We now use patience diff by default when it is available via
  `git diff --patience`.

* Allow closing the `cola classic` tool with `Ctrl+W`.

* Update desktop menu entry to read `Cola Git GUI`.

Fixes
-----
* Fixed an unbound variable error in the `push` dialog.

Packaging
---------
* Don't include `simplejson` in MANIFEST.in.
* Update desktop entry to read `Cola Git GUI`.


git-cola v1.4.1
===============

This feature release adds two new features directly from
`git-cola`'s github issues backlog.  On the developer
front, further work was done towards modularizing the code base.

Usability, bells and whistles
-----------------------------
* Dragging and dropping patches invokes `git-am`

  http://github.com/davvid/git-cola/issues/closed#issue/3

* A dialog to allow opening or cloning a repository
  is presented when `git-cola` is launched outside of a git repository.

  http://github.com/davvid/git-cola/issues/closed/#issue/22

* Warn when `push` is used to create a new branch

  http://github.com/davvid/git-cola/issues/closed#issue/35

* Optimized startup time by removing several calls to `git`.


Portability
-----------
* `git-cola` is once again compatible with PyQt 4.3.x.

Developer
---------
* `cola.gitcmds` was added to factor out git command-line utilities
* `cola.gitcfg` was added for interacting with `git-config`
* `cola.models.browser` was added to factor out repobrowser data
* Added more tests


git-cola v1.4.0.5
=================

Fixes
-----
* Fix launching external applications on Windows
* Ensure that the `amend` checkbox is unchecked when switching modes
* Update the status tree when amending commits


git-cola v1.4.0.4
=================

Packaging
---------
* Fix Lintian warnings


git-cola v1.4.0.3
=================

Fixes
-----
* Fix X11 warnings on application startup


git-cola v1.4.0.2
=================

Fixes
-----
* Added missing 'Exit Diff Mode' button for 'Diff Expression' mode

  http://github.com/davvid/git-cola/issues/closed/#issue/31

* Fix a bug when initializing fonts on Windows

  http://github.com/davvid/git-cola/issues/closed/#issue/32


git-cola v1.4.0.1
=================

Fixes
-----
* Keep entries in sorted order in the `cola classic` tool
* Fix staging untracked files

  http://github.com/davvid/git-cola/issues/closed/#issue/27

* Fix the `show` command in the Stash dialog

  http://github.com/davvid/git-cola/issues/closed/#issue/29

* Fix a typo when loading merge commit messages

  http://github.com/davvid/git-cola/issues/closed/#issue/30


git-cola v1.4.0
===============

This release focuses on a redesign of the git-cola user interface,
a tags interface, and better integration of the `cola classic` tool.
A flexible interface based on configurable docks is used to manage the
various cola widgets.

Usability, bells and whistles
-----------------------------
* New GUI is flexible and user-configurable
* Individual widgets can be detached and rearranged arbitrarily
* Add an interface for creating tags
* Provide a fallback `SSH_ASKPASS` implementation to prompt for
  SSH passwords on fetch/push/pull
* The commit message editor displays the current row/column and
  warns when lines get too long
* The `cola classic` tool displays upstream changes
* `git cola --classic` launches `cola classic` in standalone mode
* Provide more information in log messages

Fixes
-----
* Inherit the window manager's font settings
* Miscellaneous PyQt4 bug fixes and workarounds

Developer
---------
* Removed all usage of Qt Designer `.ui` files
* Simpler model/view architecture
* Selection is now shared across tools
* Centralized notifications are used to keep views in sync
* The `cola.git` command class was made thread-safe
* Less coupling between model and view actions
* The status view was rewritten to use the MVC architecture
* Added more documentation and tests


git-cola v1.3.9
===============

Usability, bells and whistles
-----------------------------
* Added a `cola classic` tool for browsing the entire repository
* Handle diff expressions with spaces
* Handle renamed files

Portability
-----------
* Handle carat `^` characters in diff expressions on Windows
* Worked around a PyQt 4.5/4.6 QThreadPool bug

Documentation
-------------
* Added a keyboard shortcuts reference page
* Added developer API documentation

Fixes
-----
* Fix the diff expression used when reviewing branches
* Fix a bug when pushing branches
* Fix X11 warnings at startup
* Fix more interrupted system calls on Mac OS X


git-cola v1.3.8
===============

Usability, bells and whistles
-----------------------------
* Fresh and tasty SVG logos
* Added `Branch Review` mode for reviewing topic branches
* Added diff modes for diffing between tags, branches,
  or arbitrary `git diff` expressions
* The push dialog selects the current branch by default.
  This is in preparation for `git-1.7.0` where unconfigured `git push`
  will refuse to push when run without specifying the remote name
  and branch.  See the `git` release notes for more information
* Support `open` and `clone` commands on Windows
* Allow saving cola UI layouts
* Re-enabled `double-click-to-stage` for unmerged entries.
  Disabling it for unmerged items was inconsistent, though safer.
* Show diffs when navigating the status tree with the keyboard

Packaging
---------
* Worked around `pyuic4` bugs in the `setup.py` build script
* Added Mac OSX application bundles to the download page


git-cola v1.3.7
===============

Subsystems
----------
* `git-difftool` became an official git command in `git-1.6.3`.
* `git-difftool` learned `--no-prompt` / `-y` and a corresponding
  `difftool.prompt` configuration variable

Usability, bells and whistles
-----------------------------
* Warn when `non-fast-forward` is used with fetch, push or pull
* Allow `Ctrl+C` to exit cola when run from the command line

Fixes
-----
* Support Unicode font names
* Handle interrupted system calls

Developer
---------
* `PEP-8`-ified more of the cola code base
* Added more tests

Packaging
---------
* All resources are now installed into `$prefix/share/git-cola`.
  Closed Debian bug #519972

  http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=519972


git-cola v1.3.6
===============

Subsystems
----------
* Added support for Kompare in `git-difftool`
* Added a separate configuration namespace for `git-difftool`
* Added the `diff.tool` configuration variable to define the default diff tool

Usability, bells and whistles
-----------------------------
* The stash dialog allows passing the `--keep-index` option to `git stash`
* Amending a published commit warns at commit time
* Simplified the file-across-revisions comparison dialog
* `origin` is selected by default in fetch/push/pull
* Removed the search field from the log widget
* The log window moved into a drawer widget at the bottom of the UI
* Log window display can be configured with
  `cola.showoutput` = `{never, always, errors}`.  `errors` is the default.
  `NOTE` -- this variable was removed with the GUI rewrite in 1.4.0.

Developer
---------
* Improved nose unittest usage

Packaging
---------
* Added a Windows/msysGit installer
* Included private versions of `simplejson` and `jsonpickle`
  for ease of installation and development
