========
Releases
========

Latest Release
==============

:ref:`v2.9.1 <v2.9.1>` is the latest stable release.

Development version
===================

Clone the git-cola repo to get the latest development version:

``git clone git://github.com/git-cola/git-cola.git``

.. _v2.9.1:

Fixes
-----
* The "Open Recent" menu was updated to new bookmarks format.

  https://github.com/git-cola/git-cola/issues/628

.. _v2.9:

git-cola v2.9
=============

Usability, bells and whistles
-----------------------------
* New Polish translation thanks to Łukasz Wojniłowicz

  https://github.com/git-cola/git-cola/pull/598

* The `Bypass Commit Hooks` feature now disables itself automatically
  when a new commit is created.  The new behavior turns the option into a
  single-use flag, which helps prevent users from accidentally leaving it
  active longer than intended.

  https://github.com/git-cola/git-cola/pull/595

* `git dag` learned to launch an external diff viewer on selected commits.
  The standard `Ctrl+D` shortcut can be used to view diffs.

  https://github.com/git-cola/git-cola/issues/468

* `git dag` learned to launch directory diffs via `git difftool --dir-diff`.
  The `Ctrl+Shift+D` shortcut launches difftool in directory-diff mode.

  https://github.com/git-cola/git-cola/issues/468

* Items in the "Favorites" list can now be renamed, which makes it
  easier to differentiate between several checkouts of the same repository.

  https://github.com/git-cola/git-cola/issues/599

  https://github.com/git-cola/git-cola/pull/601

* The startup screen now includes a logo and `git cola` version information.

  https://github.com/git-cola/git-cola/issues/526

* The `About` page was revamped to contain multiple tabs.  A new tab was added
  that provides details about `git cola`''s dependencies.  New tabs were also
  added for giving credit to `git cola`'s authors and translators.

* The `About` page can now be accessed via `git cola about`.

* The "Fast-forward only" and "No fast-forward" options supported by
  `git pull` are now accessible via `git cola pull`.

* Doing a forced push no longer requires selecting the remote branch.

  https://github.com/git-cola/git-cola/pull/618

* `git cola push` now has an option to suppress the prompt that is shown
  when pushing would create new remote branches.

  https://github.com/git-cola/git-cola/issues/605

* `git dag` now shows commit messages in a more readable color.

  https://github.com/git-cola/git-cola/issues/574

* `git cola browse` and the `status` widget learned to launch the OS-specified
  default action for a file.  When used on directories via `git cola browse`,
  or when "Open Parent Directory" is used on files, the OS-specified
  file browser will typically be used.

* `git cola browse` and the `status` widget learned to launch terminals.

Fixes
-----
* `git cola browse` was not updating when expanding items.

  https://github.com/git-cola/git-cola/issues/588

* Typofixes in comments, naming, and strings have been applied.

  https://github.com/git-cola/git-cola/pull/593

* The inotify and win32 filesystem monitoring no longer refreshes
  when updates are made to ignored files.

  https://github.com/git-cola/git-cola/issues/517

  https://github.com/git-cola/git-cola/issues/516

* The `Refresh` button on the actions panel no longer raises an
  exception when using PyQt5.

  https://github.com/git-cola/git-cola/issues/604

* Fixed a typo in the inotify backend that is triggered when files are removed.

  https://github.com/git-cola/git-cola/issues/607

* Fixed a typo when recovering from a failed attempt to open a repository.

  https://github.com/git-cola/git-cola/issues/606

* `git dag` now properly updates itself when launched from the menubar.

  https://github.com/git-cola/git-cola/pull/613

* If git-cola is invoked on Windows using `start pythonw git-cola`,
  a console window will briefly flash on the screen each time
  `git cola` invokes `git`.  The console window is now suppressed.

* We now avoid some problematic Popen flags on Windows which were
  breaking the `git rebase` feature on Windows.

* The `Save` button in `git dag`'s "Grab File..." feature now properly
  prompts for a filename when saving files.

  https://github.com/git-cola/git-cola/pull/617

Development
-----------
* The `qtpy` symlink in the source tree has been removed to allow for easier
  development on Windows.

  https://github.com/git-cola/git-cola/issues/626

.. _v2.8:

git-cola v2.8
=============

Usability, bells and whistles
-----------------------------
* `git cola push` learned to configure upstream branches.

  https://github.com/git-cola/git-cola/issues/563

Fixes
-----
* The diffstat view is now properly updated when notifications are
  received via inotify filesystem monitoring.

  https://github.com/git-cola/git-cola/issues/577

* Python3 with PyQt5 had a bug that prevented `git cola` from starting.

  https://github.com/git-cola/git-cola/pull/589

.. _v2.7:

git-cola v2.7
=============

Fixes
-----

* When repositories stored in non-ASCII, UTF-8-encoded filesystem paths
  were operated upon with `LC_ALL=C` set in the environment, unicode errors
  would occur when using `python2`.  `git cola` was made more robust and will
  now operate correctly within this environment.

  https://github.com/git-cola/git-cola/issues/581

* Support for the `GIT_WORK_TREE` environment variable was fixed.

  https://github.com/git-cola/git-cola/pull/582

Development
-----------

* The `unittest.mock` module is now used instead of the original `mock` module
  when running the `git cola` test suite using Python3.

  https://github.com/git-cola/git-cola/issues/569

Packaging
---------

* `git cola` is now compatible with *PyQt5*, *PyQt4*, and *Pyside*.
  `git cola` previously supported *PyQt4* only, but will now use whichever
  library is available.  Users are not required to upgrade at this time,
  but *PyQt5* support can be enabled anytime by making its python
  modules available.

  https://github.com/git-cola/git-cola/issues/232

  *NOTE*: We do not yet recommend using *PyQt5* because there are known
  exit-on-segfault bugs in *Qt5* that have not yet been addressed.
  `git cola` is sensitive to this bug and is known to crash on exit
  when using `git dag` or the interactive rebase feature on *PyQt5*.

  https://bugreports.qt.io/browse/QTBUG-52988

  *PyQt4* is stable and there are no known issues when using it so
  we recommend using it until the Qt5 bugs have been resolved.

* `git cola` now depends on *QtPy* and includes a bundled copy of the
  `qtpy` library.  If you are packaging `git cola` and would prefer to use
  `qtpy` from your distribution instead of the built-in version then use
  `make NO_VENDOR_LIBS=1` when building `git cola`.  This will prevent
  vendored libraries from being installed.

