git-cola v1.8.2
===============
Usability, bells and whistles
-----------------------------
* We now automatically remove missing repositories from the
  "Select Repository" dialog.

  http://github.com/git-cola/git-cola/issues/145

* A new `git cola diff` sub-command was added for diffing changed files.

Fixes
-----
* The inotify auto-refresh feature makes it difficult to select text in
  the "diff" editor when files are being continually modified by another
  process.  The auto-refresh causes it to lose the currently selected text,
  which is not wanted.  We now avoid this problem by saving and restoring
  the selection when refreshing the editor.

  http://github.com/git-cola/git-cola/issues/155

* More strings have been marked for l10n.

  http://github.com/git-cola/git-cola/issues/157

* Fixed the Alt+D Diffstat shortcut.

  http://github.com/git-cola/git-cola/issues/159

Fixes
-----
* Better error handling when cloning repositories.

  We were not handling the case where a git URL has
  no basename, e.g. `https://git.example.com/`.
  `git cola` originally rejected these URLs instead of
  allowing users to clone them.  It now allows these URLs
  when they point to valid git repositories.

  Additionally, `git cola` learned to echo the errors
  reported by `git clone` when it fails.

  http://github.com/git-cola/git-cola/issues/156

git-cola v1.8.1
===============
Usability, bells and whistles
-----------------------------
* `git dag` got a big visual upgrade.

* Ctrl+G now launches the "Grep" tool.

* Ctrl+D launches difftool and Ctrl+E launches your editor
  when in the diff panel.

* git-cola can now be told to use an alternative language.
  For example, if the native language is German and we want git-cola to
  use English then we can create a `~/.config/git-cola/language` file with
  "en" as its contents:

  $ echo en >~/.config/git-cola/language

  http://github.com/git-cola/git-cola/issues/140

* A new `git cola merge` sub-command was added for merging branches.

* Less blocking in the main UI

Fixes
-----
* Autocomplete issues on KDE

  http://github.com/git-cola/git-cola/issues/144

* The "recently opened repositories" startup dialog did not
  display itself in the absence of bookmarks.

  http://github.com/git-cola/git-cola/issues/139

git-cola v1.8.0
===============
Usability, bells and whistles
-----------------------------
* `git cola` learned to honor `.gitattributes` when showing and
  interactively applying diffs.  This makes it possible to store
  files in git using a non-utf-8 encoding and `git cola` will
  properly accept them.  This must be enabled by settings
  `cola.fileattributes` to true, as it incurs a small performance
  penalty.

  http://github.com/git-cola/git-cola/issues/96

* `git cola` now wraps commit messages at 72 columns automatically.
  This is configurable using the `cola.linebreak` variable to enable/disable
  the feature, and `cola.textwidth` to configure the limit.

  http://github.com/git-cola/git-cola/issues/133

* A new "Open Recent" sub-menu was added to the "File" menu.
  This makes it easy to open a recently-edited repository.

  http://github.com/git-cola/git-cola/issues/135

* We now show a preview for untracked files when they are clicked
  using the `Status` tool.
* A new "Open Using Default Application" action was added to the
  `Status` tool.  It is activated using either `Spacebar` or through
  the context menu.  This action uses `xdg-open` on Linux and
  `open` on Mac OS X.
* A new "Open Parent Directory" action was added to the `Status` tool.
  It is activated using either `Shift+Spacebar` or through the
  context menu.
* `git dag` learned to honor the `log.date` git configuration variable.
  This makes the date display follow whatever format the user has
  configured.
* A new `git cola config` sub-command was added for quickly
  tweaking `git cola`'s git configuration settings.
* Some small usability tweaks -- some user confirmation prompts
  were defaulting to "Cancel" when they should have been defaulting
  to the affirmative option instead.

Fixes
-----
* Properly handle arbitrarily-named branches.
* We went back to launching `git mergetool` using an xterm.
  The reason is that there are a couple of places where `git mergetool`
  requires a terminal for user interaction not covered by `--no-prompt`.
* We now properly handle an edge case when applying short diffs at
  the start of a file.

git-cola v1.7.7
===============
Usability, bells and whistles
-----------------------------
* New and improved `grep` mode lets you instantly find and edit files.
* New `git cola grep` standalone mode.
* Support for passing arguments to the configured editors, e.g. `gvim -p`
  This makes it possible to select multiple files in the status
  window and use `Ctrl-e` to edit them all at once.
