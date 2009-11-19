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
* Add missing 'Exit Diff Mode' button for 'Diff Expression' mode

  http://github.com/davvid/git-cola/issues/closed/#issue/31

* Fix a bug when initializing fonts on Windows

  http://github.com/davvid/git-cola/issues/closed/#issue/32


git-cola v1.4.0.1
=================

Fixes
-----
* The classic view keeps entries in sorted order
* Staging untracked files works again

  http://github.com/davvid/git-cola/issues/closed/#issue/27

* Fix the 'show' command in the Stash dialog

  http://github.com/davvid/git-cola/issues/closed/#issue/29

* Fix a typo when loading merge commit messages

  http://github.com/davvid/git-cola/issues/closed/#issue/30


git-cola v1.4.0
===============

This release focuses on a redesign of the git-cola user interface,
a tags interface, and better integration of the 'cola classic' widget.
A flexible interface based on configurable docks is used to manage the
various cola widgets.

Usability, bells and whistles
-----------------------------
* New main GUI is flexible and user-configurable
* Individual widgets can be detached and rearranged arbitrarily
* Add an interface for creating tags
* Provide a fallback `SSH_ASKPASS` implementation to prompt for
  SSH passwords on fetch/push/pull
* The commit message editor displays the current row/column and
  warns when lines get too long
* The cola classic widget displays upstream changes
* `git cola --classic` launches cola classic in standalone mode
* Provide more information in log messages

Fixes
-----
* Inherit the window manager's font settings
* Miscellaneous PyQt4 bug fixes and workarounds

Developer
---------
* Removed all usage of Qt Designer `.ui` files
* Simpler model/view architecture
* Selection now lives in the model
* Centralized model notifications are used to keep views in sync
* The git command class was made thread-safe
* Less coupling between model and view actions
* The status view was rewritten to use the MVC architecture
* Added more documentation and tests


git-cola v1.3.9
===============

Usability, bells and whistles
-----------------------------
* Add a `classic` view for browsing the entire repository
* Handle diff expressions with spaces
* Handle renamed files

Portability
-----------
* Handle carat `^` characters in diff expressions on Windows
* Workaround a PyQt 4.5/4.6 QThreadPool bug

Documentation
-------------
* Add keyboard shortcut documentation
* Add more API documentation

Fixes
-----
* Fix the diff expression used when reviewing branches
* Fix a bug when pushing branches
* Fix X11 warnings
* Fix interrupted system calls on Mac OS X


git-cola v1.3.8
===============

Usability, bells and whistles
-----------------------------
* Fresh and tasty SVG logos
* Branch review mode for reviewing topic branches
* Diff modes for diffing between tags, branches, or arbitrary diff expressions.
* The push dialog now selects the current branch by default. This is to prepare for upcoming git changes where git push will warn and later refuse to push when git-push is run without arguments
* Support `open` and `clone` commands on Windows
* Allow saving cola UI layouts
* Re-enable double-click-to-stage for unmerged entries.
  Disabling it for unmerged items was inconsistent, though safer
* Show diffs when navigating the status tree with the keyboard

Packaging
---------
* Work around `pyuic4` bugs in the setup.py build script
* Mac OSX application bundles now available for download


git-cola v1.3.7
===============

Subsystems
----------
* `git-difftool` is now an official git command as of `git-v1.6.3`.
* `git-difftool` learned `--no-prompt` / `-y` and a corresponding
  `difftool.prompt` configuration variable

Usability, bells and whistles
-----------------------------
* Warn when non-ffwd is used for push/pull
* Allow `Ctrl+C` to exit cola when run from the command line

Fixes
-----
* Support Unicode fonts
* Handle interrupted system calls

Developer
---------
* PEP-8-ify more of the cola code base
* Added more tests

Packaging
---------
* All resources are installed into `$prefix/share/git-cola`.
* Closes Debian bug #519972

  http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=519972


git-cola v1.3.6
===============

Subsystems
----------
* Support Kompare in `git-difftool`
* Add a unique configuration namespace for `git-difftool`
* The diff.tool git-config value defines the default diff tool

Usability, bells and whistles
-----------------------------
* The stash dialog allows passing the `--keep-index` option
* Warn when amending a published commit
* Simplify the file-across-revisions comparison dialog
* Select `origin` by default in fetch/push/pull
* Remove the search field from the log widget
* The log window moved into a drawer widget at the bottom of the UI
* Log window display can be configured with
  `cola.showoutput` = `{never, always, errors}`.
  `errors` is the default

Developer
---------
* Improve nose unittest usage

Packaging
---------
* Add a Windows/msysGit installer
* Include private versions of `simplejson` and `jsonpickle`
  for ease of installation and development