.. _v2.6:

git-cola v2.6
=============

Usability, bells and whistles
-----------------------------

* A new "Reset" sub-menu provides access to running "git reset --mixed"
  when resetting branch heads and "git reset  --merge" when resetting
  worktrees.

  https://github.com/git-cola/git-cola/issues/542

* `git cola` now supports linked worktrees, i.e. worktrees created by
  `git worktree`.

  https://github.com/git-cola/git-cola/issues/554

Fixes
-----

* Diff highlighting is now robust to the user having
  diff.supressBlankEmpty=true in their git config.

  https://github.com/git-cola/git-cola/issues/541

* The filesystem monitor now properly handles repositories that use
  `.git`-files, e.g. when using submodules.

  https://github.com/git-cola/git-cola/issues/545

  https://github.com/git-cola/git-cola/pulls/546

* Per-repository git configuration is now properly detected when launching
  `git cola` from an application launcher.

  https://github.com/git-cola/git-cola/issues/548

* `git cola` now cleans up after itself immediately to avoid leaving behind
  empty `/tmp/git-cola-XXXXXX` directories when the user uses `Ctrl+C`
  to quit the app.

  https://github.com/git-cola/git-cola/issues/566

Packaging
---------

* It is now possible to install `git cola` to and from utf8-encoded filesystem
  paths.  Previously, Python's stdlib would throw an encoding error during
  installation.  We workaround the stdlib by forcing python2 to use utf-8,
  thus fixing assumptions in the stdlib library code.

  https://github.com/git-cola/git-cola/issues/551

.. _v2.5:

git-cola v2.5
=============

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
  a Git repository.  When unset, or when set to a bogus value, `git cola`
  will prompt for a repository, as it previously did.

  https://github.com/git-cola/git-cola/issues/513

* `git cola`'s Russian and Spanish translations were improved
  thanks to Vaiz and Zeioth.

  https://github.com/git-cola/git-cola/pull/514

  https://github.com/git-cola/git-cola/pull/515

  https://github.com/git-cola/git-cola/pull/523

* `git cola` was translated to Turkish thanks to Barış ÇELİK.

  https://github.com/git-cola/git-cola/pull/520

* The status view now supports launching `git gui blame`.  It can be
  configured to use a different command by setting `cola.blameviewer`.

  https://github.com/git-cola/git-cola/pull/521

* `git dag` now allows selecting non-contiguous ranges in the log widget.

  https://github.com/git-cola/git-cola/issues/468

* Any font can now be chosen for the diff editor, not just monospace fonts.

  https://github.com/git-cola/git-cola/issues/525

Fixes
-----

* `xfce4-terminal` and `gnome-terminal` are now supported when launching
  `git mergetool` to resolve merges.  These terminals require that the command
  to execute is shell-quoted and passed as a single string argument to `-e`
  rather than as additional command line arguments.

  https://github.com/git-cola/git-cola/issues/524

* Fixed a unicode problem when formatting the error message that is shown
  when `gitk` is not installed.  We now handle unicode data in tracebacks
  generated by python itself.

  https://github.com/git-cola/git-cola/issues/528

* The `New repository` feature was fixed.

  https://github.com/git-cola/git-cola/pull/533

* We now use omit the extended description when creating "fixup!" commits,
  for consistency with the Git CLI.  We now include only the one-line summary
  in the final commit message.

  https://github.com/git-cola/git-cola/issues/522

.. _v2.4:

git-cola v2.4
=============

Usability, bells and whistles
-----------------------------

* The user interface is now HiDPI-capable.  git-cola now uses SVG
  icons, and its interface can be scaled by setting the `GIT_COLA_SCALE`
  environment variable.

* `git dag` now supports the standard editor, difftool, and history hotkeys.
  It is now possible to invoke these actions from file widget's context
  menu and through the standard hotkeys.

  https://github.com/git-cola/git-cola/pull/473

* The `Status` tool also learned about the history hotkey.
  Additionally, the `Alt-{j,k}` aliases are also supported in the `Status`
  tool for consistency with the other tools where the non-Alt hotkeys are not
  available.

  https://github.com/git-cola/git-cola/pull/488

* The `File Browser` tool now has better default column sizes,
  and remembers its window size and placement.

* The `File Browser` now supports the refresh hotkey, and has better
  behavior when refreshing.  The selection is now retained, and new and
  removed files are found when refreshing.

* A new `git-cola-completion.bash` completion script is provided in the
  `contrib/` directory.  It must be used alongside Git's completion script.
  Source it from your `~/.bashrc` (or `~/.zshrc`, etc) after sourcing
  the `git-completion.bash` script and you will have command-line completion
  support for the `git cola` and `git dag` sub-commands.

* The "checkout" dialog now offers completion for remote branches and other
  git refs.  This makes it easier to checkout remote branches in a detached
  head state.  Additionally, the checkout dialog also offers completion for
  remote branches that have not yet been checked out, which makes it easier to
  create a local tracking branch by just completing for that potential name.

  https://github.com/git-cola/git-cola/issues/390

* The "create branch" and "create tag" dialogs now save and restore their
  window settings.

* The "status" widget can now be configured to use a bold font with a darker
  background for the header items.

  https://github.com/git-cola/git-cola/pull/506

* The "status" widget now remembers its horizontol scrollbar position across
  updates.  This is helpful when working on projects with long paths.

  https://github.com/git-cola/git-cola/issues/494

Fixes
-----

* When using *Git for Windows*, a `git` window would appear
  when running *Windows 8*.  We now pass additional flags to
  `subprocess.Popen` to prevent a `git` window from appearing.

  https://github.com/git-cola/git-cola/issues/477

  https://github.com/git-cola/git-cola/pull/486

* Launching difftool with `.PY` in `$PATHEXT` on Windows was fixed.

  https://github.com/git-cola/git-cola/issues/492

* Creating a local branch tracking a remote branch that contains
  slashes in its name is now properly handled.

  https://github.com/git-cola/git-cola/issues/496

* The "Browse Other Branch" feature was broken by Python3, and is now fixed.

  https://github.com/git-cola/git-cola/issues/501

* We now avoid `long` for better Python3 compatibility.

  https://github.com/git-cola/git-cola/issues/502