* Remote operations now prompt on errors only.
* The `Tab` key now jumps to the extended description when editing the summary.
* More shortcut key labels and misc. UX improvements.

Fixes
-----
* Selecting an item no longer copies its filename to the copy/paste buffer.
  `Ctrl-c` or the "Copy" context-menu action can be used instead.
* The repository monitoring feature on Windows learned to ignore
  changes within the ".git" directory.  Thanks to Andreas Sommer.

  http://github.com/git-cola/git-cola/issues/120

git-cola v1.7.6
===============
Usability, bells and whistles
-----------------------------
* `git dag` learned to color-code branchy edges.
  The edge colors change when a new branch is detected,
  which makes the history much easier to follow.
  A huge thanks to Uri Okrent for making it happen.

* New GUI for editing remote repositories.

* New `git cola archive` and `git cola remote` sub-commands.

* `git cola browser` learned an 'Untrack' command.

* The diff editor learned to staged/unstaged while amending.

* The status tool can now scroll horizontally.

* New git repositories can be created by clicking 'New' on the
  `git cola --prompt` startup screen.

git-cola v1.7.5
===============
Usability, bells and whistles
-----------------------------
* Auto-completion was added to more tools.

* `git dag` is easier to use on smaller displays -- the author
  field elides its text which allows for a more compact display.

* Selected commits in `git dag` were made more prominent and
  easier to see.

* 'Create Branch' learned to fetch remote branches and uses a
  background thread to do so.

* User-configured GUI tools are listed alphabetically in the 'Actions' menu.

* The 'Pull' dialog remembers the value of the 'Rebase' checkbox
  between invocations.

git-cola v1.7.4.1
=================
Fixes
-----
* Detect Homebrew so that OS X users do not need to set PYTHONPATH.

* `git dag` can export patches again.

git-cola v1.7.4
===============
Usability, bells and whistles
-----------------------------
* The 'Classic' tool was renamed to 'Browser' and learned to
  limit history to the current branch.

* `git dag` learned about gravatar and uses it to show images
  for commit authors.

* `git dag` learned to use OpenGL for rendering resulting in
  much faster rendering.

* More dialogs learned vim-style keyboard shortcuts.

* The commit message editor learned better arrow key navigation.

git-cola v1.7.3
===============
Usability, bells and whistles
-----------------------------
* `git cola` learned a few new sub commands:

.. sourcecode:: sh

    git cola dag
    git cola branch
    git cola search

* `Return` in the summary field jumps to the extended description.

* `Ctrl+Return` is now a shortcut for 'Commit'.

* Better French translation for 'Sign-off'.

* The 'Search' widget now has a much simpler and streamlined
  user interface.

* vim-style `h,j,k,l` navigation shortcuts were added to the DAG widget.

* `git dag` no longer prompts for files when diffing commits if the
  text field contains paths.

* General user interface and performance improvements.

Fixes
-----
* The diff viewer no longer changes font size when holding `Control`
  while scrolling with the mouse wheel.

* Files with a typechange (e.g. symlinks that become files, etc.)
  are now correctly identified as being modified.

Packaging
---------
* The `cola.controllers` and `cola.views` packages were removed.

git-cola v1.7.2
===============
Usability, bells and whistles
-----------------------------
* `git cola` can now launch sub commands, e.g.:

.. sourcecode:: sh

    git cola classic
    git cola stash
    git cola fetch
    git cola push
    git cola pull
    git cola tag

* `git dag` is more responsive when gathering auto-completions.

* Keyboard shortcuts are displayed when the '?' key is pressed.

* Various keyboard shortcuts were added for improved usability.

* The status widget now lists unmerged files before modified files.

* vim-style `h,j,k,l` navigation shortcuts were added to the status widget.

* A 'Recently Modified Files...' tool was added.

* Tools can now be hidden with `Alt + #` (where `#` is a keyboard number)
  and focused with `Shift + Alt + #`.

* The syntax highlighting colors for diffs was made less intrusive.

* The commit message editor was redesigned to have a more compact
  and keyboard-convenient user interface.
  
* Keyboard shortcuts for adding a Signed-off-by (`Ctrl + i`)
  and creating a commit (`Ctrl + m`) were added.

* The status widget was adjusted to use less screen real-estate.