* We now use Git's default merge message when merging branches.

  https://github.com/git-cola/git-cola/issues/508

* Miscellaneous fixes

  https://github.com/git-cola/git-cola/pull/485

Packaging
---------

* git-cola's documentation no longer uses an intersphinx link mapping
  to docs.python.org.  This fixes warnings when building rpms using koji,
  where network access is prevented.

  https://bugzilla.redhat.com/show_bug.cgi?id=1231812

.. _v2.3:

git-cola v2.3
=============

Usability, bells and whistles
-----------------------------

* The Interactive Rebase feature now works on Windows!

  https://github.com/git-cola/git-cola/issues/463

* The `diff` editor now understands vim-style `hjkl` navigation hotkeys.

  https://github.com/git-cola/git-cola/issues/476

* `Alt-{j,k}` navigation hotkeys were added to allow changing to the
  next/previous file from the diff and commit editors.

* The `Rename branch` menu action is now disabled in empty repositories.

  https://github.com/git-cola/git-cola/pull/475

  https://github.com/git-cola/git-cola/issues/459

* `git cola` now checks unmerged files for conflict markers before
  staging them.  This feature can be disabled in the preferences.

  https://github.com/git-cola/git-cola/issues/464

* `git dag` now remembers which commits were selected when refreshing
  so that it can restore the selection afterwards.

  https://github.com/git-cola/git-cola/issues/480

* "Launch Editor", "Launch Difftool", "Stage/Unstage",
  and "Move Up/Down" hotkeys now work when the commit message
  editor has focus.

  https://github.com/git-cola/git-cola/issues/453

* The diff editor now supports the `Ctrl+u` hotkey for reverting
  diff hunks and selected lines.

* The `core.commentChar` Git configuration value is now honored.
  Commit messages and rebase instruction sheets will now use
  the configured character for comments.  This allows having
  commit messages that start with `#` when `core.commentChar`
  is configured to its non-default value.

  https://github.com/git-cola/git-cola/issues/446

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

* The copy/paste clipboard now persists after `git cola` exits.

  https://github.com/git-cola/git-cola/issues/484

.. _v2.2.1:

git-cola v2.2.1
===============

Fixes
-----
* Fixed the "Sign off" feature in the commit message editor.

.. _v2.2:

git-cola v2.2
=============

Usability, bells and whistles
-----------------------------
* Double-click will now choose a commit in the "Select commit" dialog.

* `git cola` has a feature that reads `.git/MERGE_MSG` and friends for the
  commit message when a merge is in-progress.  Upon refresh, `git cola` will
  now detect when a merge has completed and reset the commit message back to
  its previous state.  It is only reset if the editor contains a message
  that was read from the file and has not been manually edited by the user.

* The commit message editor's context menu now has a "Clear..." action for
  clearing the message across both the summary and description fields.

* Traditional Chinese (Taiwan) translation updates.

* The system theme's icons are now used wherever possible.

  https://github.com/git-cola/git-cola/pull/458

Fixes
-----
* The stash viewer now uses ``git show --no-ext-diff`` to avoid running
  user-configured diff tools.

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

* The interactive rebase feature was not always setting `$GIT_EDITOR`
  to the value of `gui.editor`, thus there could be instances where rebase
  will seem to not stop, or hang, when performing "reword" actions.

  We now set the `$GIT_EDITOR` environment variable when performing the
  "Continue", "Skip", and "Edit Todo" rebase actions so that the correct
  editor is used during the rebase.

  https://github.com/git-cola/git-cola/issues/445

Packaging
---------
* `git cola` moved from a 3-part version number to a simpler 2-part "vX.Y"
  version number.  Most of our releases tend to contain new features.

.. _v2.1.2:

git-cola v2.1.2
===============

Usability, bells and whistles
-----------------------------
* Updated zh_TW translations.

* `git cola rebase` now defaults to `@{upstream}`, and generally uses the same
  CLI syntax as `git rebase`.

* The commit message editor now allows you to bypass commit hooks by selecting
  the "Bypass Commit Hooks" option.  This is equivalent to passing the
  `--no-verify` option to `git commit`.

  https://github.com/git-cola/git-cola/issues/357

* We now prevent the "Delete Files" action from creating a dialog that does
  not fit on screen.

  https://github.com/git-cola/git-cola/issues/378

* `git xbase` learned to edit rebase instruction sheets that contain
  `exec` commands.

* The diff colors are now configurable.  `cola.color.{text,add,remove,header}`
  can now be set with 6-digit hexadecimal colors.
  See the `git cola manual <https://git-cola.readthedocs.io/en/latest/git-cola.html#configuration-variables>_`
  for more details.

* Improved hotkey documentation.

Fixes
-----
* `git cola` will now allow starting an interactive rebase with a dirty
  worktree when `rebase.autostash` is set.

  https://github.com/git-cola/git-cola/issues/360

.. _v2.1.1:

git-cola v2.1.1
===============

Usability, bells and whistles
-----------------------------
* A new "Find files" widget was added, and can be activated by
  using the `Ctrl+t` or `t` hotkeys.

* A new `git cola find` sub-command was added for finding files.

* `git cola` now remembers the text cursor's position when staging
  interactively with the keyboard.  This makes it easier to use the keyboard
  arrows to select and stage lines.

* The completion widgets will now select the top completion item
  when `Enter` or `Return` are pressed.

* You can now refresh using `F5` in addition to the existing `Ctrl+R` hotkey.

Fixes
-----
* `git cola` now passes `--no-abbrev-commit` to `git log` to override
  having `log.abbrevCommit = true` set in `.gitconfig`.

.. _v2.1.0:

git-cola v2.1.0
===============
Usability, bells and whistles
-----------------------------
* `git dag` now forwards all unknown arguments along to `git log`.

  https://github.com/git-cola/git-cola/issues/389

* Line-by-line interactive staging was made more robust.

  https://github.com/git-cola/git-cola/pull/399

* "Bookmarks" was renamed to "Favorites".

  https://github.com/git-cola/git-cola/issues/392

* Untracked files are now displayed using a unique icon.

  https://github.com/git-cola/git-cola/pull/388

Fixes
-----
* `git dag` was triggering a traceback on Fedora when parsing Git logs.

  https://bugzilla.redhat.com/show_bug.cgi?id=1181686

* inotify expects unicode paths on Python3.

  https://github.com/git-cola/git-cola/pull/393

* Untracked files are now assumed to be utf-8 encoded.

  https://github.com/git-cola/git-cola/issues/401

.. _v2.0.8:

git-cola v2.0.8
===============
Usability, bells and whistles
-----------------------------
* `git cola` can now create GPG-signed commits and merges.

  https://github.com/git-cola/git-cola/issues/149

  See the documentation for details about setting up a GPG agent.

* The status widget learned to copy relative paths when `Ctrl+x` is pressed.

  https://github.com/git-cola/git-cola/issues/358

* Custom GUI actions can now define their own keyboard shortcuts by
  setting `guitool.$name.shortcut` to a string understood by Qt's
  `QAction::setShortcut()` API, e.g. `Alt+X`.

  See http://qt-project.org/doc/qt-4.8/qkeysequence.html#QKeySequence-2
  for more details about the supported values.

* `git cola` learned to rename branches.

  https://github.com/git-cola/git-cola/pull/364

  https://github.com/git-cola/git-cola/issues/278

* `git dag` now has a "Show history" context menu which can be used to filter
  history using the selected paths.

Fixes
-----
* `sphinxtogithub.py` was fixed for Python3.

  https://github.com/git-cola/git-cola/pull/353

* The commit that changed how we read remotes from `git remote`
  to parsing `git config` was reverted since it created problems
  for some users.

* Fixed a crash when using the `rebase edit` feature.

  https://github.com/git-cola/git-cola/issues/351

* Better drag-and-drop behavior when dropping into gnome-terminal.

  https://github.com/git-cola/git-cola/issues/373

Packaging
---------
* The `git-cola-folder-handler.desktop` file handler was fixed
  to pass validation by `desktop-file-validate`.

  https://github.com/git-cola/git-cola/issues/356

* The `git.svg` icon was renamed to `git-cola.svg`, and `git cola` was taught
  to prefer icons from the desktop theme when available.

.. _v2.0.7:

git-cola v2.0.7
===============
Usability, bells and whistles
-----------------------------
* New hotkey: `Ctrl+Shift+M` merges branches.

* New hotkey: `Ctrl+R` refreshes the DAG viewer.

  https://github.com/git-cola/git-cola/issues/347

Fixes
-----
* We now use `git config` to parse the list of remotes
  instead of parsing the output of `git remote`, which
  is a Git porcelain and should not be used by scripts.

* Avoid "C++ object has been deleted" errors from PyQt4.

  https://github.com/git-cola/git-cola/issues/346

Packaging
---------
* The `make install` target now uses `install` instead of `cp`.

.. _v2.0.6:

git-cola v2.0.6
===============
Usability, bells and whistles
-----------------------------
* Updated Brazillian Portuguese translation.

* The status and browse widgets now allow drag-and-drop into
  external applications.

  https://github.com/git-cola/git-cola/issues/335

* We now show a progress bar when cloning repositories.

  https://github.com/git-cola/git-cola/issues/312

* The bookmarks widget was simplified to not need a
  separate dialog.

  https://github.com/git-cola/git-cola/issues/289

* Updated Traditional Chinese translation.

* We now display a warning when trying to rebase with uncommitted changes.

  https://github.com/git-cola/git-cola/issues/338

* The status widget learned to filter paths.
  `Ctrl+Shift+S` toggles the filter widget.

  https://github.com/git-cola/git-cola/issues/337

  https://github.com/git-cola/git-cola/pull/339

* The status widget learned to move files to the trash
  when the `send2trash <https://github.com/hsoft/send2trash>`_
  module is installed.

  https://github.com/git-cola/git-cola/issues/341

* "Recent repositories" is now a dedicated widget.

  https://github.com/git-cola/git-cola/issues/342

* New Spanish translation thanks to Pilar Molina Lopez.

  https://github.com/git-cola/git-cola/pull/344

Fixes
-----
* Newly added remotes are now properly seen by the fetch/push/pull dialogs.

  https://github.com/git-cola/git-cola/issues/343

.. _v2.0.5:

git-cola v2.0.5
===============
Usability, bells and whistles
-----------------------------
* New Brazillian Portuguese translation thanks to Vitor Lobo.

* New Indonesian translation thanks to Samsul Ma'arif.

* Updated Simplified Chinese translation thanks to Zhang Han.

* `Ctrl+Backspace` is now a hotkey for "delete untracked files" in
  the status widget.

* Fetch/Push/Pull dialogs now use the configured remote of the current
  branch by default.

  https://github.com/git-cola/git-cola/pull/324

Fixes
-----
* We now use `os.getcwd()` on Python3.

  https://github.com/git-cola/git-cola/pull/316

  https://github.com/git-cola/git-cola/pull/326

* The `Ctrl+P` hotkey was overloaded to both "push" and "cherry-pick",
  so "cherry-pick" was moved to `Ctrl+Shift+C`.

* Custom GUI tools with mixed-case names are now properly supported.

* "Diff Region" is now referred to as "Diff Hunk" for consistency
  with common terminology from diff/patch tools.

  https://github.com/git-cola/git-cola/issues/328

* git-cola's test suite is now portable to MS Windows.

  https://github.com/git-cola/git-cola/pull/332

.. _v2.0.4:

git-cola v2.0.4
===============
Usability, bells and whistles
-----------------------------
* We now handle the case when inotify `add_watch()` fails
  and display instructions on how to increase the number of watches.

  https://github.com/git-cola/git-cola/issues/263

* New and improved zh_TW localization thanks to Ｖ字龍(Vdragon).

  https://github.com/git-cola/git-cola/pull/265

  https://github.com/git-cola/git-cola/pull/267

  https://github.com/git-cola/git-cola/pull/268

  https://github.com/git-cola/git-cola/issues/269

  https://github.com/git-cola/git-cola/pull/270

  https://github.com/git-cola/git-cola/pull/271

  https://github.com/git-cola/git-cola/pull/272

* New hotkeys: `Ctrl+F` for fetch, `Ctrl+P` for push,
  and `Ctrl+Shift+P` for pull.

* The bookmarks widget's context menu actions were made clearer.

  https://github.com/git-cola/git-cola/issues/281

* The term "Staging Area" is used consistently in the UI
  to allow for better localization.

  https://github.com/git-cola/git-cola/issues/283