Fixes
-----
* Avoid updating the index when responding to inotify events.
  This avoids interfering with operations such as `git rebase --interactive`.

  http://github.com/git-cola/git-cola/issues/99

Packaging
---------
* Create `git-dag.pyw` in the win32 installer.

* win32 shortcuts now contain explicit calls to `pythonw.exe` instead of
  calling the `.pyw` file directly.

Deprecated Features
-------------------
* The 'Apply Changes from Branch...' feature was removed.
  `git dag`'s 'Grab File...' feature used alongside the index/worktree editor
  is a simpler alternative.

git-cola v1.7.1.1
=================
Fixes
-----
* Further enhanced the staging/unstaging behavior in the status widget.

  http://github.com/git-cola/git-cola/issues/97

* Unmerged files are no longer listed as modified.

Packaging
---------
The `cola-$version` tarballs on github were originally setup to
have the same contents as the old tarballs hosted on tuxfamily.
The `make dist` target was changed to write files to a
`git-cola-$version` subdirectory and tarball.

This makes the filenames consistent for the source tarball,
the darwin .app tarball, and the win32 .exe installer.

git-cola v1.7.1
===============
Usability, bells and whistles
-----------------------------
* Refined the staging/unstaging behavior for code reviews.

  http://github.com/git-cola/git-cola/issues/97

* Added more styling and icons to menus and buttons.

* Adjusted some terminology to more closely match the git CLI.

Fixes
-----
* Boolean `git config` settings with no value are now supported
  (these are not created by git these days but exist in legacy repositories).

* Unicode branches and tags are supported in the "branch diff" tool.

* Guard against low-memory conditions and more interrupted system calls.

Packaging
---------
* Added desktop launchers for git-cola.desktop and git-dag.desktop.
  This replaces the old cola.desktop, so some adjustments to RPM .spec
  and debian/ files will be needed.

* Fixed the darwin app-tarball Makefile target to create relative paths.

Cleanup
-------
* The `--style` option was removed.  `git cola` follows the system theme
  so there's no need for this option these days.

git-cola v1.7.0
===============
Usability, bells and whistles
-----------------------------
* Export a patch series from `git dag` into a `patches/` directory.

* `git dag` learned to diff commits, slice history along paths, etc.

* Added instant-preview to the `git stash` widget.

* A simpler preferences editor is used to edit `git config` values.

  http://github.com/git-cola/git-cola/issues/90

  http://github.com/git-cola/git-cola/issues/89

* Previous commit messages can be re-loaded from the message editor.

  http://github.com/git-cola/git-cola/issues/33

Fixes
-----
* Display commits with no file changes.

  http://github.com/git-cola/git-cola/issues/82

* Improved the diff editor's copy/paste behavior

  http://github.com/git-cola/git-cola/issues/90

Packaging
---------
* Bumped version number to ceil(minimum git version).
  `git cola` now requires `git` >= 1.6.3.

* Simplified git-cola's versioning when building from tarballs
  outside of git.  We no longer check for a 'version' file at
  the root of the repository.  We instead keep a default version
  in `cola/version.py` and use it when `git cola`'s `.git` repository
  is not available.

git-cola v1.4.3.5
=================
Usability, bells and whistles
-----------------------------
* inotify is much snappier and available on Windows
  thanks to Karl Bielefeldt.

* New right-click command to add untracked files to .gitignore
  thanks to Audrius Karabanovas.

* Stash, fetch, push, and pull usability improvements

* General usability improvements

* stderr is logged when applying partial diffs.

Fixes
-----
* Files can be unstaged when amending.

  http://github.com/git-cola/git-cola/issues/82

* Show the configured remote.$remote.pushurl in the GUI

  http://github.com/git-cola/git-cola/issues/83

* Removed usage of the "user" module.

  http://github.com/git-cola/git-cola/issues/86

* Avoids an extra `git update-index` call during startup.


git-cola v1.4.3.4
=================
Usability, bells and whistles
-----------------------------
* We now provide better feedback when `git push` fails.

  http://github.com/git-cola/git-cola/issues/69

* The Fetch, Push, and Pull dialogs now give better feedback
  when interacting with remotes.  The dialogs are modal and
  a progress dialog is used.