* The "Section" term is now referred to as "Diff Region"
  in the UI.

  https://github.com/git-cola/git-cola/issues/297

* The localization documentation related to the LANGUAGE
  environment variable was improved.

  https://github.com/git-cola/git-cola/pull/293

* The "Actions" panel now contains tooltips for each button
  in case the button labels gets truncated by Qt.

  https://github.com/git-cola/git-cola/issues/292

* Custom `git config`-defined actions can now be run in the
  background by setting `guitool.<name>.background` to `true`.

Fixes
-----
* We now use bold fonts instead of SmallCaps to avoid
  artifacts on several configurations.

* We now pickup `user.email`, `cola.tabwidth`, and similar settings
  when defined in /etc/gitconfig.

  https://github.com/git-cola/git-cola/issues/259

* Better support for unicode paths when using inotify.

  https://bugzilla.redhat.com/show_bug.cgi?id=1104181

* Unicode fixes for non-ascii locales.

  https://github.com/git-cola/git-cola/issues/266

  https://github.com/git-cola/git-cola/issues/273

  https://github.com/git-cola/git-cola/issues/276

  https://github.com/git-cola/git-cola/issues/282

  https://github.com/git-cola/git-cola/issues/298

  https://github.com/git-cola/git-cola/issues/302

  https://github.com/git-cola/git-cola/issues/303

  https://github.com/git-cola/git-cola/issues/305

* Viewing history from the file browser was fixed for Python3.

  https://github.com/git-cola/git-cola/issues/274

* setup.py was fixed to install the `*.rst` documentation.

  https://github.com/git-cola/git-cola/issues/279

* Patch export was fixed for Python3.

  https://github.com/git-cola/git-cola/issues/290

* Fixed adding a bookmark with trailing slashes.

  https://github.com/git-cola/git-cola/pull/295

* The default `git dag` layout is now setup so that its widgets
  can be freely resized on Linux.

  https://github.com/git-cola/git-cola/issues/299

* Invalid tag names are now reported when creating tags.

  https://github.com/git-cola/git-cola/pull/296

.. _v2.0.3:

git-cola v2.0.3
===============
Usability, bells and whistles
-----------------------------
* `git cola` no longer prompts after successfully creating a new branch.

  https://github.com/git-cola/git-cola/pull/251

* Hitting enter on simple dialogs now accepts them.

  https://github.com/git-cola/git-cola/pull/255

Fixes
-----
* `git dag` no longer relies on `sys.maxint`, which is
  not available in Python3.

  https://github.com/git-cola/git-cola/issues/249

* Python3-related fixes.

  https://github.com/git-cola/git-cola/pull/254

* Python3-on-Windows-related fixes.

  https://github.com/git-cola/git-cola/pull/250

  https://github.com/git-cola/git-cola/pull/252

  https://github.com/git-cola/git-cola/pull/253

* Switching repositories using the bookmarks widget was not
  refreshing the inotify watcher.

  https://github.com/git-cola/git-cola/pull/256

* Special commit messages trailers (e.g. "Acked-by:") are now special-cased to
  fix word wrapping lines that start with "foo:".

  https://github.com/git-cola/git-cola/issues/257

* `git dag` sometimes left behind selection artifacts.
  We now refresh the view to avoid them.

  https://github.com/git-cola/git-cola/issues/204

.. _v2.0.2:

git-cola v2.0.2
===============
Usability, bells and whistles
-----------------------------
* Better inotify support for file creation and deletion.

  https://github.com/git-cola/git-cola/issues/240

* `git cola` now supports the X11 Session Management Protocol
  and remembers its state across logout/reboot.

  https://github.com/git-cola/git-cola/issues/164

* `git cola` has a new icon.

  https://github.com/git-cola/git-cola/issues/190

Packaging
---------
* Building the documentation no longer requires `asciidoc`.
  We now use `Sphinx <http://sphinx-doc.org/>`_ for building
  html documentation and man pages.

Fixes
-----
* Reworked the git-dag gravatar icon code to avoid a unicode
  error in Python 2.

* Commit message line-wrapping was made to better match the GUI editor.

  https://github.com/git-cola/git-cola/issues/242

* Better support for Python3 on Windows

  https://github.com/git-cola/git-cola/issues/246