Fixes
-----
* More unicode fixes, again.  It is now possible to have
  unicode branch names, repository paths, home directories, etc.
  This continued the work initiated by Redhat's bugzilla #694806.

  https://bugzilla.redhat.com/show_bug.cgi?id=694806

git-cola v1.4.3.3
=================
Usability, bells and whistles
-----------------------------
* The `git cola` desktop launchers now prompt for a repo
  by default.  This is done by using the new `--prompt`
  flag which tells `git cola` to ignore any git repositories
  in the current directory and prompt for one instead.

Fixes
-----
* More Unicode fixes for repositories and home directories with
  embedded unicode characters.  Thanks to Christian Jann for
  patience and helpful bug reports.

* Fix the 'Clone' button in the startup dialog.

git-cola v1.4.3.2
=================
Usability, bells and whistles
-----------------------------
* Faster startup time! `git cola` now offloads initialization
  to a background thread so that the GUI appears almost instantly.

* Specialized diff options for p4merge, vimdiff, araxis, emerge,
  and ecmerge in difftool (backported from git.git).

Fixes
-----
* Fix launching commands in the background on Windows
  (e.g. when launching `git difftool`).

* Fix unicode errors when home or repository directories contain
  unicode characters.

  http://github.com/git-cola/git-cola/issues/74

  Redhat's bugzilla #694806

  https://bugzilla.redhat.com/show_bug.cgi?id=694806

git-cola v1.4.3.1
=================
Usability, bells and whistles
-----------------------------
* The `cola classic` tool can be now configured to be dockable.

  http://github.com/git-cola/git-cola/issues/56

* The `cola classic` tool now uses visual sigils to indicate a file's status.
  The idea and icons were provided by Uri Okrent.

* Include the 'Rescan' button in the 'Actions' widget regardless
  of whether inotify is installed.

Packaging
---------
* Fix installation of translations per Fedora
  This incorporates Fedora's fix for the translations path
  which originally appeared in cola-1.4.3-translations.patch.

* Mac OS X git-cola developers can now generate git-cola.app
  application bundles using 'make app-bundle'.

Fixes
-----
* Fixed a stacktrace when trying to use "Get Commit Message Template"
  with an unconfigured "commit.template" git config variable.

  http://github.com/git-cola/git-cola/issues/72

  This bug originated in Redhat's bugzilla #675721 via a Fedora user.

  https://bugzilla.redhat.com/show_bug.cgi?id=675721

* Properly raise the main window on Mac OS X.

* Properly handle staging a huge numbers of files at once.

* Speed up 'git config' usage by fixing cola's caching proxy.

* Guard against damaged ~/.cola files.

git-cola v1.4.3
===============
Usability, bells and whistles
-----------------------------
* `git dag` now has a separate display area
  for displaying commit metadata.  This area will soon
  grow additional functionality such as cherry-picking,
  branching, etc.

Fixes
-----
* Fixed tests from a previous refactoring.

* Guard against 'diff.external' configuration by always
  calling 'git diff' with the '--no-ext-diff' option.

  http://github.com/git-cola/git-cola/issues/67

* Respect 'gui.diffcontext' so that cola's diff display
  shows the correct number of context lines.

* Raise the GUI so that it is in the foreground on OS X.

Packaging
---------
* We now allow distutils to rewrite cola's shebang line.
  This allows us to run on systems where "which python"
  is Python3k.  This is exposed by setting the `PYTHON`
  Makefile variable to the location of python2.x.

* git-cola.app is now a tiny download because it no longer
  contains Qt and PyQt.  These libraries are provided as a
  separate download.

  http://code.google.com/p/git-cola/downloads/list

git-cola v1.4.2.5
=================
Usability, bells and whistles
-----------------------------
* Clicking on paths in the status widget copies them into the
  copy/paste buffer for easy middle-clicking into terminals.

* `Ctrl+C` in diff viewer copies the selected diff to the clipboard.

Fixes
-----
* Fixed the disappearing actions buttons on PyQt 4.7.4
  as reported by Arch and Ubuntu 10.10.

  http://github.com/git-cola/git-cola/issues/62

* Fixed mouse interaction with the status widget where some
  items could not be de-selected.

Packaging
---------
* Removed hard-coded reference to lib/ when calculating Python's
  site-packages directory.

git-cola v1.4.2.4
=================
Usability, bells and whistles
-----------------------------
* Removed "single-click to (un)stage" in the status view.
  This is a usability improvement since we no longer perform
  different actions depending on where a row is clicked.