Packaging
---------
* git-cola no longer depends on Asciidoc for building its documentation
  and man-pages.  We now depend on [Sphinx](http://sphinx-doc.org/) only.

.. _v2.0.1:

git-cola v2.0.1
===============
Usability, bells and whistles
-----------------------------
* Some context menu actions are now hidden when selected
  files do not exist.

  https://github.com/git-cola/git-cola/issues/238

Fixes
-----
* The build-git-cola.sh contrib script was improved.

  https://github.com/git-cola/git-cola/pull/235

* Non-ascii worktrees work properly again.

  https://github.com/git-cola/git-cola/issues/234

* The browser now guards itself against missing files.

  https://bugzilla.redhat.com/show_bug.cgi?id=1071378

* Saving widget state now works under Python3.

  https://github.com/git-cola/git-cola/pull/236

.. _v2.0.0:

git-cola v2.0.0
===============
Portability
-----------
* git-cola now runs on Python 3 thanks to Virgil Dupras.

  https://github.com/git-cola/git-cola/pull/233

* Python 2.6, 2.7, and 3.2+ are now supported.
  Python 2.5 is no longer supported.

Fixes
-----
* i18n test fixes thanks to Virgil Dupras.

  https://github.com/git-cola/git-cola/pull/231

* git-cola.app build fixes thanks to Maicon D. Filippsen.

  https://github.com/git-cola/git-cola/pull/230

* Lots of pylint improvements thanks to Alex Chernetz.

  https://github.com/git-cola/git-cola/pull/229

.. _v1.9.4:

git-cola v1.9.4
===============
Usability, bells and whistles
-----------------------------
* The new `Bookmarks` tool makes it really easy to switch between repositories.

* There is now a dedicated dialog for applying patches.
  See the ``File -> Apply Patches`` menu item.

  https://github.com/git-cola/git-cola/issues/215

* A new `git cola am` sub-command was added for applying patches.

Fixes
-----
* Fixed a typo that caused inotify events to be silently ignored.

* Fixed the sys.path setup for Mac OS X (Homebrew).

  https://github.com/git-cola/git-cola/issues/221

* Lots of pylint fixes thanks to Alex Chernetz.

.. _v1.9.3:

git-cola v1.9.3
===============
Usability, bells and whistles
-----------------------------
* `git cola --amend` now starts the editor in `amend` mode.

  https://github.com/git-cola/git-cola/issues/187

* Multiple lines of text can now be pasted into the `summary` field.
  All text beyond the first newline will be automatically moved to the
  `extended description` field.

  https://github.com/git-cola/git-cola/issues/212

Fixes
-----
* Stray whitespace in `.git` files is now ignored.

  https://github.com/git-cola/git-cola/issues/213

* Fix "known incorrect sRGB profile" in `staged-item.png`.

  http://comments.gmane.org/gmane.linux.gentoo.devel/85066

.. _v1.9.2:

git-cola v1.9.2
===============
Fixes
-----
* Fix a traceback when `git push` fails.

  https://bugzilla.redhat.com/show_bug.cgi?id=1034778

Packaging
---------
* Most of the git-cola sub-packages have been removed.
  The only remaining packages are `cola`, `cola.models`,
  and `cola.widgets`.

* The translation file for Simplified Chinese was renamed
  to `zh_CN.po`.

  https://github.com/git-cola/git-cola/issues/209

.. _v1.9.1:

git-cola v1.9.1
===============
Packaging
---------
* `git cola version --brief` now prints the brief version number.

Fixes
-----
* Resurrected the "make dist" target, for those that prefer to create
  their own tarballs.

* Fixed the typo that broke the preferences dialog.

.. _v1.9.0:

git-cola v1.9.0
===============
Usability, bells and whistles
-----------------------------
* We now ship a full-featured interactive `git rebase` editor.
  The rebase todo file is edited using the `git xbase` script which
  is provided at `$prefix/share/git-cola/bin/git-xbase`.
  This script can be used standalone by setting the `$GIT_SEQUENCE_EDITOR`
  before running `git rebase --interactive`.

  https://github.com/git-cola/git-cola/issues/1

* Fixup commit messages can now be loaded from the commit message editor.

* Tool widgets can be locked in place by using the "Tools/Lock Layout"
  menu action.

  https://github.com/git-cola/git-cola/issues/202

* You can now push to several remotes simultaneously by selecting
  multiple remotes in the "Push" dialog.

  https://github.com/git-cola/git-cola/issues/148

* The `grep` tool learned to search using three different modes:
  basic regular expressions (default), extended regular expressions,
  and fixed strings.

Packaging
---------
* `git cola` now depends on the `argparse` Python module.
  This module is part of the stdlib in Python 2.7 and must
  be installed separately when using Python 2.6 and below.

Fixes
-----
* Support unicode in the output from `fetch`, `push`, and `pull`.

.. _v1.8.5:

git-cola v1.8.5
===============
Usability, bells and whistles
-----------------------------
* We now detect when the editor or history browser are misconfigured.

  https://github.com/git-cola/git-cola/issues/197

  https://bugzilla.redhat.com/show_bug.cgi?id=886826

* Display of untracked files can be disabled from the Preferences dialog
  or by setting the `gui.displayuntracked` configuration variable to `false`.

  http://thread.gmane.org/gmane.comp.version-control.git/232683

Fixes
-----
* Unicode stash names are now supported

  https://github.com/git-cola/git-cola/issues/198

* The diffs produced when reverting workspace changes were made more robust.

.. _v1.8.4:

git-cola v1.8.4
=======================
Usability, bells and whistles
-----------------------------
* Brand new German translation thanks to Sven Claussner.

* The "File" menu now provides a "New Repository..." menu action.

* `git dag` now uses a dock-widget interface so that its widgets can
  be laid-out and arranged.  Customizations are saved and restored
  the next time `git dag` is launched.

* `git dag` now has a "Zoom Best Fit" button next alongside the
  "Zoom In" and "Zoom Out" buttons.

* `Ctrl+L` now focuses the "Search" field in the `git dag` tool.

* Right-clicking in the "diff" viewer now updates the cursor position
  before performing actions, which makes it much easier to click around
  and selectively stage sections.  Previously, the current cursor position
  was used which meant that it required two clicks (left-click to update
  the position followed by right-click to get the context menu) for the
  desired section to be used.  This is now a single right-click operation.

* The `Ctrl+D` "Launch Diff Tool" action learned to automatically choose
  between `git difftool` and `git mergetool`.  If the file is unmerged then
  we automatically launch `git mergetool` on the path, otherwise we use
  `git difftool`.  We do this because `git difftool` is not intended to
  be used on unmerged paths.  Automatically using `git mergetool` when
  appropriate is the most intuitive and muscle-memory-friendly thing to do.

* You can now right-click on folders in your standard file browser
  and choose "Open With -> Git Cola"  (Linux-only).

Fixes
-----
* Python 2.6 on Mac OS X Snow Leopard does not provide a namedtuple
  at `sys.version_info`.  We now avoid using that variable for better
  portability.

* We now read the user's Git configuration from `~/.config/git/config`
  if that file is available, otherwise we use the traditional `~/.gitconfig`
  path, just like Git itself.

* Some edge cases were fixed when applying partial/selected diffs.

* The diff viewer is now properly cleared when refreshing.

  https://github.com/git-cola/git-cola/issues/194

.. _v1.8.3:

git-cola v1.8.3
===============
Usability, bells and whistles
-----------------------------
* The diff viewer now has an "Options" menu which can be
  used to set "git diff" options.  This can be used to
  ignore whitespace changes or to show a change with its
  surrounding function as context.

  https://github.com/git-cola/git-cola/issues/150

* `git cola` now remembers your commit message and will restore it
  when `git cola` is restarted.

  https://github.com/git-cola/git-cola/pull/175

* `Ctrl+M` can now be used to toggle the "Amend last commit"
  checkbox in the commit message editor.

  https://github.com/git-cola/git-cola/pull/161

* Deleting remote branches can now be done from the "Branch" menu.

  https://github.com/git-cola/git-cola/issues/152

* The commit message editor now has a built-in spell checker.

Fixes
-----
* We now avoid invoking external diffs when showing diffstats.

  https://github.com/git-cola/git-cola/pull/163

* The `Status` tool learned to reselect files when refreshing.

  https://github.com/git-cola/git-cola/issues/165

* `git cola` now remembers whether it has been maximized and will restore the
  maximized state when `git cola` is restarted.

  https://github.com/git-cola/git-cola/issues/172

* Performance is now vastly improved when staging hundreds or
  thousands of files.

* `git cola` was not correctly saving repo-specific configuration.

  https://github.com/git-cola/git-cola/issues/174

* Fix a UnicodeDecode in sphinxtogithub when building from source.

.. _v1.8.2:

git-cola v1.8.2
===============
Usability, bells and whistles
-----------------------------
* We now automatically remove missing repositories from the
  "Select Repository" dialog.

  https://github.com/git-cola/git-cola/issues/145

* A new `git cola diff` sub-command was added for diffing changed files.

Fixes
-----
* The inotify auto-refresh feature makes it difficult to select text in
  the "diff" editor when files are being continually modified by another
  process.  The auto-refresh causes it to lose the currently selected text,
  which is not wanted.  We now avoid this problem by saving and restoring
  the selection when refreshing the editor.

  https://github.com/git-cola/git-cola/issues/155

* More strings have been marked for l10n.

  https://github.com/git-cola/git-cola/issues/157

* Fixed the Alt+D Diffstat shortcut.

  https://github.com/git-cola/git-cola/issues/159

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

  https://github.com/git-cola/git-cola/issues/156

.. _v1.8.1:

git-cola v1.8.1
===============
Usability, bells and whistles
-----------------------------
* `git dag` got a big visual upgrade.

* `Ctrl+G` now launches the "Grep" tool.

* `Ctrl+D` launches difftool and `Ctrl+E` launches your editor
  when in the diff panel.

* git-cola can now be told to use an alternative language.
  For example, if the native language is German and we want git-cola to
  use English then we can create a `~/.config/git-cola/language` file with
  "en" as its contents:

  $ echo en >~/.config/git-cola/language

  https://github.com/git-cola/git-cola/issues/140

* A new `git cola merge` sub-command was added for merging branches.

* Less blocking in the main UI

Fixes
-----
* Autocomplete issues on KDE

  https://github.com/git-cola/git-cola/issues/144

* The "recently opened repositories" startup dialog did not
  display itself in the absence of bookmarks.

  https://github.com/git-cola/git-cola/issues/139

.. _v1.8.0:

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

  https://github.com/git-cola/git-cola/issues/96

* `git cola` now wraps commit messages at 72 columns automatically.
  This is configurable using the `cola.linebreak` variable to enable/disable
  the feature, and `cola.textwidth` to configure the limit.

  https://github.com/git-cola/git-cola/issues/133

* A new "Open Recent" sub-menu was added to the "File" menu.
  This makes it easy to open a recently-edited repository.

  https://github.com/git-cola/git-cola/issues/135

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

.. _v1.7.7:

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

  https://github.com/git-cola/git-cola/issues/120

.. _v1.7.6:

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

.. _v1.7.5:

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

.. _v1.7.4.1:

git-cola v1.7.4.1
=================
Fixes
-----
* Detect Homebrew so that OS X users do not need to set PYTHONPATH.

* `git dag` can export patches again.

.. _v1.7.4:

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

.. _v1.7.3:

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

.. _v1.7.2:

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
  and focused with `Alt + Shift + #`.

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

  https://github.com/git-cola/git-cola/issues/99

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

.. _v1.7.1.1:

git-cola v1.7.1.1
=================
Fixes
-----
* Further enhanced the staging/unstaging behavior in the status widget.

  https://github.com/git-cola/git-cola/issues/97

* Unmerged files are no longer listed as modified.

Packaging
---------
The `cola-$version` tarballs on github were originally setup to
have the same contents as the old tarballs hosted on tuxfamily.
The `make dist` target was changed to write files to a
`git-cola-$version` subdirectory and tarball.

This makes the filenames consistent for the source tarball,
the darwin .app tarball, and the win32 .exe installer.

.. _v1.7.1:

git-cola v1.7.1
===============
Usability, bells and whistles
-----------------------------
* Refined the staging/unstaging behavior for code reviews.

  https://github.com/git-cola/git-cola/issues/97

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

.. _v1.7.0:

git-cola v1.7.0
===============
Usability, bells and whistles
-----------------------------
* Export a patch series from `git dag` into a `patches/` directory.

* `git dag` learned to diff commits, slice history along paths, etc.

* Added instant-preview to the `git stash` widget.

* A simpler preferences editor is used to edit `git config` values.

  https://github.com/git-cola/git-cola/issues/90

  https://github.com/git-cola/git-cola/issues/89

* Previous commit messages can be re-loaded from the message editor.

  https://github.com/git-cola/git-cola/issues/33

Fixes
-----
* Display commits with no file changes.

  https://github.com/git-cola/git-cola/issues/82

* Improved the diff editor's copy/paste behavior

  https://github.com/git-cola/git-cola/issues/90

Packaging
---------
* Bumped version number to ceil(minimum git version).
  `git cola` now requires `git` >= 1.6.3.

* Simplified git-cola's versioning when building from tarballs
  outside of git.  We no longer check for a 'version' file at
  the root of the repository.  We instead keep a default version
  in `cola/version.py` and use it when `git cola`'s `.git` repository
  is not available.

.. _v1.4.3.5:

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

  https://github.com/git-cola/git-cola/issues/82

* Show the configured remote.$remote.pushurl in the GUI

  https://github.com/git-cola/git-cola/issues/83

* Removed usage of the "user" module.

  https://github.com/git-cola/git-cola/issues/86

* Avoids an extra `git update-index` call during startup.


.. _v1.4.3.4:

git-cola v1.4.3.4
=================
Usability, bells and whistles
-----------------------------
* We now provide better feedback when `git push` fails.

  https://github.com/git-cola/git-cola/issues/69

* The Fetch, Push, and Pull dialogs now give better feedback
  when interacting with remotes.  The dialogs are modal and
  a progress dialog is used.

Fixes
-----
* More unicode fixes, again.  It is now possible to have
  unicode branch names, repository paths, home directories, etc.
  This continued the work initiated by Redhat's bugzilla #694806.

  https://bugzilla.redhat.com/show_bug.cgi?id=694806

.. _v1.4.3.3:

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

.. _v1.4.3.2:

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

  https://github.com/git-cola/git-cola/issues/74

  Redhat's bugzilla #694806

  https://bugzilla.redhat.com/show_bug.cgi?id=694806

.. _v1.4.3.1:

git-cola v1.4.3.1
=================
Usability, bells and whistles
-----------------------------
* The `cola classic` tool can be now configured to be dockable.

  https://github.com/git-cola/git-cola/issues/56

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

  https://github.com/git-cola/git-cola/issues/72

  This bug originated in Redhat's bugzilla #675721 via a Fedora user.

  https://bugzilla.redhat.com/show_bug.cgi?id=675721

* Properly raise the main window on Mac OS X.

* Properly handle staging a huge numbers of files at once.

* Speed up 'git config' usage by fixing cola's caching proxy.

* Guard against damaged ~/.cola files.

.. _v1.4.3:

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

  https://github.com/git-cola/git-cola/issues/67

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

.. _v1.4.2.5:

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

  https://github.com/git-cola/git-cola/issues/62

* Fixed mouse interaction with the status widget where some
  items could not be de-selected.

Packaging
---------
* Removed hard-coded reference to lib/ when calculating Python's
  site-packages directory.

.. _v1.4.2.4:

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

.. _v1.4.2.3:

git-cola v1.4.2.3
=================
Usability, bells and whistles
-----------------------------
* Allow un/staging by right-clicking top-level items

  https://github.com/git-cola/git-cola/issues/57

* Running 'commit' with no staged changes prompts to allow
  staging all files.

  https://github.com/git-cola/git-cola/issues/55

* Fetch, Push, and Pull are now available via the menus

  https://github.com/git-cola/git-cola/issues/58

Fixes
-----
* Simplified the actions widget to work around a regression
  in PyQt4 4.7.4.

  https://github.com/git-cola/git-cola/issues/62

.. _v1.4.2.2:

git-cola v1.4.2.2
=================
Usability, bells and whistles
-----------------------------
* `git dag` interaction was made faster.

Fixes
-----
* Added '...' indicators to the buttons for
  'Fetch...', 'Push...', 'Pull...', and 'Stash...'.

  https://github.com/git-cola/git-cola/issues/51

* Fixed a hang-on-exit bug in the cola-provided
  'ssh-askpass' implementation.

.. _v1.4.2.1:

git-cola v1.4.2.1
=================
Usability, bells and whistles
-----------------------------
* Staging and unstaging is faster.

  https://github.com/git-cola/git-cola/issues/48

* `git dag` reads history in a background thread.

Portability
-----------
* Added :data:`cola.compat.hashlib` for `Python 2.4` compatibility
* Improved `PyQt 4.1.x` compatibility.

Fixes
-----
* Configured menu actions use ``sh -c`` for Windows portability.


.. _v1.4.2:

git-cola v1.4.2
===============
Usability, bells and whistles
-----------------------------
* Added support for the configurable ``guitool.<tool>.*``
  actions as described in ``git-config(1)``.

  https://github.com/git-cola/git-cola/issues/44

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

  https://github.com/git-cola/git-cola/issues/17

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

  https://github.com/git-cola/git-cola/issues/45

* Log internal ``git`` commands when ``GIT_COLA_TRACE`` is defined.

  https://github.com/git-cola/git-cola/issues/39

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

  https://github.com/git-cola/git-cola/issues/43

Packaging
---------
* Removed colon (`:`) from the applilcation name on Windows

  https://github.com/git-cola/git-cola/issues/41

* Fixed bugs with the Windows installer

  https://github.com/git-cola/git-cola/issues/40

* Added a more standard i18n infrastructure.  The install
  tree now has the common ``share/locale/$lang/LC_MESSAGES/git-cola.mo``
  layout in use by several projects.

* Started trying to accommodate Mac OSX 10.6 (Snow Leopard)
  in the ``darwin/`` build scripts but our tester is yet to
  report success building a `.app` bundle.

* Replaced use of ``perl`` in Sphinx/documentation Makefile
  with more-portable ``sed`` constructs.  Thanks to
  Stefan Naewe for discovering the portability issues and
  providing msysgit-friendly patches.

.. _v1.4.1.2:

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
* ``git update-index --refresh`` is no longer run every time
  ``git cola version`` is run.
* Don't try to watch non-existent directories when using `inotify`.
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


.. _v1.4.1.1:

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


.. _v1.4.1:

git-cola v1.4.1
===============
This feature release adds two new features directly from
`git cola`'s github issues backlog.  On the developer
front, further work was done towards modularizing the code base.

Usability, bells and whistles
-----------------------------
* Dragging and dropping patches invokes `git am`

  https://github.com/git-cola/git-cola/issues/3

* A dialog to allow opening or cloning a repository
  is presented when `git cola` is launched outside of a git repository.

  https://github.com/git-cola/git-cola/issues/22

* Warn when `push` is used to create a new branch

  https://github.com/git-cola/git-cola/issues/35

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


.. _v1.4.0.5:

git-cola v1.4.0.5
=================
Fixes
-----
* Fix launching external applications on Windows
* Ensure that the `amend` checkbox is unchecked when switching modes
* Update the status tree when amending commits


.. _v1.4.0.4:

git-cola v1.4.0.4
=================
Packaging
---------
* Fix Lintian warnings


.. _v1.4.0.3:

git-cola v1.4.0.3
=================
Fixes
-----
* Fix X11 warnings on application startup


.. _v1.4.0.2:

git-cola v1.4.0.2
=================
Fixes
-----
* Added missing 'Exit Diff Mode' button for 'Diff Expression' mode

  https://github.com/git-cola/git-cola/issues/31

* Fix a bug when initializing fonts on Windows

  https://github.com/git-cola/git-cola/issues/32


.. _v1.4.0.1:

git-cola v1.4.0.1
=================
Fixes
-----
* Keep entries in sorted order in the `cola classic` tool
* Fix staging untracked files

  https://github.com/git-cola/git-cola/issues/27

* Fix the `show` command in the Stash dialog

  https://github.com/git-cola/git-cola/issues/29

* Fix a typo when loading merge commit messages

  https://github.com/git-cola/git-cola/issues/30


.. _v1.4.0:

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


.. _v1.3.9:

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


.. _v1.3.8:

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


.. _v1.3.7:

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


.. _v1.3.6:

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