* Added ability to create unsigned, annotated tags.

Fixes
-----
* Updated documentation to use `cola.git` instead of `cola.gitcmd`.

git-cola v1.4.2.3
=================
Usability, bells and whistles
-----------------------------
* Allow un/staging by right-clicking top-level items

  http://github.com/git-cola/git-cola/issues/57

* Running 'commit' with no staged changes prompts to allow
  staging all files.

  http://github.com/git-cola/git-cola/issues/55

* Fetch, Push, and Pull are now available via the menus

  http://github.com/git-cola/git-cola/issues/58

Fixes
-----
* Simplified the actions widget to work around a regression
  in PyQt4 4.7.4.

  http://github.com/git-cola/git-cola/issues/62

git-cola v1.4.2.2
=================
Usability, bells and whistles
-----------------------------
* `git dag` interaction was made faster.

Fixes
-----
* Added '...' indicators to the buttons for
  'Fetch...', 'Push...', 'Pull...', and 'Stash...'.

  http://github.com/git-cola/git-cola/issues/51

* Fixed a hang-on-exit bug in the cola-provided
  'ssh-askpass' implementation.

git-cola v1.4.2.1
=================
Usability, bells and whistles
-----------------------------
* Staging and unstaging is faster.

  http://github.com/git-cola/git-cola/issues/48

* `git dag` reads history in a background thread.

Portability
-----------
* Added :data:`cola.compat.hashlib` for `Python 2.4` compatibility
* Improved `PyQt 4.1.x` compatibility.

Fixes
-----
* Configured menu actions use ``sh -c`` for Windows portability.


git-cola v1.4.2
===============
Usability, bells and whistles
-----------------------------
* Added support for the configurable ``guitool.<tool>.*``
  actions as described in ``git-config(1)``.

  http://github.com/git-cola/git-cola/issues/44

  http://schacon.github.com/git/git-config.html

  This makes it possible to add new actions to `git cola`
  by simply editing ``~/.gitconfig``.  This implements the
  same guitool support as `git gui`.
* Introduced a stat cache to speed up `git config` and
  repository status checks.
* Added Alt-key shortcuts to the main `git cola` interface.
* The `Actions` dock widget switches between a horizontal
  and vertical layout when resized.
* We now use ``git diff --submodule`` for submodules
  (used when git >= 1.6.6).
* The context menu for modified submodules includes an option
  to launch `git cola`.

  http://github.com/git-cola/git-cola/issues/17

* Prefer ``$VISUAL`` over ``$EDITOR`` when both are defined.
  These are used to set a default editor in lieu of `core.editor`
  configuration.
* Force the editor to be ``gvim`` when we see ``vim``.
  This prevents us from launching an editor in the (typically
  unattached) parent terminal and creating zombie editors
  that cannot be easily killed.
* Selections are remembered and restored across updates.
  This makes the `partial-staging` workflow easier since the
  diff view will show the updated diff after staging.
* Show the path to the current repository in a tooltip
  over the commit message editor.

  http://github.com/git-cola/git-cola/issues/45

* Log internal ``git`` commands when ``GIT_COLA_TRACE`` is defined.

  http://github.com/git-cola/git-cola/issues/39

Fixes
-----
* Improved backwards compatibility for Python 2.4.
* `Review mode` can now review the current branch; it no longer
  requires you to checkout the branch into which the reviewed
  branch will be merged.
* Guard against `color.ui = always` configuration when using
  `git log` by passing ``--no-color``.
* ``yes`` and ``no`` are now supported as valid booleans
  by the `git config` parser.
* Better defaults are used for `fetch`, `push`, and `pull`..

  http://github.com/git-cola/git-cola/issues/43

Packaging
---------
* Removed colon (`:`) from the applilcation name on Windows

  http://github.com/git-cola/git-cola/issues/41

* Fixed bugs with the Windows installer

  http://github.com/git-cola/git-cola/issues/40

* Added a more standard i18n infrastructure.  The install
  tree now has the common ``share/locale/$lang/LC_MESSAGES/git-cola.mo``
  layout in use by several projects.

* Started trying to accomodate Mac OSX 10.6 (Snow Leopard)
  in the ``darwin/`` build scripts but our tester is yet to
  report success building a `.app` bundle.

* Replaced use of ``perl`` in Sphinx/documentation Makefile
  with more-portable ``sed`` constructs.  Thanks to
  Stefan Naewe for discovering the portability issues and
  providing msysgit-friendly patches.

git-cola v1.4.1.2
=================
Usability, bells and whistles
-----------------------------
* It is now possible to checkout from the index as well
  as from `HEAD`.  This corresponds to the
  `Removed Unstaged Changes` action in the `Repository Status` tool.
* The `remote` dialogs (fetch, push, pull) are now slightly
  larger by default.
* Bookmarks can be selected when `git cola` is run outside of a git repository.
* Added more user documentation.  We now include many links to
  external git resources.
* Added `git dag` to the available tools.
  `git dag` is a node-based DAG history browser.
  It doesn't do much yet, but it's been merged so that we can start
  building and improving upon it.

Fixes
-----
* Fixed a missing ``import`` when showing `right-click` actions
  for unmerged files in the `Repository Status` tool.
* ``git update-index --refresh`` is no longer run everytime
  ``git cola version`` is run.
* Don't try to watch non-existant directories when using `inotify`.
* Use ``git rev-parse --symbolic-full-name`` plumbing to find
  the name of the current branch.

Packaging
---------
* The ``Makefile`` will now conditionally include a ``config.mak``
  file located at the root of the project.  This allows for user
  customizations such as changes to the `prefix` variable
  to be stored in a file so that custom settings do not need to
  be specified every time on the command-line.
* The build scripts no longer require a ``.git`` directory to
  generate the ``builtin_version.py`` module.  The release tarballs
  now include a ``version`` file at the root of the project which
  is used in lieu of having the git repository available.
  This allows for ``make clean && make`` to function outside of
  a git repository.
* Added maintainer's ``make dist`` target to the ``Makefile``.
* The built-in `simplejson` and `jsonpickle` libraries can be
  excluded from ``make install`` by specifying the ``standalone=true``
  `make` variable.  For example, ``make standalone=true install``.
  This corresponds to the ``--standalone`` option to ``setup.py``.


git-cola v1.4.1.1
=================
Usability, bells and whistles
-----------------------------
* We now use patience diff by default when it is available via
  `git diff --patience`.
* Allow closing the `cola classic` tool with `Ctrl+W`.

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
`git cola`'s github issues backlog.  On the developer
front, further work was done towards modularizing the code base.

Usability, bells and whistles
-----------------------------
* Dragging and dropping patches invokes `git am`

  http://github.com/git-cola/git-cola/issues/3

* A dialog to allow opening or cloning a repository
  is presented when `git cola` is launched outside of a git repository.

  http://github.com/git-cola/git-cola/issues/closed/#issue/22

* Warn when `push` is used to create a new branch

  http://github.com/git-cola/git-cola/issues/35

* Optimized startup time by removing several calls to `git`.


Portability
-----------
* `git cola` is once again compatible with PyQt 4.3.x.

Developer
---------
* `cola.gitcmds` was added to factor out git command-line utilities
* `cola.gitcfg` was added for interacting with `git config`
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

  http://github.com/git-cola/git-cola/issues/closed/#issue/31

* Fix a bug when initializing fonts on Windows

  http://github.com/git-cola/git-cola/issues/closed/#issue/32


git-cola v1.4.0.1
=================
Fixes
-----
* Keep entries in sorted order in the `cola classic` tool
* Fix staging untracked files

  http://github.com/git-cola/git-cola/issues/closed/#issue/27

* Fix the `show` command in the Stash dialog

  http://github.com/git-cola/git-cola/issues/closed/#issue/29

* Fix a typo when loading merge commit messages

  http://github.com/git-cola/git-cola/issues/closed/#issue/30


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
  This is in preparation for `git 1.7.0` where unconfigured `git push`
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
* `git difftool` became an official git command in `git 1.6.3`.
* `git difftool` learned `--no-prompt` / `-y` and a corresponding
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
* Added support for Kompare in `git difftool`
* Added a separate configuration namespace for `git difftool`
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
* `NOTE` -- `cola.showoutput` was removed with the GUI rewrite in 1.4.0.

Developer
---------
* Improved nose unittest usage

Packaging
---------
* Added a Windows/msysGit installer
* Included private versions of `simplejson` and `jsonpickle`
  for ease of installation and development
