Upcoming
========

Usability, bells and whistles
-----------------------------
* Git Cola now supports Git repositories that were created using the SHA-256
  hash algorithm, e.g. using ``git init --object-format=sha256``.

* `git dag` will now open a repository when it is specified on the command-line.
  Previously, the `--repo` option was required in order to specify a repository.
  The `git dag` positional arguments will now used when `--repo` is unspecified.

* `git dag` now special-cases the root commit when interacting with difftool
  so that diffs are performed against git's builtin empty tree.
  Other commits are diffed using ``git diff {commit}~..{commit}``.
  (`#1493 <https://github.com/git-cola/git-cola/issues/1493>`_)

* The spellcheck system now supports configuring multiple dictionaries
  using ``git config --global --add cola.dictionary <path>`` with the
  path to a newline-separated dictionary file. Dictionary files must follow
  the same format as ``/usr/share/dict/words``.

* Git Cola can now read spelling dictionaries from the `aspell` system.
  Configure ``git config --global cola.aspell.enabled true`` and
  install ``aspell-*`` language packages to add additional dictionaries.
  (`#1499 <https://github.com/git-cola/git-cola/issues/1499>`_)

* Git Cola now has non-interactive **sync** action which directly pulls
  changes from the tracking branch by ``git pull``.


Fixes
-----
* Viewing images in plain text mode (e.g. SVG files) was not displaying the
  diff text due to the deferred loading that was added to better support
  large diffs. This has been corrected.
  (`#1498 <https://github.com/git-cola/git-cola/issues/1498>`_)


.. _v4.14.0:

v4.14.0
=======

Usability, bells and whistles
-----------------------------
* Large diffs are now truncated to one megabyte by default for performance.
  The diff size limit can be changed in the diff editor's options menu.
  (`#1484 <https://github.com/git-cola/git-cola/issues/1484>`_)

* Renamed files are now detected when diffing commits using the DAG viewer's
  "Diff selected to this..." and "Diff this to selected..." actions.
  (`#1476 <https://github.com/git-cola/git-cola/issues/1476>`_)

* The DAG viewer now accepts ``-L`` arguments just like ``git log``.

* The DAG viewer can generate ``-L`` search expressions using its new
  "Trace Evolution of Line Range..." context menu action.
  (`#1483 <https://github.com/git-cola/git-cola/issues/1483>`_)

* A new ``git cola open`` sub-command can be used to launch the "Quick Open"
  dialog for opening bookmarked and recently-opened repositories.
  (`#1482 <https://github.com/git-cola/git-cola/issues/1482>`_)

* `code` (VSCode) and `cursor` are now supported for opening files at specific lines.
  (`#1487 <https://github.com/git-cola/git-cola/pull/1487>`_)

* The Stash tool now ensures that other stashes are displayed when
  dropping stashes.
  (`#1491 <https://github.com/git-cola/git-cola/issues/1491>`_)

* The "Merge into current branch" action in the Branches tool now uses
  ``git merge`` options as configured in the "Merge" dialog.
  (`#1473 <https://github.com/git-cola/git-cola/issues/1473>`_)

* The font size for the main UI elements can now be configured
  in the Preferences.
  (`#1474 <https://github.com/git-cola/git-cola/issues/1474>`_)

* The commit message editor now displays a visual indicator when
  amending a commit or when the Author and/or Commit Date has been overridden.
  (`#1490 <https://github.com/git-cola/git-cola/issues/1490>`_)

* A menu action to revert all changes was added to the diff context menu.
  (`#1492 <https://github.com/git-cola/git-cola/issues/1492>`_)

Fixes
-----
* The "Set Upstream Branch" action in the Branches tool was fixed so that it
  is robust to scenarios where the upstream branch is renamed.
  (`#1475 <https://github.com/git-cola/git-cola/issues/1475>`_)

* The "Prune Missing Entries" action in the startup dialog and the Bookmarks and Recent
  tools now save the settings after pruning.
  (`#1479 <https://github.com/git-cola/git-cola/issues/1479>`_)

* The default history viewer on Windows, used by the "Visualize Current Branch..."
  and "Visualize All Branches..." actions, was updated to avoid issues when settings
  are edited.
  (`#1496 <https://github.com/git-cola/git-cola/issues/1496>`_)

Translations
------------
* New Tamil translation.
  (`#1478 <https://github.com/git-cola/git-cola/pull/1478>`_)

Packaging and Dependencies
--------------------------
* The Windows installer now uses Python 3.12 and PyQt 6.9.


.. _v4.13.0:

v4.13.0
=======

Usability, bells and whistles
-----------------------------
* The diff viewer now displays the number of removed (``-``) and added (``+``)
  lines when the "Show filenames" tool menu option is enabled.
  (`#1471 <https://github.com/git-cola/git-cola/issues/1471>`_)

* The commit tool has a new "Set Commit Author" tool menu action that temporarily
  switches between author identities independent of your ``git config`` settings.
  The value specified in the dialog is passed directly to ``git commit --author=...``.
  (`#1469 <https://github.com/git-cola/git-cola/issues/1469>`_)

* Widget layouts can now be saved and loaded to ``*.layout`` files.
  Layouts are saved to ``~/.config/git-cola/layouts`` by default and can be
  saved and loaded using the `View > Layouts` menu actions.
  (`#1467 <https://github.com/git-cola/git-cola/issues/1467>`_)

* The status tool has been updated to launch editors with multiple files when invoking
  its "Edit" action.

* The commit date tool now has a button to set the time and date to the current time.

* The commit message editor now moves up and down visually when word-wrapping is
  enabled. The cursor previously jumped to the beginning and end of a word-wrapped line
  when Up and Down were pressed.

Fixes
-----

* The "Ambiguous shortcut warning" that could be triggered in rare scenarios when using
  the Amend hotkey has been eliminated.

Translations
------------
* Updated Japanese translation.
  (`#1472 <https://github.com/git-cola/git-cola/pull/1472>`_)


.. _v4.12.0:

v4.12.0
=======

Usability, bells and whistles
-----------------------------
* Most users will now default to editing the per-repo config by default when opening the
  settings dialog. New users that do not have the ``user.name`` and ``user.email`` settings
  configured will default to editing the global user settings, which was previously the
  default behavior for all users.
  (`#1460 <https://github.com/git-cola/git-cola/issues/1460>`_)

* The rebase tool now honors the `rebase.updateRefs` git configuration.
  The tool will only prompt you whether or not to update stacked branches / refs
  when this configuration is unset.
  (`#1458 <https://github.com/git-cola/git-cola/issues/1458>`_)

* The `rebase.updateRefs` configuration can now be configured through the
  "Update stacked branches/refs when rebasing" checkbox in the settings.

* The branches tool would previously make its branches and tags bold when text was input
  into its filter field. This behavior has been changed so that the branches and tags
  are now filtered so that only the matching branches and tags are displayed.
  (`#1457 <https://github.com/git-cola/git-cola/issues/1457>`_)

* The value of the `Force` checkbox, which causes ``git push --force`` to be used in the `Push` tool,
  now persists across sessions.
  (`#1461 <https://github.com/git-cola/git-cola/issues/1461>`_)

* The push dialog will now prompt when creating new remote branches when the
  local branch name does not match the new remote branch name.

Fixes
-----
* The push dialog was fixed to use the correct refspec arguments when pushing a local
  branch into a differently-named remote branch.
  (`#1462 <https://github.com/git-cola/git-cola/issues/1462>`_)

* The commit message length warning was not being updated in some scenarios.
  (`#1459 <https://github.com/git-cola/git-cola/issues/1459>`_)


.. _v4.11.0:

v4.11.0
=======

Usability, bells and whistles
-----------------------------
* The DAG viewer will now copy text into the your clipboard when any of the commit ID,
  author, date or summary fields are clicked in the commit diff view.
  (`#1456 <https://github.com/git-cola/git-cola/issues/1456>`_)

* The DAG viewer now has an option to disable the display of staged and modified
  changes.

* The commit message line length warning is no longer dependent on the cursor position.
  The longest line in the commit message is now used to enable the warning.
  (`#1448 <https://github.com/git-cola/git-cola/issues/1448>`_)

Fixes
-----
* The DAG view now updates itself when merging branches using the "Branches" tool.
  (`#1454 <https://github.com/git-cola/git-cola/issues/1454>`_)

* Proxy autodetection on KDE was improved to correctly handle the host and port output
  from `kreadconfig*`.
  (`#1450 <https://github.com/git-cola/git-cola/issues/1450>`_)
  (`#1451 <https://github.com/git-cola/git-cola/pull/1451>`_)
  (`#1452 <https://github.com/git-cola/git-cola/issues/1452>`_)
  (`#1453 <https://github.com/git-cola/git-cola/pull/1453>`_)

* Various widgets were made more resilient to errors when the Git worktree is externally
  deleted while Git Cola has it open.
  (`#1445 <https://github.com/git-cola/git-cola/pull/1445>`_)

* Cosmetic typos were fixed in the documentation, translations, docstrings and
  command-line help messages.
  (`#1446 <https://github.com/git-cola/git-cola/pull/1446>`_)


.. _v4.10.1:

V4.10.1
=======

Fixes
-----
* A regression in the rebase editor which prevented the display of commits was fixed.
  (`#1442 <https://github.com/git-cola/git-cola/issues/1442>`_)

* File system monitoring on Windows when using WSL was further improved.
  (`#1441 <https://github.com/git-cola/git-cola/issues/1441>`_)

Packaging and Dependencies
--------------------------
* The vendored `qtpy` library was updated to `v2.4.2`.


.. _v4.10.0:

v4.10.0
=======

Usability, bells and whistles
-----------------------------
* The DAG viewer now displays staged and modified changes alongside other commits.
  (`#1428 <https://github.com/git-cola/git-cola/issues/1428>`_)
  (`#1439 <https://github.com/git-cola/git-cola/pull/1439>`_)

* The commit message's Summary field now resizes itself to match the size of the
  configured font.
  (`#1301 <https://github.com/git-cola/git-cola/issues/1301>`_)
  (`#1435 <https://github.com/git-cola/git-cola/issues/1435>`_)

* Git Cola refreshes Git's "index" (``.git/index``) automatically on startup by default.
  This can now be disabled by configuring ``cola.updateindex`` to ``false``.
  (`#1438 <https://github.com/git-cola/git-cola/issues/1438>`_)

* The "Set Upstream Branch" menu in the "Branches" tool can grow too large to fit on
  screen when repositories contain many remote branches. A new dialog with autocomplete
  and scrollable entry fields was added for selecting a new upstream branch.
  (`#1440 <https://github.com/git-cola/git-cola/issues/1440>`_)

Fixes
-----
* Qt6 support was improved for the Recent and Favorites filters.

* A regression in the tab order when tabbing from the Summary field
  into the Extended Description field has been fixed.
  (`#1436 <https://github.com/git-cola/git-cola/issues/1436>`_)

* The file system monitoring was made more resilient on Windows
  when using WSL.
  (`#1441 <https://github.com/git-cola/git-cola/issues/1441>`_)


.. _v4.9.0:

v4.9.0
======

Usability, bells and whistles
-----------------------------
* ``git dag --follow <filename>`` is now supported for viewing the history of files
  that have been renamed.
  (`#1327 <https://github.com/git-cola/git-cola/issues/1327>`_)

* HTTP proxies are now automatically configured on Gnome and KDE Desktop Environments.
  (`#1420 <https://github.com/git-cola/git-cola/issues/1420>`_)
  (`#1431 <https://github.com/git-cola/git-cola/issues/1431>`_)

* The Git ``http.proxy`` configuration can now be edited on the settings page.
  (`#1420 <https://github.com/git-cola/git-cola/issues/1420>`_)

* `The NO_COLOR environment variable <http://no-color.org>`_ is now set to ``1`` when
  running the ``git commit``, ``git fetch``, ``git push`` and ``git pull`` commands.
  This is done to disable ANSI color output in third-party tools that can be integrated
  into these commands via git hooks. `TERM` is also set to `dumb` for tools that do not
  honor this variable.
  (`#1426 <https://github.com/git-cola/git-cola/issues/1426>`_)

* The commit message editor now has a "Set Commit Date" option that allows you
  to override the recorded date and time when authoring commits.
  (`#1429 <https://github.com/git-cola/git-cola/pull/1429>`_)

* The DAG's automatic column resizing behavior has been improved.
  (`#1432 <https://github.com/git-cola/git-cola/issues/1432>`_)

* The "Copy Commit" ``Alt + Ctrl + C`` action was added to the main menu.
  (`#1430 <https://github.com/git-cola/git-cola/issues/1430>`_)

* The DAG and main interfaces have been streamlined to reduce visual clutter.


Translations
------------
* Updated Chinese (Taiwan) translations.
  (`#1424 <https://github.com/git-cola/git-cola/pull/1424>`_)

Packaging
---------
* The ``setup.cfg`` file has been removed and ``pyproject.toml`` has been updated to
  handle all of the packaging configuration. ``pip`` will no longer install data files
  such as ``share/applications``, ``share/metainfo``, and the hotkey html files, so
  the ``garden.yaml`` and ``Makefile`` commands have been updated to provide this
  functionality instead. The html files installed in the ``cola/data/`` python package
  area are necessary for Git Cola's ``?`` hotkey window and should not be relocated.

* `notify2 <https://pypi.org/project/notify2>` (``sudo apt install python3-notify2``)
  is now supported and preferred over ``notify-py`` for sending desktop notifications.
  This is an optional dependency that enables additional features when installed.
  ``notify-py`` will continue to be used if only it is installed, but only `notify2` will
  be used when both are available. Support for the current ``notifypy`` API will be
  kept around for now but if a breaking change is ever introduced then support for
  ``notify-py`` will be dropped in favor of supporting ``notify2`` exclusively.

* Improved support for PySide6. PySide2 has some breaking divergences from PyQt6.

Fixes
-----
* The repository selection startup dialog was updated to work on Qt6/PyQt6.
  (`#1422 <https://github.com/git-cola/git-cola/issues/1422>`_)

* "Open Using Default Application" now handles paths inside a subdirectory correctly.
  (`#1419 <https://github.com/git-cola/git-cola/issues/1419>`_)

Development
-----------
* The version number reported by ``git cola version`` and the "About" dialog was made
  more accurate when Git Cola is run directly from a Git worktree.
  (`#1425 <https://github.com/git-cola/git-cola/issues/1425>`_)


.. _v4.8.2:

v4.8.2
======

Usability, bells and whistles
-----------------------------
* The Reset actions now remember the last value used.
  (`#1406 <https://github.com/git-cola/git-cola/issues/1406>`_)

Translations
------------
* Updated Japanese translation.
  (`#1411 <https://github.com/git-cola/git-cola/pull/1411>`_)

Fixes
-----
* The ``Ctrl+C`` "Copy Diff" hotkey was restored in the DAG diff viewer.
  (`#1412 <https://github.com/git-cola/git-cola/issues/1412>`_)


.. _v4.8.1:

v4.8.1
======

Usability, bells and whistles
-----------------------------
* The clone dialog now defaults to cloning into the parent directory by default.
  (`#1402 <https://github.com/git-cola/git-cola/issues/1402>`_)

Fixes
-----
* Qt6 support was improved for the right-click context menus.
  (`#1409 <https://github.com/git-cola/git-cola/issues/1409>`_)
  (`#1410 <https://github.com/git-cola/git-cola/pull/1410>`_)


.. _v4.8.0:

v4.8.0
======

Usability, bells and whistles
-----------------------------
* The Rebase editor is now aware of the ``drop``, ``break``, ``label``, ``merge`` and ``reset``
  commands that were added in recent versions of Git.

* Desktop notifications can now be enabled when pushing remotes by enabling the
  "Notify on Push" option in the preferences.
  (`#1404 <https://github.com/git-cola/git-cola/pull/1404>`_)
  (`#350 <https://github.com/git-cola/git-cola/issues/350>`_)

* Faster and easier commit hash copying in DAG. Left-clicking on the Commit ID will
  now copy it directly into the clipboard without any further action.
  (`#1401 <https://github.com/git-cola/git-cola/issues/1401>`_)

* "Grab File from Parent Commit" actions have been added to the DAG.
  (`#1401 <https://github.com/git-cola/git-cola/issues/1401>`_)

* The `Unstage Selected` action was added to the context menu for unmerged files.
  (`#1397 <https://github.com/git-cola/git-cola/pull/1397>`_)

* ``git cola rebase`` now provides  a ``--rebase-merges`` option and passes the
  same option to ``git rebase`` when `Git v1.18.0` or newer is detected.

Development
-----------
* Pre-commits hooks were updated.
  (`#1396 <https://github.com/git-cola/git-cola/pull/1396>`_)


.. _v4.7.1:

v4.7.1
======

Packaging
---------
* The `importlib_metadata` dependency which was restored for Python 3.8 and earlier
  to retain Python 3.7 support. The use of `setuptools_scm` 8.0 and newer to generate
  the `cola/_scm_version.py` version file has been deferred to prevent the need to
  upgrade Python.


.. _v4.7.0:

v4.7.0
======

Usability, bells and whistles
-----------------------------
* The Fetch dialog can now fetch directly into a remote tracking branch.
  Previously, fetching just a remote branch would fetch it into `FETCH_HEAD`,
  which is not very intuitive. If only a remote branch is selected then it makes
  more sense to fetch into that branch's remote tracking branch directly.
  Use `FETCH_HEAD` in the local branch field to fetch into `FETCH_HEAD` instead.
  (`#1387 <https://github.com/git-cola/git-cola/pull/1387>`_)

* The Fetch, Push and Pull dialogs now remember the selected remotes.
  (`#729 <https://github.com/git-cola/git-cola/issues/729>`_)

* The Fetch, Push and Pull dialogs now display the git commands that will be run.
  The Pull dialog now selects the remote branch automatically.
  (`#729 <https://github.com/git-cola/git-cola/issues/729>`_)

* The `cola.refreshonfocus` and `cola.inotify` configuration settings are now accessible
  from the `git cola config` settings dialog.

Fixes
-----
* The "Ignore" action in the Status context menu now supports adding to the local
  `.git/info/exclude` when using linked repositories created using `git worktree`.
  (`#1394 <https://github.com/git-cola/git-cola/issues/1394>`_)

* The `Cmd-m` hotkey on macOS will now minimize the application. The "Amend" action
  can now be accessed using `Alt-m`.
  (`#1390 <https://github.com/git-cola/git-cola/issues/1390>`_)
  (`#1391 <https://github.com/git-cola/git-cola/pull/1391>`_)

* The `git-cola-sequence-editor` Rebase Editor will now be found correctly
  in more situatios on Windows.
  (`#1385 <https://github.com/git-cola/git-cola/issues/1385>`_)
  (`#1388 <https://github.com/git-cola/git-cola/pull/1388>`_)

* Git Cola syncs the OS-level filesystem when windows are closed, which can
  cause performance issues. The `cola.sync` configuration variable can
  be configured to `false` to avoid this behavior.
  (`#1305 <https://github.com/git-cola/git-cola/issues/1305>`_)

Packaging
---------
* The `importlib_metadata` dependency, which was previously required for Python 3.8 and earlier,
  has been eliminated.


.. _v4.6.1:

v4.6.1
======

Packaging
---------
* `launchable` tags were added to the flatpak app metainfo files.


.. _v4.6.0:

v4.6.0
======

Usability, bells and whistles
-----------------------------
* The Rebase editor (`git-cola-sequence-editor`) can now add "remarks" to commits.
  Remarks are simple numbered flags (0-9) that allow you to mark commits. This lets
  you visually highlight commits to aid you when rebasing and grouping related commits
  across a large patch series. Remarks can be added to a single commit or to all
  commits that touch a file.
  (`#1375 <https://github.com/git-cola/git-cola/pull/1375>`_)
  (`#1380 <https://github.com/git-cola/git-cola/pull/1380>`_)

* Invalid `commit.template` configuration is now reported in the `Console` tool
  instead of presenting an error traceback dialog via a `UsageError` exception.
  (`#1384 <https://github.com/git-cola/git-cola/issues/1384>`_)

Fixes
-----
* The file system monitor was corrected to catch `PermissionError` exceptions.
  (`bz #2260155 <https://bugzilla.redhat.com/show_bug.cgi?id=2260155>`_)

Packaging
---------
* If the `polib` module (e.g. `sudo apt install python3-polib`) is installed then it
  will be used instead of the vendored `cola.polib` module. This makes it easier for
  distributions to remove the vendored module from the `cola` namespace.
  `polib` is now listed as an install requirement in `pyproject.toml`.
  (`bz #2264526 <https://bugzilla.redhat.com/show_bug.cgi?id=2264526>`_)

* The flatpak metainfo now contains the required developer name field.
  (`#1382 <https://github.com/git-cola/git-cola/pull/1382>`_)

Development
-----------
* The "actions/cache" and "styfle/cancel-workflow-action" github actions were upgraded.

* The test suite now uses ``ruff`` to validate python code. ``pylint`` is no longer used.
  (`#1353 <https://github.com/git-cola/git-cola/issues/1353>`_)
  (`#1383 <https://github.com/git-cola/git-cola/pull/1383>`_)


.. _v4.5.0:

v4.5.0
======

Usability, bells and whistles
-----------------------------
* "Stage Modified" was added to the available toolbar actions.
  (`#1371 <https://github.com/git-cola/git-cola/issues/1371>`_)

* "Stage Untracked" no longer stages modified files when the list of
  untracked files to stage is empty.
  (`#1371 <https://github.com/git-cola/git-cola/issues/1371>`_)

* `Ctrl + Space` can now be used to display the autocomplete options in input fields
  that provide autocompletion.

* The Diff widget now displays the currently selected filename.
  Uncheck the "Show filenames" option in the Diff widget's tool menu
  to disable this feature.
  (`#1367 <https://github.com/git-cola/git-cola/issues/1367>`_)

* The "Fetch", "Push" and "Pull" dialogs now have an embedded progress bar instead
  of displaying a progress bar in a separate popup window.

* The "Fetch", "Push" and "Pull" dialogs will now stay open after the remote
  operation completes when the "Close on completion" checkbox is unchecked.
  These dialogs closed themselves unconditionally before this change.

Fixes
-----
* PyQt6 compatibility for the "Find in diff" feature.

* PyQt6 compatibility for the ``git dag`` Gravatar icons.

Translations
------------
* Updated Polish translation.
  (`#1368 <https://github.com/git-cola/git-cola/pull/1368>`_)

Packaging and Dependencies
--------------------------
* The vendored `qtpy` library was updated to `v2.4.1`.

* The documentation no longer depends on `jaraco.packaging`.

Development
-----------
* upload-artifact and setup-python github actions were upgraded.


.. _v4.4.1:

v4.4.1
======

Usability, bells and whistles
-----------------------------
* The remote messages dialog is now displayed for the Pull and Push actions in the
  Branches widget only. This dialog is disabled by default and enabled in the
  main Push and Pull dialog settings.
  (`#1363 <https://github.com/git-cola/git-cola/issues/1363>`_)

* The whole-file staging actions in the Diff widget's right-click menu are now listed
  after the selection and hunk staging actions. This helps prevent accidental clicks
  from clobbering the index for the entire file.
  (`#1362 <https://github.com/git-cola/git-cola/issues/1362>`_)

* The completion popup no longer reappears after an item is selected in the
  "Checkout Branch" action and similar dialogs.
  (`#1360 <https://github.com/git-cola/git-cola/issues/1360>`_)

Fixes
-----
* PyQt6 compatibility was improved.


.. _v4.4.0:

v4.4.0
======

Usability, bells and whistles
-----------------------------
* Git Cola now preserves `# commentary` in commit messages by default.
  The `commit.cleanup` Git configuration variable can be used to
  customize this behavior. For example, if you want Git Cola to
  strip comments (the old behavior before v4.4.0) then
  you can run `git config --global commit.cleanup strip` or configure
  the "Commit Message Cleanup" setting in the Preferences window.
  (`#1330 <https://github.com/git-cola/git-cola/issues/1330>`_)

* `git dag` now includes completions for `git log` options in the text input field.

* `git dag` now provides convenient search filters when right-clicking in the
  text input field.

* A `1.25 x` Hi-DPI magnification option mode is now available in the Appearance settings.
  (`#1313 <https://github.com/git-cola/git-cola/issues/1313>`_)

* MacOS-specific application themes are now available in the Appearance settings
  when the pyobjc module is installed.
  (`#905 <https://github.com/git-cola/git-cola/issues/905>`_)

* Git Cola now runs `git commit` in the background and feedback is provided while
  the commit is running. This prevents the UI from freezing when running pre-commit
  hooks that can make `git commit` take a long time to run.
  (`#1320 <https://github.com/git-cola/git-cola/issues/1320>`_)

* The Diff context menu was reworked to reduce visual clutter and better match
  the Status context menu.
  (`#1347 <https://github.com/git-cola/git-cola/issues/1347>`_)

* The standalone `git cola tag` tool now autocompletes the tag name field.
  (`#706 <https://github.com/git-cola/git-cola/pull/706>`_)
  (`#691 <https://github.com/git-cola/git-cola/issues/691>`_)

* The "Branches" dock widget now has a "Visualize" right-click menu option.
  (`#1061 <https://github.com/git-cola/git-cola/issues/1061>`_)

* The "Stash" dialog learned to rename stashes.
  (`#558 <https://github.com/git-cola/git-cola/issues/558>`_)

* The "Fetch", "Push" and "Pull" dialogs can now display remote messages from the server.
  (`#951 <https://github.com/git-cola/git-cola/issues/951>`_)

Fixes
-----
* `git dag` fixed how it was handling refspec arguments.
  (`#1334 <https://github.com/git-cola/git-cola/issues/1334>`_)

* `git dag` will now properly refresh itself when remote branches are updated.
  (`#1063 <https://github.com/git-cola/git-cola/issues/1063>`_)

* The `cola.inotify` feature no longer runs into issues when accessing WSL2
  filesystems from Windows 11+.
  (`#1194 <https://github.com/git-cola/git-cola/issues/1194>`_)

Development
-----------
* `cercis <https://pypi.org/project/cercis/>`_ is now being used to enforce
  Git Cola's python code style. We were previously disabling quote normalization
  when using `black`. Use of `cercis` allows us to enable quote normalization
  under its default single-quote settings.

* The test suite now works on Windows.
  (`#1331 <https://github.com/git-cola/git-cola/issues/1331>`_)
  (`#1332 <https://github.com/git-cola/git-cola/pull/1332>`_)

* Pre-commits hooks and code modernization.
  (`#1333 <https://github.com/git-cola/git-cola/pull/1333>`_)

* Compatibility with Sphinx 7.2.0 was added to the `sphinxtogithub`
  sphinx documentation plugin.
  (`#1336 <https://github.com/git-cola/git-cola/pull/1336>`_)


.. _v4.3.2:

v4.3.2
======

Usability, bells and whistles
-----------------------------
* The minimum font size can now be set lower, which is helpful for Hi-DPI displays.
  (`#1342 <https://github.com/git-cola/git-cola/pull/1342>`_)

Fixes
-----
* Flashing windows during startup on Windows has been fixed.
  (`#1329 <https://github.com/git-cola/git-cola/issues/1329>`_)

* `git dag` was not displaying history when refspecs were specified.
  (`#1334 <https://github.com/git-cola/git-cola/issues/1334>`_)

Development
-----------
* Compatibility with Sphinx 7.2.0 was added to the `sphinxtogithub`
  sphinx documentation plugin.
  (`#1336 <https://github.com/git-cola/git-cola/pull/1336>`_)


.. _v4.3.1:

v4.3.1
======

Fixes
-----
* The pypi wheel was fixed to include `entry_points.txt`.

* The "Revert" command was throwing an exception after successfully completing.


.. _v4.3.0:

v4.3.0
======

Usability, bells and whistles
-----------------------------
* `git dag` now displays commit metadata more similarly to `git log`.
  The commit date is now displayed and the subject field is displayed
  directly above the extended description.

* `git dag` now supports a `cola.logdate` configuration for controlling
  the date format. The configured value is passed to `git log --date=<format>`.
  (`#1319 <https://github.com/git-cola/git-cola/pull/1319>`_)
  (`#1312 <https://github.com/git-cola/git-cola/issues/1312>`_)

* The default `patches` directory that is used when exporting patches
  is now configurable using the `cola.patchesdirectory` configuration
  variable and the Preferences dialog.

* The Diff Editor can now export the diff selection, or the current
  diff hunk, to a `*.patch` file from the `Patches` context menu action.

* Existing patches can be appended to by choosing a patch file from
  the `Append Patch` sub-menu in the `Patches` context menu action.

* Patches can now be applied by dragging and dropping patches files from
  a file browser onto the diff editor. The "Apply Patches" dialog is
  launched with the drag-and-dropped patch files.

* Shell completions for zsh are now provided in the source distribution.
  See the `contrib/_git-cola` zsh completion file for more details

Fixes
-----
* ``QApplication::desktop()`` is no longer available on PyQt6.
  Git Cola no longer relies on this method.

Packaging
---------
* Git Cola can now be installed on Windows using `winget`.
  See the ``README.md`` file for more details.
  (`#1318 <https://github.com/git-cola/git-cola/pull/1318>`_)


.. _v4.2.1:

v4.2.1
======

Fixes
-----
* Diffs for repositories with a single commit have been fixed.
  (`#1306 <https://github.com/git-cola/git-cola/issues/1306>`_)

* The toolbars follow the Qt toolbar style, as they did prior to `v4.2.0`.
  (`#1307 <https://github.com/git-cola/git-cola/issues/1307>`_)

* The "Checkout Branch" dialog was fixed to display all completions when first shown.
  (`#1308 <https://github.com/git-cola/git-cola/issues/1308>`_)


.. _v4.2.0:

v4.2.0
======

Usability, bells and whistles
-----------------------------
* The Diff Editor can now send diffs to your favorite editor before the diffs are applied.
  The right-click "Edit Diff ..." menu actions and the `Ctrl + Shift + S` /
  `Ctrl + Shift + U` hotkeys send the current diff hunk, or the selected diff, to your
  editor before they are applied to the worktree / staging area.
  (`#1290 <https://github.com/git-cola/git-cola/pull/1290>`_)
  (`#794 <https://github.com/git-cola/git-cola/issues/794>`_)

* The Diff Editor and DAG viewer can now search within their diffs using
  `Ctrl + F` and `Ctrl + G` hotkeys.
  (`#1116 <https://github.com/git-cola/git-cola/issues/1116>`_)

* A new *Diff Mode* can be used to diff and unstage edits relative to any commit.
  (`#816 <https://github.com/git-cola/git-cola/issues/816>`_)

* The Commit Message Editor can now spell-check the summary field. Previously only the
  "Extended Description..." field supported spell checking.
  (`#633 <https://github.com/git-cola/git-cola/issues/633>`_)
  (`#1070 <https://github.com/git-cola/git-cola/issues/1070>`_)

* Repositories in your "Recents" and "Favorites" can now be searched using the new
  "Search" tool button. Quickly switch between these repositories using the `Alt + P`
  hotkey and "Quick Open..." File menu action.
  (`#1282 <https://github.com/git-cola/git-cola/pull/1282>`_)

* "Favorites", "Recents" and the startup dialog now display a case-insensitively
  sorted list of repositories.
  (`#1047 <https://github.com/git-cola/git-cola/issues/1047>`_)

* The startup dialog now has a right-click context menu that allows you to prune
  stale entries and other actions that were not previously accessible from
  the startup dialog.
  (`#1199 <https://github.com/git-cola/git-cola/issues/1199>`_)
  (`#1280 <https://github.com/git-cola/git-cola/pull/1280>`_)

* The "Copy Leading Paths" action in the Status tool's right-click "Copy" sub-menu
  can now strip off an arbitrary number of leading paths.
  (`#784 <https://github.com/git-cola/git-cola/issues/784>`_)

* The "Cherry-Pick" action now reports errors when "git cherry-pick" fails.
  A new "Abort Cherry-Pick" action has been added for aborting a failed cherry-pick.
  (`#1062 <https://github.com/git-cola/git-cola/issues/1062>`_)

* The diff text can now be quickly zoomed using `Ctrl + Mouse wheel` scroll.
  This will quickly change the text size within the current session only.
  (`#1029 <https://github.com/git-cola/git-cola/issues/1029>`_)

* The Console and Diff widgets learned to open URLs. Right-click on a line
  that contains http URLs and context-menu actions for opening each URL
  using your default web browser will be displayed.
  (`#1139 <https://github.com/git-cola/git-cola/issues/1139>`_)

* Drag-and-drop has been improved when dragging filenames from the Status tool.
  Dragging multiple files requires special handling to improve usability.
  Some terminals (such as `kitty`) consume multiple file URLs by separating paths with
  newlines. This is useful when you'd like to capture raw filenames but is less
  convenient when dropping  filenames onto a command-line. Drag with the `Alt`-modifier
  held down to drag-and-drop filenames for command-line use. Using the `Alt` modifier
  omits URLs so that the drag-and-drop payload includes only space-delimited,
  shell-quoted paths.
  (`#719 <https://github.com/git-cola/git-cola/issues/719>`_)

* The DAG viewer now displays the diff between the start and end commits when
  multiple commits are selected. The diffs are displayed in the DAG's diff viewer.
  (`#552 <https://github.com/git-cola/git-cola/issues/552>`_)

* The DAG viewer learned to checkout branches and initiate rebases from its right-click menu.
  (`#1113 <https://github.com/git-cola/git-cola/issues/1113>`_)

* The DAG diff viewer learned to word-wrap the diff text.
  (`#1242 <https://github.com/git-cola/git-cola/issues/1242>`_)

* The spelling dictionaries are now discovered dynamically at runtime.
  `dict/words` and `dict/propernames` are now discovered via `$XDG_DATA_DIRS`
  by the spell checker. This allows a spelling dictionary to be placed in e.g..
  `~/.local/share/dict/words` to override the default `/usr/share/dict/words`.
  (`#873 <https://github.com/git-cola/git-cola/issues/873>`_)

* The File menu now has a "Patches" sub-menu with a full set of "git am" Patch actions.

* The Diff Editor and various Diff widgets now have a "Copy Diff" action with an
  `Alt + Shift + C` hotkey that copies the selected diff text to the clipboard with the
  `+`, `-` and `<Space>` diff prefix characters removed.
  (`#1288 <https://github.com/git-cola/git-cola/issues/1288>`_)

* The "Revert" action for reverting commits from the DAG tool now displays error
  messages when ``git revert`` fails.
  (`#885 <https://github.com/git-cola/git-cola/issues/885>`_)

* The Diff Editor now uses an easier-to-see *block cursor* by default.
  Disable `cola.blockcursor <https://git-cola.readthedocs.io/en/latest/git-cola.html#cola-blockcursor>`_
  to continue using original *line cursor* by running
  ``git config --global cola.blockcursor false``, or by editing the settings in the menu.

* The "Unmerged" header item in the Status tool now displays a summary list of unmerged files.

* The hotkeys documentation has been updated to clarify that the "Copy Commit ID"
  action is available in several tools.
  (`#779 <https://github.com/git-cola/git-cola/issues/779>`_)

* Saving files when using "Browse Other Branch" now displays errors from
  ``git show`` when saving files from arbitrary commits.
  (`#1065 <https://github.com/git-cola/git-cola/issues/1065>`_)

* The Apply Patches dialog now reports errors when patches fail to apply.
  (`#673 <https://github.com/git-cola/git-cola/issues/673>`_)

* The "Status" tool now disables "Copy" actions in its context menu when no
  files have been selected.
  (`#697 <https://github.com/git-cola/git-cola/issues/697>`_)

* The "Unstage" menu item in the Status tool now uses a "Remove" icon.
  (`#1289 <https://github.com/git-cola/git-cola/pull/1289>`_)

Development
-----------
* The vendored `qtpy` module was modified to sever its dependency on the
  `packaging.version` module. This mostly affects users that want to run
  Git Cola directly from the source tree outside of any virtualenv.
  (`#1286 <https://github.com/git-cola/git-cola/issues/1286>`_)


.. _v4.1.0:

v4.1.0
======

Usability, bells and whistles
-----------------------------
* The rebase editor was taught to handle stacked branch workflows enabled by
  ``git rebase --update-refs``. The ``git cola rebase`` sub-command now has
  an ``--update-refs`` option and the menu actions display a prompt that allows
  you to enable the updating of stacked branches.
  (`#1261 <https://github.com/git-cola/git-cola/pull/1261>`_)
  (`#571 <https://github.com/git-cola/git-cola/issues/571>`_)

* The status widget now respects `diff.ignoreSubmodules`.
  (`#1269 <https://github.com/git-cola/git-cola/issues/1269>`_)

Packaging and Dependencies
--------------------------
* PyQt6 is now officially supported.
  (`#1211 <https://github.com/git-cola/git-cola/issues/1211>`_)
  (`#1273 <https://github.com/git-cola/git-cola/issues/1273>`_)

* The vendored `qtpy` library was updated to `v2.3.0`.

Development
-----------
* Fixes and updates to Git Cola's CI actions.
  (`#1278 <https://github.com/git-cola/git-cola/pull/1278>`_)
  (`#1277 <https://github.com/git-cola/git-cola/issues/1277>`_)


.. _v4.0.4:

v4.0.4
======

Fixes
-----
* The "T" hotkey for "Find Files" was removed to avoid issues in some configurations.
  (`#1270 <https://github.com/git-cola/git-cola/issues/1270>`_)

* Some context menus entries were corrected to better handle binary files.
  (`#1271 <https://github.com/git-cola/git-cola/pull/1271>`_)


.. _v4.0.3:

v4.0.3
======

Usability, bells and whistles
-----------------------------
* The branches widget no longer loses its selection state in response to
  notifications and UI actions.
  (`#1221 <https://github.com/git-cola/git-cola/issues/1221>`_)

* The use of ``gravatar.com`` to fetch icons associated with author emails
  can now be disabled by setting `git config --global cola.gravatar false`.
  (`#933 <https://github.com/git-cola/git-cola/issues/933>`_)

Fixes
-----
* The config reader has been revamped to better read settings when git config
  files are located in unexpected locations.
  (`#927 <https://github.com/git-cola/git-cola/issues/927>`_)
  (`#1264 <https://github.com/git-cola/git-cola/issues/1264>`_)

* The preferences dialog no longer throws an error when the editor has not
  been configured.
  (`#1263 <https://github.com/git-cola/git-cola/issues/1263>`_)

* Context menu actions for staging files has been added when diffing images.
  (`#1265 <https://github.com/git-cola/git-cola/issues/1265>`_)

* The stash editor now properly displays stashes with slashes ("/") in
  their names or messages.
  (`#1267 <https://github.com/git-cola/git-cola/pull/1267>`_)

* The settings file is now written-to and read-from in a robust manner to avoid data
  loss when doing an ACPI shutdown or forced shutdown of a machine.
  (`#1241 <https://github.com/git-cola/git-cola/issues/1241>`_)

* Git Cola now displays an error message when attempting to open a repository that
  cannot be accessed due to the new `safe.directory` protections in Git v2.30.3.
  (`#1243 <https://github.com/git-cola/git-cola/issues/1243>`_)

Translations
------------
* The .po and .pot files now contain location information.
  (`#880 <https://github.com/git-cola/git-cola/issues/880>`_)


.. _v4.0.2:

v4.0.2
======

Usability, bells and whistles
-----------------------------
* The Rebase editor (`git-cola-sequence-editor`) now supports multi-select.
  Use `Shift-{Up,Down}` to select multiple lines and the keyboard hotkeys
  listed in the `?` dialog to drive the UI.
  (`#1257 <https://github.com/git-cola/git-cola/pull/1257>`_)

* The `$GIT_VISUAL` and `$VISUAL` environment variable are now consulted in addition
  to `$GIT_EDITOR` and `$EDITOR` when the `gui.editor` configuration is unset.
  (`#1237 <https://github.com/git-cola/git-cola/pull/1237>`_)

* The application window icon is now enabled when running on Wayland.
  (`#1240 <https://github.com/git-cola/git-cola/pull/1240>`_)

* The Status widget now has an "Open Worktree" action.
  (`#1245 <https://github.com/git-cola/git-cola/pull/1245>`_)

* The "Open Using Default Application", "Open Directory",
  "Open Parent Directory" and "Open Worktree" actions are now available on Windows.

* The dialog for opening repositories is now a read-only dialog that omits the
  ability to create folders and modify the filesystem.
  (`#1168 <https://github.com/git-cola/git-cola/issues/1168>`_)

* A few more `git` calls have been eliminated from the startup sequence.
  This further improved the startup time for Git Cola.
  (`#1259 <https://github.com/git-cola/git-cola/pull/1259>`_)

Fixes
-----
* Documentation rendering errors have been fixed.
  (`#1256 <https://github.com/git-cola/git-cola/pull/1256>`_)

* Use of a `~/.config/git-cola/language` file to override the language has been fixed.
  (`#1246 <https://github.com/git-cola/git-cola/issues/1246>`_)

* We no longer write the `cola.spellcheck` configuration value on launch.
  (`#1238 <https://github.com/git-cola/git-cola/pull/1238>`_)

Translations
------------
* Updated Spanish translation.
  (`#1244 <https://github.com/git-cola/git-cola/pull/1244>`_)

* Updated Japanese translation.
  (`#1249 <https://github.com/git-cola/git-cola/pull/1249>`_)

Packaging
---------
* Building documentation offline is supported again.
  (`#1250 <https://github.com/git-cola/git-cola/issues/1250>`_)

* The Appstream Metadata files were missing in the v4.0.0 release are included again.
  (`#1254 <https://github.com/git-cola/git-cola/pull/1254>`_)
  (`#1253 <https://github.com/git-cola/git-cola/issues/1253>`_)


.. _v4.0.1:

v4.0.1
======

Usability, bells and whistles
-----------------------------
* Double-clicking dock widgets no longer creates sub-windows when the layout is locked.
  (`#1176 <https://github.com/git-cola/git-cola/issues/1176>`_)
  (`#1198 <https://github.com/git-cola/git-cola/pull/1198>`_)

Fixes
-----
* We now guard against `locale.getdefaultlocale()` returning `None` in some
  configurations, notably on macOS if none of 'LC_ALL', 'LC_CTYPE', 'LANG' or 'LANGUAGE'
  are defined.
  (`#1234 <https://github.com/git-cola/git-cola/issues/1234>`_)

* The preferences dialog has been fixed to properly handle booleans.
  (`#1235 <https://github.com/git-cola/git-cola/pull/1235>`_)

* The `docs/` directory was restructured to avoid missing `setup.py` errors.
  `share/doc/git-cola` is now a symlink pointing to `docs/`.
  (`#1230 <https://github.com/git-cola/git-cola/issues/1230>`_)

* Message boxes could sometimes display off-screen or using geometry that is larger
  than the current desktop. Message box sizes are now clamped to the desktop size.
  (`#1228 <https://github.com/git-cola/git-cola/issues/1228>`_)


.. _v4.0.0:

v4.0.0
======

Breaking Changes
----------------
These changes are primarily breaking changes for packagers of Git Cola.
For example, Linux distribution and Homebrew package maintainers may need to
be aware of these changes.

Changes have been made build infrastructure and the resulting filesystem artifacts.

* The build system is now Python3-only and has been modernized for PEP-517/518.
  While Git Cola still builds and runs under Python2, it is no longer officially
  supported and may stop working in a future release without notice.
  (`#1201 <https://github.com/git-cola/git-cola/issues/1201>`_)

* ``Qt4`` / ``PyQt4`` is no longer supported.

* The `#!/usr/bin/env python` shebang lines in the `git-cola` and `git-dag` wrapper
  scripts have been updated to use `python3`.
  (`#1204 <https://github.com/git-cola/git-cola/pull/1204>`_)

* The build system was switched to `setuptools` and no longer depends on `distutils`.
  ``python setup.py {build,install,build_pot,build_mo}`` are no longer provided.
  Use the https://pypa-build.readthedocs.io/en/stable/installation.html
  ``python -m build`` tool to generate sdist and wheel distributions,
  and ``pip install .`` to install Git Cola from source.
  (`#1204 <https://github.com/git-cola/git-cola/pull/1204>`_)

* The `git-cola`, `git-dag` and `git-cola-sequence-editor` commands are now installed
  using setuptools entry points.

* The `bin/` wrapper scripts in the source tree continue to be provided for convenience
  but they are not the scripts that get installed.

* The `qtpy` Python package is no longer installed alongside the `cola` Python package.

* The `cola` package is now installed into the standard Python site-packages location.

* The `share/git-cola/lib` private Python modules directory no longer exists.

* The `NO_VENDOR_LIBS` and `NO_PRIVATE_LIBS` Makefile options are no longer necessary.

* The `share/git-cola` filesystem namespace no longer exists. All of cola's package data
  is distributed alongside the `cola` module as package data.

* Building the Sphinx documentation now also requires the `jaraco.packaging` and
  `rst.linker` packages. See `setup.cfg` for the package requirement details.

Usability, bells and whistles
-----------------------------
* `Custom UI themes
  <https://git-cola.readthedocs.io/en/latest/git-cola.html#custom-themes>`_
  can be used by adding `*.qss` Qt stylesheet files to `~/.config/git-cola/themes/`.
  (`#1222 <https://github.com/git-cola/git-cola/pull/1222>`_)
  (`#1226 <https://github.com/git-cola/git-cola/pull/1226>`_)

* Git Cola now keeps track of child Browser windows and will close all of them when
  the main window is closed.
  (`#1200 <https://github.com/git-cola/git-cola/pull/1200>`_)

Fixes
-----
* Staging conflicted binary files has been fixed to avoid Unicode decoding errors.
  (`#1189 <https://github.com/git-cola/git-cola/issues/1189>`_)

* Ensure that secure permissions are used when creating temporary files.
  (`#1209 <https://github.com/git-cola/git-cola/pull/1209>`_)

* The line numbering in the diff viewer was corrected when displaying merge diffs.
  (`#1208 <https://github.com/git-cola/git-cola/pull/1208>`_)

* Documentation typo fixes.
  (`#1193 <https://github.com/git-cola/git-cola/pull/1193>`_)

* Git Cola was revamped to use Qt signals and slots for all of its notifications.
  This made its notification system more robust.
  (`#1202 <https://github.com/git-cola/git-cola/pull/1202>`_)
  (`#1203 <https://github.com/git-cola/git-cola/pull/1203>`_)
  (`#1205 <https://github.com/git-cola/git-cola/pull/1205>`_)
  (`#1206 <https://github.com/git-cola/git-cola/pull/1206>`_)

Packaging
---------
* `vcruntime140.dll` and `msvcp140.dll` are now included in the Windows installation.
  (`#1207 <https://github.com/git-cola/git-cola/pull/1207>`_)


.. _v3.12.0:

v3.12.0
=======

Usability, bells and whistles
-----------------------------
* The git config guitool action can now be grouped under user-defined menus.
  This is done by using slash (``/``) delimiters in the action name.
  Entries before the final slash are treated like sub-menus inside the
  top-level ``Actions`` menu.
  (`#1150 <https://github.com/git-cola/git-cola/issues/1150>`_)

* Toolbars now have a full set of icons. The icons follow the system theme
  and can be configured to display text, just icons, or text and icons.
  (`#1177 <https://github.com/git-cola/git-cola/pull/1177>`_)

* The startup dialog will now open the selected repository when the "enter"
  key is pressed.
  (`#1162 <https://github.com/git-cola/git-cola/issues/1162>`_)

* ``Shift+S`` will stage selected lines (in addition to ``s``).
  (`#1187 <https://github.com/git-cola/git-cola/issues/1187>`_)

Fixes
-----
* The vendored qtpy library was patched to retain Python2 compatibility.

* The "Unstage" toolbar action was fixed.
  (`#1178 <https://github.com/git-cola/git-cola/issues/1178>`_)

* We now avoid `QWidget::setWidth(float)` for compatibility with newer Qt versions.
  (`#1183 <https://github.com/git-cola/git-cola/pull/1183>`_)

* Documentation typo fixes.
  (`#1185 <https://github.com/git-cola/git-cola/pull/1185>`_)

Translations
------------
* Updated Polish translation.
  (`#1184 <https://github.com/git-cola/git-cola/pull/1184>`_)

Development
-----------
* Git Cola now uses Github Actions for running its continuous integration tests.
  (`#1179 <https://github.com/git-cola/git-cola/pull/1179>`_)


.. _v3.11.0:

v3.11.0
=======

Usability, bells and whistles
-----------------------------
* The Status tool was improved to better retain selected files when
  the state changes and the display is refreshed.
  (`#1130 <https://github.com/git-cola/git-cola/issues/1130>`_)
  (`#1131 <https://github.com/git-cola/git-cola/pull/1131>`_)

* The Diff editor can now stage selected lines for untracked files.
  Git Cola will detect when a file is untracked and will allow you to
  partially stage it, just like existing tracked files.
  (`#1146 <https://github.com/git-cola/git-cola/pull/1146>`_)
  (`#1084 <https://github.com/git-cola/git-cola/issues/1084>`_)

* Diffing of staged files has been implemented for repositories that contain
  no commits.
  (`#1149 <https://github.com/git-cola/git-cola/pull/1149>`_)
  (`#1110 <https://github.com/git-cola/git-cola/issues/1110>`_)

* Documentation improvements and typo fixes.
  (`#1163 <https://github.com/git-cola/git-cola/pull/1163>`_)
  (`#1164 <https://github.com/git-cola/git-cola/pull/1164>`_)

Security
--------
* The `FIPS security mode <https://github.com/python/cpython/issues/53462>`_
  is now supported by Git Cola when running on FIPS-enabled Python
  (Python 3.9+ or centos8/rhel8's patched Python 3.6).
  (`#1157 <https://github.com/git-cola/git-cola/issues/1157>`_)

Fixes
-----
* The `argparse` usage was adjusted to remain compatible with older Pythons.
  (`#1155 <https://github.com/git-cola/git-cola/issues/1155>`_)

* The window restoration logic was fixed to properly save/restore settings
  when different languages are used.
  (`#1071 <https://github.com/git-cola/git-cola/issues/1071>`_)
  (`#1161 <https://github.com/git-cola/git-cola/issues/1161>`_)
  (`#382 <https://github.com/git-cola/git-cola/issues/382>`_)

* `git dag` no longer passes floats to `QPen::setWidth()` for better compatibility.
  (`bz #2014950 <https://bugzilla.redhat.com/show_bug.cgi?id=2014950>`_)

Packaging
---------
* The Windows installer was slimmed down by removing unused Qt DLLs.
  (`#1152 <https://github.com/git-cola/git-cola/pull/1152>`_)


.. _v3.10.1:

v3.10.1
=======

Fixes
-----
* Patch release to fix a typo in the Interactive Rebase feature.

.. _v3.10:

v3.10
=====

Usability, bells and whistles
-----------------------------
* The git config reader now supports the `include.path` directive
  for including config files.
  (`#1136 <https://github.com/git-cola/git-cola/issues/1136>`_)
  (`#1137 <https://github.com/git-cola/git-cola/pull/1137>`_)

* The dialog for selecting commits now support filtering.
  (`#1121 <https://github.com/git-cola/git-cola/pull/1121>`_)

* The diff editor now wraps long lines by default. The diff options
  menu can be used to enable/disable line wrapping.
  (`#1123 <https://github.com/git-cola/git-cola/pull/1123>`_)

* Git Cola now honors `core.hooksPath` for configuring custom Git hooks,
  which was introduced in Git v2.9.
  (`#1118 <https://github.com/git-cola/git-cola/issues/1118>`_)

* A new `Ctrl + Shift + S` hotkey was added for staging/unstaging all
  files, both modified and untracked.

* The `Status` tool now supports `Ctrl + A` for selecting all files and
  it behaves more predictably when performing operations when multiple
  categories of files are selected (e.g. when both modified and untracked
  header items are selected).
  (`#1117 <https://github.com/git-cola/git-cola/issues/1117>`_)

Translations
------------
* Updated Hungarian translation.
  (`#1135 <https://github.com/git-cola/git-cola/pull/1135>`_)

Fixes
-----
* The "Interactive Rebase" feature was updated to work with Windows.

* `make install-man` was updated to support Sphinx 4.0.
  (`#1141 <https://github.com/git-cola/git-cola/issues/1141>`_)

* `git cola --help-commands` was updated for newer versions of argparse.
  (`#1133 <https://github.com/git-cola/git-cola/issues/1133>`_)

Development
-----------
* Git Cola can now be started as a Python module.
  (`#1119 <https://github.com/git-cola/git-cola/pull/1119>`_)


.. _v3.9:

v3.9
====

Usability, bells and whistles
-----------------------------
* The startup dialog now detects when Recent and Favorite repositories no
  longer exist on disk, and offers to remove these entries when selected.
  (`#1089 <https://github.com/git-cola/git-cola/pull/1089>`_)

* The startup dialog now includes a simpler and more condensed folder view
  that can be used for selecting Favorites and Recent repositories.
  (`#1086 <https://github.com/git-cola/git-cola/pull/1086>`_)

* The "Commit" menu now includes an "Undo Last Commit" action.
  (`#890 <https://github.com/git-cola/git-cola/issues/890>`_)

* The "Reset" menu was revamped to expose all of Git's reset modes alongside a
  new "Restore Worktree" action that updates the worktree using "git read-tree".
  (`#890 <https://github.com/git-cola/git-cola/issues/890>`_)

Translations
------------
* Updated Polish translation.
  (`#1107 <https://github.com/git-cola/git-cola/pull/1107>`_)

* Updated Japanese translation.
  (`#1098 <https://github.com/git-cola/git-cola/pull/1098>`_)

* Updated Brazilian translation.
  (`#1091 <https://github.com/git-cola/git-cola/pull/1091>`_)

Packaging
---------
* The ``--use-env-python`` option for ``setup.py`` is now Python3 compatible.
  (`#1102 <https://github.com/git-cola/git-cola/issues/1102>`_)


.. _v3.8:

v3.8
====

Usability, bells and whistles
-----------------------------
* The submodules widget can now be used to add submodules.
  Submodules are now updated recursively.
  (`#534 <https://github.com/git-cola/git-cola/issues/534>`_)

* The image diff viewer can now be toggled between text and image modes.
  This is helpful when, for example, diffing .svg files where it can be useful
  to see diffs in both an image and text representation.
  (`#859 <https://github.com/git-cola/git-cola/issues/859>`_)
  (`#1035 <https://github.com/git-cola/git-cola/pull/1035>`_)

* The default `ssh-askpass` username + password dialog included with Git Cola
  can now toggle between showing and masking the password input field.
  (`#1069 <https://github.com/git-cola/git-cola/pull/1069>`_)

Translations
------------
* Updated Polish translation.
  (`#1076 <https://github.com/git-cola/git-cola/pull/1076>`_)

* Updated Hungarian translation.
  (`#1067 <https://github.com/git-cola/git-cola/pull/1067>`_)

Packaging
---------
* The `share/appdata` AppStream data was renamed to `share/metainfo`
  in accordance with `AppStream standard changes from 2016
  <https://github.com/ximion/appstream/blob/master/NEWS#L1363>`_.
  (`#1079 <https://github.com/git-cola/git-cola/pull/1079>`_)

* The ``cola`` modules are now installed into the Python ``site-packages``
  directory by default.  This allows distributions to package ``git-cola`` for
  multiple versions of Python.  See the PACKAGING NOTES section in the README
  for details about suppressing the installation of the private
  ``share/git-cola/lib/cola`` modules when building cola.
  (`#181 <https://github.com/git-cola/git-cola/issues/181>`_)

* Git Cola's rebase / sequence editor, formerly known as ``git-xbase`` and
  installed as ``share/git-cola/bin/git-xbase``, has been renamed to
  ``git-cola-sequence-editor`` and is now installed into the default
  ``bin/git-cola-sequence-editor`` executable location to enable external
  reuse of this general-purpose tool.

* A workaround used by the pynsist installer preamble script was obsoleted by
  `takluyver/pynsist#149 <https://github.com/takluyver/pynsist/pull/149>`_
  and has now been removed.
  (`#1073 <https://github.com/git-cola/git-cola/pull/1073>`_)

Fixes
-----
* `git dag` now uses integer widths when initializing its brushes.
  (`#1080 <https://github.com/git-cola/git-cola/pull/1080>`_)


.. _v3.7:

v3.7
====

Usability, bells and whistles
-----------------------------
* The ``git-xbase`` rebase editor now includes a file list for filtering
  the changes displayed in the diff view.
  (`#1051 <https://github.com/git-cola/git-cola/pull/1051>`_)

* The fallback `ssh-askpass` script, which provides the Username/Password
  login dialog when performing remote operations, previously presented both
  the username and password input fields with ``***`` asterisks.
  The dialog now uses asterisks for the password field only.
  (`#1026 <https://github.com/git-cola/git-cola/pull/1026>`_)

* Stashes can now be applied using the `Ctrl + Enter` hotkey, popped with the
  `Ctrl + Backspace` hotkey, and dropped with the `Ctrl + Shift + Backspace`
  hotkey when inside the stash dialog.  This enables a keyboard-centric
  mouse-free workflow when using the stash dialog.

* When amending a commit, `git cola` will check whether the commit has been
  published to a remote branch using ``git branch -r --contains HEAD``.
  This command can be slow when operating on a repository with many
  remote branches.  The new `cola.checkpublishedcommits` configuration
  variable allows you to opt-out of this check, which improves performance
  when amending a commit.  The settings widget exposes this variable as,
  "Check Published Commits when Amending".
  (`#1021 <https://github.com/git-cola/git-cola/issues/1021>`_)
  (`#1027 <https://github.com/git-cola/git-cola/pull/1027>`_)

Translations
------------
* Updated Polish translation.
  (`#1033 <https://github.com/git-cola/git-cola/pull/1033>`_)

Fixes
-----
* ``git-dag.appdata.xml`` was updated to allow network access for author icons.
  (`#1050 <https://github.com/git-cola/git-cola/pull/1050>`_)

* The inotify filesystem monitor now handles
  `OSError: [Errno 24] Too many open files` errors by disabling inotify.
  (`#1015 <https://github.com/git-cola/git-cola/issues/1015>`_)

* Typos in various documentation files have been fixed.
  (`#1025 <https://github.com/git-cola/git-cola/pull/1025>`_)

* The "Recent Repositories" limit was off by one, and now correctly
  remembers the configured number of repositories in the menu.
  (`#1024 <https://github.com/git-cola/git-cola/pull/1024>`_)

* The "revert" action in the DAG and other tools now uses
  ``git revert --no-edit``, which avoids launching an editor
  when reverting the commit.  Use `Ctrl+m` in the commit message
  editor after reverting a commit to rewrite its commit message.
  (`#1020 <https://github.com/git-cola/git-cola/issues/1020>`_)


.. _v3.6:

v3.6
====

Usability, bells and whistles
-----------------------------
* The remote editor is much faster since it no longer queries
  remotes, and uses the cached information instead.
  (`#986 <https://github.com/git-cola/git-cola/issues/986>`_)

* Commit message templates can now be loaded automatically by setting
  ``git config cola.autoloadcommittemplate true``.
  (`#1013 <https://github.com/git-cola/git-cola/pull/1013>`_)
  (`#735 <https://github.com/git-cola/git-cola/pull/735>`_)

* The UI layout can now be reset back to its initial state by selecting
  the "Reset Layout" action.  This reverts the layout to the same state
  as when the app first launched.
  (`#1008 <https://github.com/git-cola/git-cola/pull/1008>`_)
  (`#994 <https://github.com/git-cola/git-cola/issues/994>`_)

* Files can now be ignored in either the project's `.gitignore`, or in the
  repository's private local `.git/info/exclude` ignore file.
  (`#1006 <https://github.com/git-cola/git-cola/pull/1006>`_)
  (`#1000 <https://github.com/git-cola/git-cola/issues/1000>`_)

* New remotes are now selected when they are added in the "Edit Remotes" tool.
  (`#1002 <https://github.com/git-cola/git-cola/pull/1002>`_)

* The "Recent" repositories list is now saved to disk when opening a
  repository.  Previously, this list was only updated when exiting the app.
  (`#1001 <https://github.com/git-cola/git-cola/pull/1001>`_)

* The bookmarks tool now has a "Delete" option in its right-click menu.
  (`#999 <https://github.com/git-cola/git-cola/pull/999>`_)

* The current repository is no longer listed in the "File/Open Recent" menu.
  (`#998 <https://github.com/git-cola/git-cola/pull/998>`_)

Translations
------------
* Updated Hungarian translation.
  (`#1005 <https://github.com/git-cola/git-cola/pull/1005>`_)
  (`#1018 <https://github.com/git-cola/git-cola/pull/1018>`_)

* Updated Turkish translation.
  (`#1003 <https://github.com/git-cola/git-cola/pull/1003>`_)
  (`#1011 <https://github.com/git-cola/git-cola/pull/1011>`_)

Fixes
-----
* Better support for Python 3.8's line buffering modes.
  (`#1014 <https://github.com/git-cola/git-cola/pull/1014>`_)

* The default `ssh-askpass` script now uses a more generic `#!` shebang line.
  (`#1012 <https://github.com/git-cola/git-cola/pull/1012>`_)

* Fetch, push, and pull operations will now refresh the model and display when
  operations complete.
  (`#996 <https://github.com/git-cola/git-cola/issues/996>`_)

* The branches widget now refreshes its display when changing branches.
  (`#992 <https://github.com/git-cola/git-cola/pull/992>`_)

Packaging
---------
* The `share/git-cola/bin/git-xbase` script will now have its `#!` lines
  updated during installation.
  (`#991 <https://github.com/git-cola/git-cola/pull/991>`_)

Development
-----------
* The unit tests were made more platform-independent.
  (`#993 <https://github.com/git-cola/git-cola/pull/993>`_)


.. _v3.5:

v3.5
====

Usability, bells and whistles
-----------------------------
* Auto-completion for filenames can now be disabled.  This speeds up
  revision completion when working in large repositories with many files.
  (`#981 <https://github.com/git-cola/git-cola/pull/981>`_)

* The Stash dialog now shows the stash date as a tooltip when hovering
  over a stashed change.
  (`#982 <https://github.com/git-cola/git-cola/pull/982>`_)

* Qt HiDPI settings are overridden by the `git cola` HiDPI appearance settings.
  These overrides can now be disabled by selecting the "Disable" mode.
  This allows users to control the Qt HiDPI settings through environment
  variables.  Additionally, the "Auto" mode now detects the presence of
  the Qt HiDPI variables and no longer overrides them when the user has
  configured their environment explicitly.
  (`#963 <https://github.com/git-cola/git-cola/issues/963>`_)

* Confirmation dialogs can now focus buttons using the Tab key.
  Previously, the "Y" and "N" keys could be used to confirm or deny
  using the keyboard, but "Tab" is more familiar.
  (`#965 <https://github.com/git-cola/git-cola/issues/965>`_)

* Error dialogs (for example, when a commit hook fails) will now always
  show the details.  The details were previously hidden behind a toggle.
  (`#968 <https://github.com/git-cola/git-cola/issues/968>`_)

Translations
------------
* Updated Japanese translation.
  (`#973 <https://github.com/git-cola/git-cola/pull/973>`_)
  (`#974 <https://github.com/git-cola/git-cola/pull/974>`_)

* Updated Simplified Chinese translation.
  (`#950 <https://github.com/git-cola/git-cola/pull/950>`_)

Fixes
-----
* The filesystem monitor no longer logs that it has been enabled after the
  inotify watch limit is reached on Linux.
  (`#984 <https://github.com/git-cola/git-cola/pull/984>`_)

* Better Unicode robustness.
  (`#990 <https://github.com/git-cola/git-cola/issues/990>`_)
  (`#910 <https://github.com/git-cola/git-cola/issues/991>`_)

* The "Branches" widget did not always update itself when deleting branches
  (for example, when inotify is disabled or unavailable).
  (`#978 <https://github.com/git-cola/git-cola/issues/978>`_)

* Non-ASCII Unicode byte strings are more robustly handled by the log widget.
  (`#977 <https://github.com/git-cola/git-cola/issues/977>`_)

* Non-Unicode results from the `gettext` library are more robustly handled.
  (`#969 <https://github.com/git-cola/git-cola/issues/969>`_)

* Launching `git cola` from within a directory that has since been deleted
  would previously result in an error, and is now robustly handled.
  (`#961 <https://github.com/git-cola/git-cola/issues/961>`_)

Packaging
---------
* The vendored `qtpy` library was updated to `v1.9`.


.. _v3.4:

v3.4
====

Usability, bells and whistles
-----------------------------
* The file browser now includes "Blame" in its context menu.
  (`#953 <https://github.com/git-cola/git-cola/issues/953>`_)

* The "Push" action now uses "git push --force-with-lease" when using
  the "Force" option with Git v1.8.5 and newer.
  (`#946 <https://github.com/git-cola/git-cola/issues/946>`_)

* Updated German translation.
  (`#936 <https://github.com/git-cola/git-cola/pull/936>`_)

* The `Status` widget learned to optionally display file counts in its
  category headers, and indent the files displayed in each category.
  (`#931 <https://github.com/git-cola/git-cola/pull/931>`_)

* The `Branches` widget can now sort branches by their most recent commit.
  (`#930 <https://github.com/git-cola/git-cola/pull/930>`_)

* `git cola` now includes configurable GUI themes that can be used to style
  the user interface.  Enable the new themes by configuring `cola.theme`
  in the preferences window.  See the
  `cola.theme documentation <https://git-cola.readthedocs.io/en/latest/git-cola.html#cola-theme>`_
  for more details.  (`#924 <https://github.com/git-cola/git-cola/pull/924>`_)

* `git cola` now has built-in support for HiDPI displays by enabling
  the Qt 5.6 `QT_AUTO_SCREEN_SCALE_FACTOR` feature.
  (`#938 <https://github.com/git-cola/git-cola/issues/938>`_)

* `git cola` now uses HiDPI pixmaps when rendering icons, and the builtin
  icons have been updated to look sharp when displayed in HiDPI.
  (`#932 <https://github.com/git-cola/git-cola/pull/932>`_)

Fixes
-----
* `git cola`'s "Revert Unstaged Edits" previously checked out from "HEAD^",
  when in "Amend" mode, and removing staged changes.  This behavior has been
  changed to always checkout from the index, which avoids data loss.
  (`#947 <https://github.com/git-cola/git-cola/issues/947>`_)

* `git cola` has been updated to work with newer versions of `gnome-terminal`
  and no longer shell-quotes its arguments when launching `gnome-terminal`.
  The `cola.terminalshellquote` configuration variable can be set to `true` to
  get the old behavior, or to handle other terminals that take the command to run
  as a single string instead of as arguments to `execv()`.
  (`#935 <https://github.com/git-cola/git-cola/pull/935>`_)

* `git dag` now properly handles arbitrary input on Python3.
  Previously, an exception would be raised when entering `--grep=xxx` where
  `xxx` is a quoted string with a missing end-quote.
  (`#941 <https://github.com/git-cola/git-cola/pull/941>`_)

Development
-----------
* The contribution guidelines for contributors has been updated to mention
  how to regenerate the `*.mo` message files.
  (`#934 <https://github.com/git-cola/git-cola/pull/934>`_)


.. _v3.3:

v3.3
====

Usability, bells and whistles
-----------------------------
* `git dag` improved how it renders parent commits.
  (`#921 <https://github.com/git-cola/git-cola/pull/921>`_)

* The `Branches` widget now checks out branches when double-clicked.
  (`#920 <https://github.com/git-cola/git-cola/pull/920>`_)

* The new `Submodules` widget makes it easy to interact with submodules.
  Additionally, submodules can now be updated using the `Status` widget.
  (`#916 <https://github.com/git-cola/git-cola/pull/916>`_)

* Updated Japanese translation.
  (`#914 <https://github.com/git-cola/git-cola/pull/914>`_)

* The "Open Terminal" action now launches a Git Bash shell on Windows.
  (`#913 <https://github.com/git-cola/git-cola/pull/913>`_)

* New menu actions for updating all submodules.
  (`#911 <https://github.com/git-cola/git-cola/pull/911>`_)

* The status widget can now update submodules.
  (`#911 <https://github.com/git-cola/git-cola/pull/911>`_)

* The "Apply Patch" `git cola am` dialog now includes a diff viewer
  to display the contents of the selected patch.

* The "Alt+D" diffstat hotkey now selects the staged/modified/etc.
  header in the Status widget, which shows the totality of everything
  that will be committed.
  (`#771 <https://github.com/git-cola/git-cola/issues/771>`_)

* Running "Launch Editor" from the diff editor now opens the editor at the
  current line.
  (`#898 <https://github.com/git-cola/git-cola/pull/898>`_)

* The textwidth and tabwidth configuration values can now be set
  per-repository, rather than globally only.

* Text entry widgets switched to using a block cursor in `v3.2`.
  This has been reverted to the original line cursor for consistency
  with other applications and user expectations.
  (`#889 <https://github.com/git-cola/git-cola/issues/889>`_)

* The "edit at line" feature, used by the "Grep" tool, now supports
  the Sublime text editor.
  (`#894 <https://github.com/git-cola/git-cola/pull/894>`_)

Fixes
-----
* Launching external programs has been improved on Windows.
  (`#925 <https://github.com/git-cola/git-cola/pull/925>`_)

* Improve compatibility when using PySide2.
  (`#912 <https://github.com/git-cola/git-cola/pull/912>`_)

* The Diff Editor was not honoring the configured tab width on startup.
  (`#900 <https://github.com/git-cola/git-cola/issues/900>`_)

* The "Delete Files" feature was creating an unreadable display when
  many files were selected.  Word-wrap the list of files so that the
  display stays within a sensible size.
  (`#895 <https://github.com/git-cola/git-cola/issues/895>`_)

* Spelling and grammar fixes.
  (`#915 <https://github.com/git-cola/git-cola/pull/915>`_)
  (`#891 <https://github.com/git-cola/git-cola/pull/891>`_)

Development
-----------
* The logo was run through `tidy` to give it a consistent style.
  Some technical issues with the logo were improved.
  (`#877 <https://github.com/git-cola/git-cola/issues/877>`_)

* The entire codebase is now checked by `flake8`, rather than just
  the module and test directories.  This catches things like
  the pynsist installer scripts.
  (`#884 <https://github.com/git-cola/git-cola/issues/884>`_)
  (`#882 <https://github.com/git-cola/git-cola/issues/882>`_)
  (`#879 <https://github.com/git-cola/git-cola/pull/879>`_)

Packaging
---------
* The vendored `qtpy` library was updated to `v1.6`.

* The Windows installer's wrapper scripts were missing an import.
  (`#878 <https://github.com/git-cola/git-cola/issues/878>`_)


.. _v3.2:

v3.2
====

Usability, bells and whistles
-----------------------------
* The `git cola dag` DAG window now supports `git revert`.
  (`#843 <https://github.com/git-cola/git-cola/issues/843>`_)

* `git stash pop` is now supported by the stash dialog.
  (`#844 <https://github.com/git-cola/git-cola/issues/844>`_)

* The status widget now ensures that each item is visible when selection
  changes.  Previously, if you scrolled to the right to see the name of
  a long filename, and then selected a short filename above it, the widget
  may not have shown the short filename in the viewport.  We now ensure
  that the filenames are visible when the selection changes.
  (`#828 <https://github.com/git-cola/git-cola/pull/828>`_)

* The `git xbase` rebase editor no longer displays an error when
  cancelling an interactive rebase.
  (`#814 <https://github.com/git-cola/git-cola/issues/814>`_)

* The dialog shown when renaming remotes has been simplified.
  (`#840 <https://github.com/git-cola/git-cola/pull/840>`_)
  (`#838 <https://github.com/git-cola/git-cola/issues/838>`_)

* The help dialog in the `git-xbase` Rebase editor is now scrollable.
  (`#855 <https://github.com/git-cola/git-cola/issues/855>`_)

Translations
------------
* Updated Brazilian translation.
  (`#845 <https://github.com/git-cola/git-cola/pull/845>`_)

* Updated Czech translation.
  (`#854 <https://github.com/git-cola/git-cola/pull/854>`_)
  (`#853 <https://github.com/git-cola/git-cola/pull/853>`_)
  (`#835 <https://github.com/git-cola/git-cola/pull/835>`_)
  (`#813 <https://github.com/git-cola/git-cola/pull/813>`_)

* Update Spanish translation.
  (`#862 <https://github.com/git-cola/git-cola/pull/862>`_)
  (`#867 <https://github.com/git-cola/git-cola/pull/867>`_)

Packaging
---------
* The original `#!/usr/bin/env python` shebang lines can now be
  retained by passing `USE_ENV_PYTHON=1` to `make` when installing.
  (`#850 <https://github.com/git-cola/git-cola/issues/850>`_)

* The Makefile is now resilient to DESTDIR and prefix containing whitespace.
  (`#858 <https://github.com/git-cola/git-cola/pull/858>`_)

* The vendored `qtpy` library was updated to `v1.4.2`.

* `python3-distutils` is needed to build cola on Debian.
  (`#837 <https://github.com/git-cola/git-cola/issues/837>`_)

Fixes
-----
* The "C" key no longer closes the message dialogs, for example the
  one that is shown when a commit fails its pre-commit hooks.
  This allows "Ctrl+C" copy to work, rather than closing the dialog.
  (`#734 <https://github.com/git-cola/git-cola/issues/734>`_)

* Dock widgets sizes are now properly saved and restored when the main
  window is maximized.
  (`#848 <https://github.com/git-cola/git-cola/issues/848>`_)

* The spellcheck feature was broken under Python3.
  (`#857 <https://github.com/git-cola/git-cola/issues/857>`_)

* A regression when saving stashes was fixed.
  (`#847 <https://github.com/git-cola/git-cola/issues/847>`_)

* Diffing image files was not updating the available context menus,
  which prevented the "Stage" action from being present in the menu.
  (`#841 <https://github.com/git-cola/git-cola/issues/841>`_)

* `git cola` now detects when `git lfs uninstall` has been run.  This allows
  you to re-initialize "Git LFS" in an existing repository where it had been
  previously uninstalled.
  (`#842 <https://github.com/git-cola/git-cola/issues/842>`_)

* Custom color values that did not contain any hexadecimal digits in the
  `a-f` range were being converted into integers by the config reader.  This
  then caused the configured colors to be ignored.

  These color values are now interpreted correctly.  Additionally, color
  values can now use an optional HTML-like `#` prefix.

  Example `.gitconfig` snippet::

    [cola "color"]
        text = "#0a0303"

  (`#836 <https://github.com/git-cola/git-cola/pull/836>`_)
  (`#849 <https://github.com/git-cola/git-cola/issues/849>`_)

* We now display an error message graphically when `Git` is not installed.
  Previously, the message went to stderr only.
  (`#830 <https://github.com/git-cola/git-cola/issues/830>`_)

* Changing diff options was causing resulting in an exception.
  (`#833 <https://github.com/git-cola/git-cola/issues/833>`_)
  (`#834 <https://github.com/git-cola/git-cola/pull/834>`_)

* The DAG window now updates itself when branches and tags are created.
  (`#814 <https://github.com/git-cola/git-cola/issues/814>`_)

* The user's `$PATH` environment variable can now contain UTF-8
  encoded paths.  Previously, launching external commands could
  lead to errors.
  (`#807 <https://github.com/git-cola/git-cola/issues/807>`_)

* Git Cola development sandboxes can now be stored on UTF-8 encoded
  filesystem paths.  Previously, the interactive rebase feature
  could be broken when running in that environment.
  (`#825 <https://github.com/git-cola/git-cola/issues/825>`_)

* The log window now uses an ISO-8601 time stamp, which
  avoids localized output in the log window.
  (`#817 <https://github.com/git-cola/git-cola/issues/817>`_)

Development
-----------
* The code base has been thoroughly sanitized using `pylint`, and
  Travis is now running pylint over the entire project.

* Miscellaneous improvements and code improvements.
  (`#874 <https://github.com/git-cola/git-cola/issues/874>`_)


.. _v3.1:

v3.1
====

Usability, bells and whistles
-----------------------------
* The "Browser" widget learned to rename files using "git mv".
  (`#239 <https://github.com/git-cola/git-cola/issues/239>`_)

* The "Diff" widget learned to diff images.  Side-by-side and pixel diff
  modes allow you to inspect changes to common images formats.
  (`#444 <https://github.com/git-cola/git-cola/issues/444>`_)
  (`#803 <https://github.com/git-cola/git-cola/pull/803>`_)

* Git LFS and Git Annex are natively supported by the image diff viewer.

* Git Annex operations are now included. `git annex init` can be performed on
  repositories, and `git annex add` can be run on untracked files from the
  status widget.  Install `git-annex` to activate this feature.

* Git LFS operations are now included. `git lfs install` can be performed on
  repositories, and `git lfs track` can be run on untracked files from the
  status widget.  Install `git-lfs` to activate this feature.

* The "Stash" tool learned to stash staged changes only.  Select the
  "Stage Index" option and only staged changes will be stashed away.
  (`#413 <https://github.com/git-cola/git-cola/issues/413>`_)

* The "Stash" tool learned to use vim-like navigation keyboard shortcuts,
  shows error messages when things go wrong, and now saves the "Stash Index"
  and "Keep Index" options across sessions.

* The Edit menu's "Copy" and "Select All" actions now forward to either the
  diff, status, recent, or favorites widgets, based on which widget has focus.

* The "File" and "Edit" menu can now be activated using `Alt + {F,E}` hotkeys.
  (`#759 <https://github.com/git-cola/git-cola/issues/759>`_)

* It was easy to accidentally trigger the first action in the `Status` tool's
  context menu when using a quick right-click to bring up the menu.
  A short sub-second delay was added to ensure that the top-most action is not
  triggered unless enough time has passed.  This prevents accidental
  activation of the first item (typically "Stage" or "Unstage") without
  burdening common use cases.
  (`#755 <https://github.com/git-cola/git-cola/pull/755>`_)
  (`#643 <https://github.com/git-cola/git-cola/issues/643>`_)

* The "Ctrl+S" hotkey now works for the header items in the Status tool.
  Selected the "Modified" header item and activating the "Stage" hotkey,
  for example, will stage all modified files.  This works for the "Staged",
  "Modified", and "Untracked" headers.  This is not enabled for the
  "Unmerged" header by design.
  (`#772 <https://github.com/git-cola/git-cola/issues/772>`_)

* The list of "Recent" repositories previously capped the number of
  repositories shown to 8 repositories.  This can be set to a higher
  value by setting the `cola.maxrecent` configuration variable.
  (`#752 <https://github.com/git-cola/git-cola/issues/752>`_)

* The "Create Branch" dialog now prevents invalid branch names.
  (`#765 <https://github.com/git-cola/git-cola/issues/765>`_)

* Updated Turkish translation.
  (`#756 <https://github.com/git-cola/git-cola/pull/756>`_)

* Updated Ukrainian translation.
  (`#753 <https://github.com/git-cola/git-cola/pull/753>`_)

* Updated German translation.
  (`#802 <https://github.com/git-cola/git-cola/pull/802>`_)

* Updated Czech translation
  (`#792 <https://github.com/git-cola/git-cola/pull/792>`_)
  (`#806 <https://github.com/git-cola/git-cola/pull/806>`_)

* The window title can be configured to not display the absolute path of the
  repository.
  (`#775 <https://github.com/git-cola/git-cola/issues/775>`_)

* The "Edit Remotes" editor learned to edit remote URLS.

* Bare repositories can now be created by selecting the
  "New Bare Repository..." action from the `File` menu.

* The "Branches" widget learned to configure upstream branches.

* A new `git cola clone` sub-command was added for cloning repositories.

Packaging
---------
* The vendored `qtpy` library was updated to `v1.3.1`.

* The macOS installation was made simpler for better compatibility with
  Homebrew.
  (`#636 <https://github.com/git-cola/git-cola/issues/636>`_)

* The Windows installer is now much simpler.  Git Cola now bundles
  Python and PyQt5, so users need only install the "Git for Windows"
  and "Git Cola" installers to get things working.

Fixes
-----
* Uninitialized difftool errors will now be displayed graphically.
  They were previously going to the shell.
  (`#457 <https://github.com/git-cola/git-cola/issues/457>`_)

* Translations marked "fuzzy" will no longer be used when translating strings.
  (`#782 <https://github.com/git-cola/git-cola/issues/782>`_)

* Deleted unmerged files will now correctly use a deleted icon.
  (`#479 <https://github.com/git-cola/git-cola/issues/479>`_)

* The `Ctrl+C` "Copy" hotkey on the diff viewer has been fixed.
  (`#767 <https://github.com/git-cola/git-cola/issues/767>`_)

* The "Create Tag" dialog did not correctly handle the case when a signed
  tag is requested, but no message is provided, and the user chooses to
  create a non-annotated tag instead.  This convenience fallback will now
  properly create an unsigned, non-annotated tag.
  (`#696 <https://github.com/git-cola/git-cola/issues/696>`_)

* `.gitconfig` and `.git/config` values editable by the Preferences dialog
  (aka `git cola config`) will now get unset when set to an empty value.
  For example, setting a different `user.email` in the current repository,
  followed by a subsequent emptying of that field, would previously result in
  an empty string getting stored in the config.  This has been fixed so that
  the value will now get unset in the config instead.
  (`#406 <https://github.com/git-cola/git-cola/issues/406>`_)

* Spelling and typo fixes.
  (`#748 <https://github.com/git-cola/git-cola/pull/748>`_)

* `core.commentChar` is now honored when set in the local repository
  `.git/config`.
  (`#766 <https://github.com/git-cola/git-cola/issues/766>`_)

* The log window was using a format string that did not display
  correctly in all locales.  A locale-aware format is now used.
  (`#800 <https://github.com/git-cola/git-cola/pull/800>`_)

* The dialog displayed when prompting for a reference could sometimes
  lose focus.
  (`#804 <https://github.com/git-cola/git-cola/pull/804>`_)


.. _v3.0:

v3.0
====

Usability, bells and whistles
-----------------------------
* Updated Simplified Chinese translation.
  (`#726 <https://github.com/git-cola/git-cola/pull/726>`_)

* Updated Ukrainian translation.
  (`#723 <https://github.com/git-cola/git-cola/pull/723>`_)

* New Czech translation.
  (`#736 <https://github.com/git-cola/git-cola/pull/736>`_)
  (`#737 <https://github.com/git-cola/git-cola/pull/737>`_)
  (`#740 <https://github.com/git-cola/git-cola/pull/740>`_)
  (`#743 <https://github.com/git-cola/git-cola/pull/743>`_)

* The "name" field in the "Create Tag" dialog now includes autocompletion,
  which makes it easy to see which tags currently exist.

* `git cola` now has configurable toolbars.  Use the `View > Add toolbar`
  menu item to add a toolbar.

* Setting `cola.expandtab` to `true` will now expand tabs into spaces
  in the commit message editor.  The number of spaces to insert is determined
  by consulting `cola.tabwidth`, which defaults to `8`.

* The "Copy SHA-1" hotkey is now `Alt + Ctrl + C`, to avoid clobbering the
  ability to copy text from the DAG window.
  (`#705 <https://github.com/git-cola/git-cola/pull/705>`_)

* The "Prepare Commit Message" action can now be invoked via the
  `Ctrl+Shift+Return` shortcut.
  (`#707 <https://github.com/git-cola/git-cola/pull/707>`_)

* The `Branches` pane now has a filter field that highlights branches whose
  names match the string entered into its text field.
  (`#713 <https://github.com/git-cola/git-cola/pull/713>`_)

* Actions that are triggered in response to button presses were being
  triggered when the button was pressed, rather than when it was released,
  which was a usability flaw.  All buttons now respond when clicked
  rather than when pressed.
  (`#715 <https://github.com/git-cola/git-cola/pull/715>`_)

* The DAG window will now only refresh when object IDs change.
  Previously, the DAG would redraw itself in response to inotify events,
  such as filesystem operations, which was disruptive when inspecting a large
  diff in its diff viewer.  The DAG will now only redraw when the object IDs
  corresponding to its query input changes.  Furthermore, when redrawing, the
  scrollbar positions are retained to minimize disruption to the viewport
  contents.
  (`#620 <https://github.com/git-cola/git-cola/issues/620>`_)
  (`#724 <https://github.com/git-cola/git-cola/issues/724>`_)

* The "About" dialog now includes the SHA-1 where Git Cola was built.
  (`#530 <https://github.com/git-cola/git-cola/issues/530>`_)

* The "Status" widget now has "Copy Leading Path to Clipboard" and
  "Copy Basename to Clipboard" actions.
  (`#435 <https://github.com/git-cola/git-cola/issues/435>`_)
  (`#436 <https://github.com/git-cola/git-cola/issues/436>`_)

* The "Status" widget now supports custom "Copy xxx to Clipboard" actions.
  (`#437 <https://github.com/git-cola/git-cola/issues/437>`_)

* The main menu now has an "Edit" menu.
  (`#725 <https://github.com/git-cola/git-cola/issues/725>`_)

* `git dag` learned to checkout commits into a detached HEAD state.
  (`#698 <https://github.com/git-cola/git-cola/issues/698>`_)

* The `status` widget's context menus now omit actions selection-dependent
  actions when no file is selected.
  (`#731 <https://github.com/git-cola/git-cola/pull/731>`_)

* The startup dialog now focuses the repository list so that repositories
  can be selected with the keyboard without mouse intervention.
  (`#741 <https://github.com/git-cola/git-cola/issues/741>`_)

Fixes
-----
* `git dag` now prevents nodes from overlapping in more situations.
  (`#689 <https://github.com/git-cola/git-cola/pull/689>`_)

* Adding untracked Git submodule repo directories previously ran
  `git add submodule/` but we now call `git add submodule` without
  the trailing slash (`/`) to avoid staging files that belong to the
  submodule (which is possibly a `git` bug).  By working around the
  buggy behavior we allow users to recover by issuing the appropriate
  `git submodule add` command to properly register the submodule.
  (`#681 <https://github.com/git-cola/git-cola/pull/681>`_)

* We now avoid `git for-each-ref --sort=version:refname` on versions
  of `git` older than `v2.7.0`.  Previously we only avoided it for
  versions older than `v2.0.0`, which was a mistake.
  (`#686 <https://github.com/git-cola/git-cola/pull/686>`_)

* The error message displayed when `git` is not installed has been fixed.
  (`#686 <https://github.com/git-cola/git-cola/pull/686>`_)

* Adding new remotes was silently broken.
  (`#684 <https://github.com/git-cola/git-cola/issues/684>`_)
  (`#685 <https://github.com/git-cola/git-cola/pull/685>`_)

* The repo selection dialog had errors during startup when the
  `cola.refreshonfocus` feature was enabled, as reported on Ubuntu 16.04.
  (`#690 <https://github.com/git-cola/git-cola/issues/690>`_)

* Restored support for PyQt 4.6 (Centos 6.8)
  (`#692 <https://github.com/git-cola/git-cola/issues/692>`_)

* Switching repositories now resets the "Amend Mode" and other settings
  when switching.
  (`#710 <https://github.com/git-cola/git-cola/issues/710>`_)

* `git rebase` error messages now displayed when rebasing fails or stops
  via the standalone `git cola rebase` front-end.
  (`#721 <https://github.com/git-cola/git-cola/issues/721>`_)

* `git cola` learned to stage broken symlinks.
  (`#727 <https://github.com/git-cola/git-cola/issues/727>`_)

* The "View History" feature in the `Browser` tool was fixed, and now
  disambiguates between refs and paths.
  (`#732 <https://github.com/git-cola/git-cola/issues/732>`_)

* The diff editor now has better support for files with CRLF `\r\n`
  line endings.
  (`#730 <https://github.com/git-cola/git-cola/issues/730>`_)

* `cola.inotify` in a repo-local config is now honored
  when `git cola` is launched from a desktop entry (`git cola --prompt`).
  (`#695 <https://github.com/git-cola/git-cola/issues/695>`_)


.. _v2.11:

v2.11
=====

Usability, bells and whistles
-----------------------------
* New Ukrainian translation.
  (`#670 <https://github.com/git-cola/git-cola/pull/670>`_)
  (`#672 <https://github.com/git-cola/git-cola/pull/672>`_)

* New and improved French translations.

* The new `Branches` widget makes it easier to checkout, merge, push,
  and pull branches from a single interface.

* `git cola` now includes a dark icon theme.  The dark icon theme can be
  activated either by setting the `GIT_COLA_ICON_THEME` environment variable
  to `dark`, by configuring `cola.icontheme` to `dark`, or by specifying
  `--icon-theme=dark` on the command line.
  (`#638 <https://github.com/git-cola/git-cola/pull/638>`_)

* Autocompletion was added to the `Fetch`, `Push`, and `Pull` dialogs.

* The commit message editor now remembers the "Spellcheck" setting
  after exiting.
  (`#645 <https://github.com/git-cola/git-cola/pull/645>`_)

* `git dag` now uses an improved algorithm for laying out the graph,
  which avoids collisions under certain graph configurations, and
  avoids overlapping tag with commits.
  (`#648 <https://github.com/git-cola/git-cola/pull/648>`_)
  (`#651 <https://github.com/git-cola/git-cola/pull/651>`_)
  (`#654 <https://github.com/git-cola/git-cola/pull/654>`_)
  (`#656 <https://github.com/git-cola/git-cola/pull/656>`_)
  (`#659 <https://github.com/git-cola/git-cola/pull/659>`_)

* `git dag` now remembers its column sizes across sessions.
  (`#674 <https://github.com/git-cola/git-cola/issues/674>`_)

* `Grep` now shows a preview of the selected file's content in a split window
  below the grep results.

* `Grep` now includes line numbers in the preview pane's output.

* `Edit Remotes` now remembers its window settings after exiting.

* `Diff` now has an option to display line numbers in the editor.
  (`#136 <https://github.com/git-cola/git-cola/issues/136>`_)

* `Amend Last Commit` can now be triggered via the `Commit` menu in addition
  to the commit message editor's options.
  (`#640 <https://github.com/git-cola/git-cola/issues/640>`_)

* The `File Browser` tool was made much faster and can now operate on
  much larger repositories.
  (`#499 <https://github.com/git-cola/git-cola/issues/499>`_)

* A new "turbo" mode was added that allows you to opt-out of operations
  that can slow `git cola` on large repositories.  The turbo mode is
  enabled by configuring `git config cola.turbo true`.  Turbo mode
  disables the background loading of Git commit messages and other
  details in the `File Browser` widget.

* A new GitIgnore dialog allows adding custom gitignore patterns.
  (`#653 <https://github.com/git-cola/git-cola/pull/653>`_)

* The spellchecker in `git cola` can now use an additional dictionary
  by configuring `cola.dictionary` to the path to a file containing
  a newline-separated list of words.
  (`#663 <https://github.com/git-cola/git-cola/issues/663>`_)

* The stash, export patches, diff, and gitignore dialogs now remember
  their window sizes.

* A new `git cola recent` sub-command was added for finding recently
  edited files.

* The `Fetch` dialog now allows pruning remote branches.
  (`#639 <https://github.com/git-cola/git-cola/issues/639>`_)
  (`#680 <https://github.com/git-cola/git-cola/pull/680>`_)

Fixes
-----
* `git cola`'s spellchecker now supports the new `dict-common` filesystem
  layout, and prefers the `/usr/share/dict/cracklib-small` file over the
  `/usr/share/dict/words` provided on older distributions.
  This makes the spellchecker compatible with Arch, which does not provide
  a `words` symlink like Debian.
  (`#663 <https://github.com/git-cola/git-cola/issues/663>`_)

* Properly handle the case where an existing file is untracked using
  the File Browser.

* Fix a quirk where the "Create Branch" dialog sometimes required clicking
  twice on the radio buttons.
  (`#662 <https://github.com/git-cola/git-cola/pull/662>`_)

* Fixed a focus issue to ensure that "Push", "Fetch", and "Pull" can
  be executed with the press of a single enter key after being shown.
  (`#661 <https://github.com/git-cola/git-cola/issues/661>`_)

* Committing is now allowed in when resolving a merge results in no
  changes.  This state was previously prevented by the commit message editor,
  which prevented users from resolving merges that result in no changes.
  (`#679 <https://github.com/git-cola/git-cola/pull/679>`_)

* The filesystem monitor would sometimes emit backtraces when directories
  are modified.  This has been fixed.
  (`bz #1438522 <https://bugzilla.redhat.com/show_bug.cgi?id=1438522>`_)

* Absolute paths are now returned when querying for `.git`-relative paths
  from within a submodule, which uses `.git`-files.
  This fixes launching `git cola` from within a subdirectory of a submodule.
  (`#675 <https://github.com/git-cola/git-cola/pull/675>`_)


.. _v2.10:

v2.10
=====

Usability, bells and whistles
-----------------------------
* `git cola` can now invoke the `.git/hooks/cola-prepare-commit-msg`
  hook to update the commit message.  This hook takes the same parameters
  as Git's `prepare-commit-message` hook.  The default path to this hook
  can be overridden by setting the `cola.prepareCommitMessageHook`
  configuration variable.
  (`Documentation <https://git-cola.readthedocs.io/en/latest/git-cola.html#prepare-commit-message>`_)

* `git cola diff` (and the corresponding `Diff` menu actions) can now
  launch difftool with the standard `Ctrl+D` hotkey.  The `Ctrl+E` hotkey was
  also added for launching an editor.

Translations
------------
* Traditional Chinese (Taiwan) translation updates.

Fixes
-----
* `git cola` now works when installed in non-ASCII, UTF-8-encoded paths.
  (`#629 <https://github.com/git-cola/git-cola/issues/629>`_)

* Styling issues that caused black backgrounds in various widgets when using
  PyQt5 on Mac OS X have been fixed.
  (`#624 <https://github.com/git-cola/git-cola/issues/624>`_)

* The "Open Recent" menu action was broken and has been fixed.
  (`#634 <https://github.com/git-cola/git-cola/issues/634>`_)

* Exiting `git cola` with a maximized main window would hang when reopened
  on Linux.
  (`#641 <https://github.com/git-cola/git-cola/issues/641>`_)

Packaging
---------
* `appdata.xml` files are now provided at
  `share/appdata/git-cola.xml` and `share/appdata/git-dag.xml`
  for use by the Linux software gallery.
  (`#627 <https://github.com/git-cola/git-cola/pull/627>`_)
  (`Appdata <https://people.freedesktop.org/~hughsient/appdata/>`_)


.. _v2.9.1:

v2.9.1
======

Fixes
-----
* The "Open Recent" menu was updated to new bookmarks format.
  (`#628 <https://github.com/git-cola/git-cola/issues/628>`_)


.. _v2.9:

v2.9
====

Usability, bells and whistles
-----------------------------
* New Polish translation thanks to Łukasz Wojniłowicz
  (`#598 <https://github.com/git-cola/git-cola/pull/598>`_)

* The `Bypass Commit Hooks` feature now disables itself automatically
  when a new commit is created.  The new behavior turns the option into a
  single-use flag, which helps prevent users from accidentally leaving it
  active longer than intended.
  (`#595 <https://github.com/git-cola/git-cola/pull/595>`_)

* `git dag` learned to launch an external diff viewer on selected commits.
  The standard `Ctrl+D` shortcut can be used to view diffs.
  (`#468 <https://github.com/git-cola/git-cola/issues/468>`_)

* `git dag` learned to launch directory diffs via `git difftool --dir-diff`.
  The `Ctrl+Shift+D` shortcut launches difftool in directory-diff mode.
  (`#468 <https://github.com/git-cola/git-cola/issues/468>`_)

* Items in the "Favorites" list can now be renamed, which makes it
  easier to differentiate between several checkouts of the same repository.
  (`#599 <https://github.com/git-cola/git-cola/issues/599>`_)
  (`#601 <https://github.com/git-cola/git-cola/pull/601>`_)

* The startup screen now includes a logo and `git cola` version information.
  (`#526 <https://github.com/git-cola/git-cola/issues/526>`_)

* The `About` page was revamped to contain multiple tabs.  A new tab was added
  that provides details about `git cola`''s dependencies.  New tabs were also
  added for giving credit to `git cola`'s authors and translators.

* The `About` page can now be accessed via `git cola about`.

* The "Fast-forward only" and "No fast-forward" options supported by
  `git pull` are now accessible via `git cola pull`.

* Doing a forced push no longer requires selecting the remote branch.
  (`#618 <https://github.com/git-cola/git-cola/pull/618>`_)

* `git cola push` now has an option to suppress the prompt that is shown
  when pushing would create new remote branches.
  (`#605 <https://github.com/git-cola/git-cola/issues/605>`_)

* `git dag` now shows commit messages in a more readable color.
  (`#574 <https://github.com/git-cola/git-cola/issues/574>`_)

* `git cola browse` and the `status` widget learned to launch the OS-specified
  default action for a file.  When used on directories via `git cola browse`,
  or when "Open Parent Directory" is used on files, the OS-specified
  file browser will typically be used.

* `git cola browse` and the `status` widget learned to launch terminals.

Fixes
-----
* `git cola browse` was not updating when expanding items.
  (`#588 <https://github.com/git-cola/git-cola/issues/588>`_)

* Typo fixes in comments, naming, and strings have been applied.
  (`#593 <https://github.com/git-cola/git-cola/pull/593>`_)

* The inotify and win32 filesystem monitoring no longer refreshes
  when updates are made to ignored files.
  (`#517 <https://github.com/git-cola/git-cola/issues/517>`_)
  (`#516 <https://github.com/git-cola/git-cola/issues/516>`_)

* The `Refresh` button on the actions panel no longer raises an
  exception when using PyQt5.
  (`#604 <https://github.com/git-cola/git-cola/issues/604>`_)

* Fixed a typo in the inotify back-end that is triggered when files are removed.
  (`#607 <https://github.com/git-cola/git-cola/issues/607>`_)

* Fixed a typo when recovering from a failed attempt to open a repository.
  (`#606 <https://github.com/git-cola/git-cola/issues/606>`_)

* `git dag` now properly updates itself when launched from the menu bar.
  (`#613 <https://github.com/git-cola/git-cola/pull/613>`_)

* If git-cola is invoked on Windows using `start pythonw git-cola`,
  a console window will briefly flash on the screen each time
  `git cola` invokes `git`.  The console window is now suppressed.

* We now avoid some problematic Popen flags on Windows which were
  breaking the `git rebase` feature on Windows.

* The `Save` button in `git dag`'s "Grab File..." feature now properly
  prompts for a filename when saving files.
  (`#617 <https://github.com/git-cola/git-cola/pull/617>`_)

Development
-----------
* The `qtpy` symlink in the source tree has been removed to allow for easier
  development on Windows.
  (`#626 <https://github.com/git-cola/git-cola/issues/626>`_)


.. _v2.8:

v2.8
====

Usability, bells and whistles
-----------------------------
* `git cola push` learned to configure upstream branches.
  (`#563 <https://github.com/git-cola/git-cola/issues/563>`_)

Fixes
-----
* The diffstat view is now properly updated when notifications are
  received via inotify filesystem monitoring.
  (`#577 <https://github.com/git-cola/git-cola/issues/577>`_)

* Python3 with PyQt5 had a bug that prevented `git cola` from starting.
  (`#589 <https://github.com/git-cola/git-cola/pull/589>`_)


.. _v2.7:

v2.7
====

Fixes
-----

* When repositories stored in non-ASCII, UTF-8-encoded filesystem paths
  were operated upon with `LC_ALL=C` set in the environment, Unicode errors
  would occur when using `python2`.  `git cola` was made more robust and will
  now operate correctly within this environment.
  (`#581 <https://github.com/git-cola/git-cola/issues/581>`_)

* Support for the `GIT_WORK_TREE` environment variable was fixed.
  (`#582 <https://github.com/git-cola/git-cola/pull/582>`_)

Development
-----------

* The `unittest.mock` module is now used instead of the original `mock` module
  when running the `git cola` test suite using Python3.
  (`#569 <https://github.com/git-cola/git-cola/issues/569>`_)

Packaging
---------

* `git cola` is now compatible with *PyQt5*, *PyQt4*, and *Pyside*.
  `git cola` previously supported *PyQt4* only, but will now use whichever
  library is available.  Users are not required to upgrade at this time,
  but *PyQt5* support can be enabled anytime by making its python
  modules available.
  (`#232 <https://github.com/git-cola/git-cola/issues/232>`_)

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

v2.6
====

Usability, bells and whistles
-----------------------------

* A new "Reset" sub-menu provides access to running "git reset --mixed"
  when resetting branch heads and "git reset  --merge" when resetting
  worktrees.
  (`#542 <https://github.com/git-cola/git-cola/issues/542>`_)

* `git cola` now supports linked worktrees, i.e. worktrees created by
  `git worktree`.
  (`#554 <https://github.com/git-cola/git-cola/issues/554>`_)

Fixes
-----

* Diff highlighting is now robust to the user having
  diff.supressBlankEmpty=true in their git config.
  (`#541 <https://github.com/git-cola/git-cola/issues/541>`_)

* The filesystem monitor now properly handles repositories that use
  `.git`-files, e.g. when using submodules.
  (`#545 <https://github.com/git-cola/git-cola/issues/545>`_)
  (`#546 <https://github.com/git-cola/git-cola/pulls/546>`_)

* Per-repository git configuration is now properly detected when launching
  `git cola` from an application launcher.
  (`#548 <https://github.com/git-cola/git-cola/issues/548>`_)

* `git cola` now cleans up after itself immediately to avoid leaving behind
  empty `/tmp/git-cola-XXXXXX` directories when the user uses `Ctrl+C`
  to quit the app.
  (`#566 <https://github.com/git-cola/git-cola/issues/566>`_)

Packaging
---------

* It is now possible to install `git cola` to and from UTF-8-encoded filesystem
  paths.  Previously, Python's stdlib would throw an encoding error during
  installation.  We workaround the stdlib by forcing python2 to use UTF-8,
  thus fixing assumptions in the stdlib library code.
  (`#551 <https://github.com/git-cola/git-cola/issues/551>`_)


.. _v2.5:

v2.5
====

Usability, bells and whistles
-----------------------------

* The icon for untracked files was adjusted to better differentiate
  between files and the "Untracked" header.
  (`#509 <https://github.com/git-cola/git-cola/issues/509>`_)

* Ctrl+O was added as a hotkey for opening repositories.
  (`#507 <https://github.com/git-cola/git-cola/pull/507>`_)

* `git dag` now uses consistent edge colors across updates.
  (`#512 <https://github.com/git-cola/git-cola/issues/512>`_)

* `git cola`'s Bookmarks widget can now be used to set a "Default Repository".
  Under the hood, we set the `cola.defaultrepo` configuration variable.
  The default repository is used whenever `git cola` is launched outside of
  a Git repository.  When unset, or when set to a bogus value, `git cola`
  will prompt for a repository, as it previously did.
  (`#513 <https://github.com/git-cola/git-cola/issues/513>`_)

* `git cola`'s Russian and Spanish translations were improved
  thanks to Vaiz and Zeioth.
  (`#514 <https://github.com/git-cola/git-cola/pull/514>`_)
  (`#515 <https://github.com/git-cola/git-cola/pull/515>`_)
  (`#523 <https://github.com/git-cola/git-cola/pull/523>`_)

* `git cola` was translated to Turkish thanks to Barış ÇELİK.
  (`#520 <https://github.com/git-cola/git-cola/pull/520>`_)

* The status view now supports launching `git gui blame`.  It can be
  configured to use a different command by setting `cola.blameviewer`.
  (`#521 <https://github.com/git-cola/git-cola/pull/521>`_)

* `git dag` now allows selecting non-contiguous ranges in the log widget.
  (`#468 <https://github.com/git-cola/git-cola/issues/468>`_)

* Any font can now be chosen for the diff editor, not just mono-space fonts.
  (`#525 <https://github.com/git-cola/git-cola/issues/525>`_)

Fixes
-----

* `xfce4-terminal` and `gnome-terminal` are now supported when launching
  `git mergetool` to resolve merges.  These terminals require that the command
  to execute is shell-quoted and passed as a single string argument to `-e`
  rather than as additional command line arguments.
  (`#524 <https://github.com/git-cola/git-cola/issues/524>`_)

* Fixed a Unicode problem when formatting the error message that is shown
  when `gitk` is not installed.  We now handle Unicode data in tracebacks
  generated by python itself.
  (`#528 <https://github.com/git-cola/git-cola/issues/528>`_)

* The `New repository` feature was fixed.
  (`#533 <https://github.com/git-cola/git-cola/pull/533>`_)

* We now use omit the extended description when creating "fixup!" commits,
  for consistency with the Git CLI.  We now include only the one-line summary
  in the final commit message.
  (`#522 <https://github.com/git-cola/git-cola/issues/522>`_)


.. _v2.4:

v2.4
====

Usability, bells and whistles
-----------------------------

* The user interface is now HiDPI-capable. Git Cola now uses SVG
  icons, and its interface can be scaled by setting the `GIT_COLA_SCALE`
  environment variable.

* `git dag` now supports the standard editor, difftool, and history hotkeys.
  It is now possible to invoke these actions from file widget's context
  menu and through the standard hotkeys.
  (`#473 <https://github.com/git-cola/git-cola/pull/473>`_)

* The `Status` tool also learned about the history hotkey.
  Additionally, the `Alt + {J,K}` aliases are also supported in the `Status`
  tool for consistency with the other tools where the non-Alt hotkeys are not
  available.
  (`#488 <https://github.com/git-cola/git-cola/pull/488>`_)

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
  (`#390 <https://github.com/git-cola/git-cola/issues/390>`_)

* The "create branch" and "create tag" dialogs now save and restore their
  window settings.

* The "status" widget can now be configured to use a bold font with a darker
  background for the header items.
  (`#506 <https://github.com/git-cola/git-cola/pull/506>`_)

* The "status" widget now remembers its horizontal scrollbar position across
  updates.  This is helpful when working on projects with long paths.
  (`#494 <https://github.com/git-cola/git-cola/issues/494>`_)

Fixes
-----

* When using *Git for Windows*, a `git` window would appear
  when running *Windows 8*.  We now pass additional flags to
  `subprocess.Popen` to prevent a `git` window from appearing.
  (`#477 <https://github.com/git-cola/git-cola/issues/477>`_)
  (`#486 <https://github.com/git-cola/git-cola/pull/486>`_)

* Launching difftool with `.PY` in `$PATHEXT` on Windows was fixed.
  (`#492 <https://github.com/git-cola/git-cola/issues/492>`_)

* Creating a local branch tracking a remote branch that contains
  slashes in its name is now properly handled.
  (`#496 <https://github.com/git-cola/git-cola/issues/496>`_)

* The "Browse Other Branch" feature was broken by Python3, and is now fixed.
  (`#501 <https://github.com/git-cola/git-cola/issues/501>`_)

* We now avoid `long` for better Python3 compatibility.
  (`#502 <https://github.com/git-cola/git-cola/issues/502>`_)

* We now use Git's default merge message when merging branches.
  (`#508 <https://github.com/git-cola/git-cola/issues/508>`_)

* Miscellaneous fixes
  (`#485 <https://github.com/git-cola/git-cola/pull/485>`_)

Packaging
---------

* git-cola's documentation no longer uses an inter-sphinx link mapping
  to docs.python.org.  This fixes warnings when building RPMs using koji,
  where network access is prevented.

  https://bugzilla.redhat.com/show_bug.cgi?id=1231812


.. _v2.3:

v2.3
====

Usability, bells and whistles
-----------------------------

* The Interactive Rebase feature now works on Windows!
  (`#463 <https://github.com/git-cola/git-cola/issues/463>`_)

* The `diff` editor now understands vim-style `hjkl` navigation hotkeys.
  (`#476 <https://github.com/git-cola/git-cola/issues/476>`_)

* `Alt + {J,K}` navigation hotkeys were added to allow changing to the
  next/previous file from the diff and commit editors.

* The `Rename branch` menu action is now disabled in empty repositories.
  (`#475 <https://github.com/git-cola/git-cola/pull/475>`_)
  (`#459 <https://github.com/git-cola/git-cola/issues/459>`_)

* `git cola` now checks unmerged files for conflict markers before
  staging them.  This feature can be disabled in the preferences.
  (`#464 <https://github.com/git-cola/git-cola/issues/464>`_)

* `git dag` now remembers which commits were selected when refreshing
  so that it can restore the selection afterwards.
  (`#480 <https://github.com/git-cola/git-cola/issues/480>`_)

* "Launch Editor", "Launch Difftool", "Stage/Unstage",
  and "Move Up/Down" hotkeys now work when the commit message
  editor has focus.
  (`#453 <https://github.com/git-cola/git-cola/issues/453>`_)

* The diff editor now supports the `Ctrl+u` hotkey for reverting
  diff hunks and selected lines.

* The `core.commentChar` Git configuration value is now honored.
  Commit messages and rebase instruction sheets will now use
  the configured character for comments.  This allows having
  commit messages that start with `#` when `core.commentChar`
  is configured to its non-default value.
  (`#446 <https://github.com/git-cola/git-cola/issues/446>`_)

Fixes
-----

* Diff syntax highlighting was improved to handle more edge cases
  and false positives.
  (`#467 <https://github.com/git-cola/git-cola/pull/467>`_)

* Setting commands in the interactive rebase editor was fixed.
  (`#472 <https://github.com/git-cola/git-cola/issues/472>`_)

* git-cola no longer clobbers the Ctrl+Backspace text editing shortcut
  in the commit message editor.
  (`#453 <https://github.com/git-cola/git-cola/issues/453>`_)

* The copy/paste clipboard now persists after `git cola` exits.
  (`#484 <https://github.com/git-cola/git-cola/issues/484>`_)


.. _v2.2.1:

v2.2.1
======

Fixes
-----
* Fixed the "Sign off" feature in the commit message editor.


.. _v2.2:

v2.2
====

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

* The system theme's icons are now used wherever possible.
  (`#458 <https://github.com/git-cola/git-cola/pull/458>`_)

Translations
------------
* Traditional Chinese (Taiwan) translation updates.

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
  (`#218 <https://github.com/git-cola/git-cola/issues/218>`_)
  (`#262 <https://github.com/git-cola/git-cola/issues/262>`_)
  (`#377 <https://github.com/git-cola/git-cola/issues/377>`_)

* `git dag`'s file list tool was updated to properly handle Unicode paths.

* `gnome-terminal` is no longer used by default when `cola.terminal` is unset.
  It is broken, as was detailed in #456.
  (`#456 <https://github.com/git-cola/git-cola/issues/456>`_)

* The interactive rebase feature was not always setting `$GIT_EDITOR`
  to the value of `gui.editor`, thus there could be instances where rebase
  will seem to not stop, or hang, when performing "reword" actions.

  We now set the `$GIT_EDITOR` environment variable when performing the
  "Continue", "Skip", and "Edit Todo" rebase actions so that the correct
  editor is used during the rebase.
  (`#445 <https://github.com/git-cola/git-cola/issues/445>`_)

Packaging
---------
* `git cola` moved from a 3-part version number to a simpler 2-part "vX.Y"
  version number.  Most of our releases tend to contain new features.


.. _v2.1.2:

v2.1.2
======
Usability, bells and whistles
-----------------------------
* Updated zh_TW translations.

* `git cola rebase` now defaults to `@{upstream}`, and generally uses the same
  CLI syntax as `git rebase`.

* The commit message editor now allows you to bypass commit hooks by selecting
  the "Bypass Commit Hooks" option.  This is equivalent to passing the
  `--no-verify` option to `git commit`.
  (`#357 <https://github.com/git-cola/git-cola/issues/357>`_)

* We now prevent the "Delete Files" action from creating a dialog that does
  not fit on screen.
  (`#378 <https://github.com/git-cola/git-cola/issues/378>`_)

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
  (`#360 <https://github.com/git-cola/git-cola/issues/360>`_)


.. _v2.1.1:

v2.1.1
======
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

v2.1.0
======
Usability, bells and whistles
-----------------------------
* `git dag` now forwards all unknown arguments along to `git log`.
  (`#389 <https://github.com/git-cola/git-cola/issues/389>`_)

* Line-by-line interactive staging was made more robust.
  (`#399 <https://github.com/git-cola/git-cola/pull/399>`_)

* "Bookmarks" was renamed to "Favorites".
  (`#392 <https://github.com/git-cola/git-cola/issues/392>`_)

* Untracked files are now displayed using a unique icon.
  (`#388 <https://github.com/git-cola/git-cola/pull/388>`_)

Fixes
-----
* `git dag` was triggering a traceback on Fedora when parsing Git logs.
  (`bz #181676 <https://bugzilla.redhat.com/show_bug.cgi?id=1181686>`_)

* inotify expects Unicode paths on Python3.
  (`#393 <https://github.com/git-cola/git-cola/pull/393>`_)

* Untracked files are now assumed to be UTF-8 encoded.
  (`#401 <https://github.com/git-cola/git-cola/issues/401>`_)


.. _v2.0.8:

v2.0.8
======
Usability, bells and whistles
-----------------------------
* `git cola` can now create GPG-signed commits and merges.
  See the documentation for details about setting up a GPG agent.
  (`#149 <https://github.com/git-cola/git-cola/issues/149>`_)

* The status widget learned to copy relative paths when `Ctrl+x` is pressed.
  (`#358 <https://github.com/git-cola/git-cola/issues/358>`_)

* Custom GUI actions can now define their own keyboard shortcuts by
  setting `guitool.$name.shortcut` to a string understood by the Qt
  `QKeySequence` API, e.g. `Alt+X`.
  See the `Qt docs <https://doc.qt.io/qt-6/qkeysequence.html#toString>`_
  for more details about the supported values.

* `git cola` learned to rename branches.
  (`#364 <https://github.com/git-cola/git-cola/pull/364>`_)
  (`#278 <https://github.com/git-cola/git-cola/issues/278>`_)

* `git dag` now has a "Show history" context menu which can be used to filter
  history using the selected paths.

Fixes
-----
* `sphinxtogithub.py` was fixed for Python3.
  (`#353 <https://github.com/git-cola/git-cola/pull/353>`_)

* The commit that changed how we read remotes from `git remote`
  to parsing `git config` was reverted since it created problems
  for some users.

* Fixed a crash when using the `rebase edit` feature.
  (`#351 <https://github.com/git-cola/git-cola/issues/351>`_)

* Better drag-and-drop behavior when dropping into gnome-terminal.
  (`#373 <https://github.com/git-cola/git-cola/issues/373>`_)

Packaging
---------
* The `git-cola-folder-handler.desktop` file handler was fixed
  to pass validation by `desktop-file-validate`.
  (`#356 <https://github.com/git-cola/git-cola/issues/356>`_)

* The `git.svg` icon was renamed to `git-cola.svg`, and `git cola` was taught
  to prefer icons from the desktop theme when available.


.. _v2.0.7:

v2.0.7
======
Usability, bells and whistles
-----------------------------
* New hotkey: `Ctrl+Shift+M` merges branches.

* New hotkey: `Ctrl+R` refreshes the DAG viewer.
  (`#347 <https://github.com/git-cola/git-cola/issues/347>`_)

Fixes
-----
* We now use `git config` to parse the list of remotes
  instead of parsing the output of `git remote`, which
  is a Git porcelain and should not be used by scripts.

* Avoid "C++ object has been deleted" errors from PyQt4.
  (`#346 <https://github.com/git-cola/git-cola/issues/346>`_)

Packaging
---------
* The `make install` target now uses `install` instead of `cp`.


.. _v2.0.6:

v2.0.6
======
Usability, bells and whistles
-----------------------------
* Updated Brazilian Portuguese translation.

* The status and browse widgets now allow drag-and-drop into
  external applications.
  (`#335 <https://github.com/git-cola/git-cola/issues/335>`_)

* We now show a progress bar when cloning repositories.
  (`#312 <https://github.com/git-cola/git-cola/issues/312>`_)

* The bookmarks widget was simplified to not need a
  separate dialog.
  (`#289 <https://github.com/git-cola/git-cola/issues/289>`_)

* Updated Traditional Chinese translation.

* We now display a warning when trying to rebase with uncommitted changes.
  (`#338 <https://github.com/git-cola/git-cola/issues/338>`_)

* The status widget learned to filter paths.
  `Ctrl+Shift+S` toggles the filter widget.
  (`#337 <https://github.com/git-cola/git-cola/issues/337>`_)
  (`#339 <https://github.com/git-cola/git-cola/pull/339>`_)

* The status widget learned to move files to the trash
  when the `send2trash <https://github.com/hsoft/send2trash>`_
  module is installed.
  (`#341 <https://github.com/git-cola/git-cola/issues/341>`_)

* "Recent repositories" is now a dedicated widget.
  (`#342 <https://github.com/git-cola/git-cola/issues/342>`_)

* New Spanish translation thanks to Pilar Molina Lopez.
  (`#344 <https://github.com/git-cola/git-cola/pull/344>`_)

Fixes
-----
* Newly added remotes are now properly seen by the fetch/push/pull dialogs.
  (`#343 <https://github.com/git-cola/git-cola/issues/343>`_)


.. _v2.0.5:

v2.0.5
======
Usability, bells and whistles
-----------------------------
* New Brazilian Portuguese translation thanks to Vitor Lobo.

* New Indonesian translation thanks to Samsul Ma'arif.

* Updated Simplified Chinese translation thanks to Zhang Han.

* `Ctrl+Backspace` is now a hotkey for "delete untracked files" in
  the status widget.

* Fetch/Push/Pull dialogs now use the configured remote of the current
  branch by default.
  (`#324 <https://github.com/git-cola/git-cola/pull/324>`_)

Fixes
-----
* We now use `os.getcwd()` on Python3.
  (`#316 <https://github.com/git-cola/git-cola/pull/316>`_)
  (`#326 <https://github.com/git-cola/git-cola/pull/326>`_)

* The `Ctrl+P` hotkey was overloaded to both "push" and "cherry-pick",
  so "cherry-pick" was moved to `Ctrl+Shift+C`.

* Custom GUI tools with mixed-case names are now properly supported.

* "Diff Region" is now referred to as "Diff Hunk" for consistency
  with common terminology from diff/patch tools.
  (`#328 <https://github.com/git-cola/git-cola/issues/328>`_)

* git-cola's test suite is now portable to MS Windows.
  (`#332 <https://github.com/git-cola/git-cola/pull/332>`_)


.. _v2.0.4:

v2.0.4
======
Usability, bells and whistles
-----------------------------
* We now handle the case when inotify `add_watch()` fails
  and display instructions on how to increase the number of watches.
  (`#263 <https://github.com/git-cola/git-cola/issues/263>`_)

* New and improved zh_TW localization thanks to Ｖ字龍(Vdragon).
  (`#265 <https://github.com/git-cola/git-cola/pull/265>`_)
  (`#267 <https://github.com/git-cola/git-cola/pull/267>`_)
  (`#268 <https://github.com/git-cola/git-cola/pull/268>`_)
  (`#269 <https://github.com/git-cola/git-cola/issues/269>`_)
  (`#270 <https://github.com/git-cola/git-cola/pull/270>`_)
  (`#271 <https://github.com/git-cola/git-cola/pull/271>`_)
  (`#272 <https://github.com/git-cola/git-cola/pull/272>`_)

* New hotkeys: `Ctrl+F` for fetch, `Ctrl+P` for push,
  and `Ctrl+Shift+P` for pull.

* The bookmarks widget's context menu actions were made clearer.
  (`#281 <https://github.com/git-cola/git-cola/issues/281>`_)

* The term "Staging Area" is used consistently in the UI
  to allow for better localization.
  (`#283 <https://github.com/git-cola/git-cola/issues/283>`_)

* The "Section" term is now referred to as "Diff Region"
  in the UI.
  (`#297 <https://github.com/git-cola/git-cola/issues/297>`_)

* The localization documentation related to the LANGUAGE
  environment variable was improved.
  (`#293 <https://github.com/git-cola/git-cola/pull/293>`_)

* The "Actions" panel now contains tooltips for each button
  in case the button labels gets truncated by Qt.
  (`#292 <https://github.com/git-cola/git-cola/issues/292>`_)

* Custom `git config`-defined actions can now be run in the
  background by setting `guitool.<name>.background` to `true`.

Fixes
-----
* We now use bold fonts instead of SmallCaps to avoid
  artifacts on several configurations.

* We now pickup `user.email`, `cola.tabwidth`, and similar settings
  when defined in /etc/gitconfig.
  (`#259 <https://github.com/git-cola/git-cola/issues/259>`_)

* Better support for Unicode paths when using inotify.
  (`bz #1104181 <https://bugzilla.redhat.com/show_bug.cgi?id=1104181>`_)

* Unicode fixes for non-ASCII locales.
  (`#266 <https://github.com/git-cola/git-cola/issues/266>`_)
  (`#273 <https://github.com/git-cola/git-cola/issues/273>`_)
  (`#276 <https://github.com/git-cola/git-cola/issues/276>`_)
  (`#282 <https://github.com/git-cola/git-cola/issues/282>`_)
  (`#298 <https://github.com/git-cola/git-cola/issues/298>`_)
  (`#302 <https://github.com/git-cola/git-cola/issues/302>`_)
  (`#303 <https://github.com/git-cola/git-cola/issues/303>`_)
  (`#305 <https://github.com/git-cola/git-cola/issues/305>`_)

* Viewing history from the file browser was fixed for Python3.
  (`#274 <https://github.com/git-cola/git-cola/issues/274>`_)

* setup.py was fixed to install the `*.rst` documentation.
  (`#279 <https://github.com/git-cola/git-cola/issues/279>`_)

* Patch export was fixed for Python3.
  (`#290 <https://github.com/git-cola/git-cola/issues/290>`_)

* Fixed adding a bookmark with trailing slashes.
  (`#295 <https://github.com/git-cola/git-cola/pull/295>`_)

* The default `git dag` layout is now setup so that its widgets
  can be freely resized on Linux.
  (`#299 <https://github.com/git-cola/git-cola/issues/299>`_)

* Invalid tag names are now reported when creating tags.
  (`#296 <https://github.com/git-cola/git-cola/pull/296>`_)


.. _v2.0.3:

v2.0.3
======
Usability, bells and whistles
-----------------------------
* `git cola` no longer prompts after successfully creating a new branch.
  (`#251 <https://github.com/git-cola/git-cola/pull/251>`_)

* Hitting enter on simple dialogs now accepts them.
  (`#255 <https://github.com/git-cola/git-cola/pull/255>`_)

Fixes
-----
* `git dag` no longer relies on `sys.maxint`, which is
  not available in Python3.
  (`#249 <https://github.com/git-cola/git-cola/issues/249>`_)

* Python3-related fixes.
  (`#254 <https://github.com/git-cola/git-cola/pull/254>`_)

* Python3-on-Windows-related fixes.
  (`#250 <https://github.com/git-cola/git-cola/pull/250>`_)
  (`#252 <https://github.com/git-cola/git-cola/pull/252>`_)
  (`#253 <https://github.com/git-cola/git-cola/pull/253>`_)

* Switching repositories using the bookmarks widget was not
  refreshing the inotify watcher.
  (`#256 <https://github.com/git-cola/git-cola/pull/256>`_)

* Special commit messages trailers (e.g. "Acked-by:") are now special-cased to
  fix word wrapping lines that start with "foo:".
  (`#257 <https://github.com/git-cola/git-cola/issues/257>`_)

* `git dag` sometimes left behind selection artifacts.
  We now refresh the view to avoid them.
  (`#204 <https://github.com/git-cola/git-cola/issues/204>`_)


.. _v2.0.2:

v2.0.2
======
Usability, bells and whistles
-----------------------------
* Better inotify support for file creation and deletion.
  (`#240 <https://github.com/git-cola/git-cola/issues/240>`_)

* `git cola` now supports the X11 Session Management Protocol
  and remembers its state across logout/reboot.
  (`#164 <https://github.com/git-cola/git-cola/issues/164>`_)

* `git cola` has a new icon.
  (`#190 <https://github.com/git-cola/git-cola/issues/190>`_)

Packaging
---------
* Building the documentation no longer requires `asciidoc`.
  We now use `Sphinx <https://www.sphinx-doc.org>`_ for building
  html documentation and man pages.

Fixes
-----
* Reworked the git-dag gravatar icon code to avoid a Unicode
  error in Python 2.

* Commit message line-wrapping was made to better match the GUI editor.
  (`#242 <https://github.com/git-cola/git-cola/issues/242>`_)

* Better support for Python3 on Windows
  (`#246 <https://github.com/git-cola/git-cola/issues/246>`_)

Packaging
---------
* git-cola no longer depends on Asciidoc for building its documentation
  and man-pages.  We now depend on [Sphinx](https://www.sphinx-doc.org) only.


.. _v2.0.1:

v2.0.1
======
Usability, bells and whistles
-----------------------------
* Some context menu actions are now hidden when selected
  files do not exist.
  (`#238 <https://github.com/git-cola/git-cola/issues/238>`_)

Fixes
-----
* The build-git-cola.sh contrib script was improved.
  (`#235 <https://github.com/git-cola/git-cola/pull/235>`_)

* Non-ASCII worktrees work properly again.
  (`#234 <https://github.com/git-cola/git-cola/issues/234>`_)

* The browser now guards itself against missing files.
  (`bz #1041378 <https://bugzilla.redhat.com/show_bug.cgi?id=1071378>`_)

* Saving widget state now works under Python3.
  (`#236 <https://github.com/git-cola/git-cola/pull/236>`_)


.. _v2.0.0:

v2.0.0
======
Portability
-----------
* git-cola now runs on Python 3 thanks to Virgil Dupras.
  (`#233 <https://github.com/git-cola/git-cola/pull/233>`_)

* Python 2.6, 2.7, and 3.2+ are now supported.
  Python 2.5 is no longer supported.

Fixes
-----
* i18n test fixes thanks to Virgil Dupras.
  (`#231 <https://github.com/git-cola/git-cola/pull/231>`_)

* git-cola.app build fixes thanks to Maicon D. Filippsen.
  (`#230 <https://github.com/git-cola/git-cola/pull/230>`_)

* Lots of pylint improvements thanks to Alex Chernetz.
  (`#229 <https://github.com/git-cola/git-cola/pull/229>`_)


.. _v1.9.4:

v1.9.4
======
Usability, bells and whistles
-----------------------------
* The new `Bookmarks` tool makes it really easy to switch between repositories.

* There is now a dedicated dialog for applying patches.
  See the ``File > Apply Patches`` menu item.
  (`#215 <https://github.com/git-cola/git-cola/issues/215>`_)

* A new `git cola am` sub-command was added for applying patches.

Fixes
-----
* Fixed a typo that caused inotify events to be silently ignored.

* Fixed the sys.path setup for Mac OS X (Homebrew).
  (`#221 <https://github.com/git-cola/git-cola/issues/221>`_)

* Lots of pylint fixes thanks to Alex Chernetz.


.. _v1.9.3:

v1.9.3
======
Usability, bells and whistles
-----------------------------
* `git cola --amend` now starts the editor in `amend` mode.
  (`#187 <https://github.com/git-cola/git-cola/issues/187>`_)

* Multiple lines of text can now be pasted into the `summary` field.
  All text beyond the first newline will be automatically moved to the
  `extended description` field.
  (`#212 <https://github.com/git-cola/git-cola/issues/212>`_)

Fixes
-----
* Stray whitespace in `.git` files is now ignored.
  (`#213 <https://github.com/git-cola/git-cola/issues/213>`_)

* Fix "known incorrect sRGB profile" in `staged-item.png`.
  (`gentoo-devel message #85066
  <https://web.archive.org/web/20141012075946/http://comments.gmane.org:80/gmane.linux.gentoo.devel/85066>`_)


.. _v1.9.2:

v1.9.2
======
Fixes
-----
* Fix a traceback when `git push` fails.
  (`bz #1034778 <https://bugzilla.redhat.com/show_bug.cgi?id=1034778>`_)

Packaging
---------
* Most of the git-cola sub-packages have been removed.
  The only remaining packages are `cola`, `cola.models`,
  and `cola.widgets`.

* The translation file for Simplified Chinese was renamed
  to `zh_CN.po`.
  (`#209 <https://github.com/git-cola/git-cola/issues/209>`_)


.. _v1.9.1:

v1.9.1
======
Packaging
---------
* `git cola version --brief` now prints the brief version number.

Fixes
-----
* Resurrected the "make dist" target, for those that prefer to create
  their own tarballs.

* Fixed the typo that broke the preferences dialog.


.. _v1.9.0:

v1.9.0
======
Usability, bells and whistles
-----------------------------
* We now ship a full-featured interactive `git rebase` editor.
  The rebase todo file is edited using the `git xbase` script which
  is provided at `$prefix/share/git-cola/bin/git-xbase`.
  This script can be used standalone by setting the `$GIT_SEQUENCE_EDITOR`
  before running `git rebase --interactive`.
  (`#1 <https://github.com/git-cola/git-cola/issues/1>`_)

* Fixup commit messages can now be loaded from the commit message editor.

* Tool widgets can be locked in place by using the "Tools/Lock Layout"
  menu action.
  (`#202 <https://github.com/git-cola/git-cola/issues/202>`_)

* You can now push to several remotes simultaneously by selecting
  multiple remotes in the "Push" dialog.
  (`#148 <https://github.com/git-cola/git-cola/issues/148>`_)

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
* Support Unicode in the output from `fetch`, `push`, and `pull`.


.. _v1.8.5:

v1.8.5
======
Usability, bells and whistles
-----------------------------
* We now detect when the editor or history browser are misconfigured.
  (`#197 <https://github.com/git-cola/git-cola/issues/197>`_)
  (`bz #886826 <https://bugzilla.redhat.com/show_bug.cgi?id=886826>`_)

* Display of untracked files can be disabled from the Preferences dialog
  or by setting the `gui.displayuntracked` configuration variable to `false`.
  (`Git Mailing List on 2013-08-21
  <https://public-inbox.org/git/20130821032913.GA6092@wheezy.local/>`_)

Fixes
-----
* Unicode stash names are now supported
  (`#198 <https://github.com/git-cola/git-cola/issues/198>`_)

* The diffs produced when reverting workspace changes were made more robust.


.. _v1.8.4:

v1.8.4
======
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
  and choose ``Open With > Git Cola``  (Linux-only).

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
  (`#194 <https://github.com/git-cola/git-cola/issues/194>`_)


.. _v1.8.3:

v1.8.3
======
Usability, bells and whistles
-----------------------------
* The diff viewer now has an "Options" menu which can be
  used to set "git diff" options.  This can be used to
  ignore whitespace changes or to show a change with its
  surrounding function as context.
  (`#150 <https://github.com/git-cola/git-cola/issues/150>`_)

* `git cola` now remembers your commit message and will restore it
  when `git cola` is restarted.
  (`#175 <https://github.com/git-cola/git-cola/pull/175>`_)

* `Ctrl+M` can now be used to toggle the "Amend last commit"
  checkbox in the commit message editor.
  (`#161 <https://github.com/git-cola/git-cola/pull/161>`_)

* Deleting remote branches can now be done from the "Branch" menu.
  (`#152 <https://github.com/git-cola/git-cola/issues/152>`_)

* The commit message editor now has a built-in spell checker.

Fixes
-----
* We now avoid invoking external diffs when showing diffstats.
  (`#163 <https://github.com/git-cola/git-cola/pull/163>`_)

* The `Status` tool learned to reselect files when refreshing.
  (`#165 <https://github.com/git-cola/git-cola/issues/165>`_)

* `git cola` now remembers whether it has been maximized and will restore the
  maximized state when `git cola` is restarted.
  (`#172 <https://github.com/git-cola/git-cola/issues/172>`_)

* Performance is now vastly improved when staging hundreds or
  thousands of files.

* `git cola` was not correctly saving repo-specific configuration.
  (`#174 <https://github.com/git-cola/git-cola/issues/174>`_)

* Fix a UnicodeDecode in sphinxtogithub when building from source.


.. _v1.8.2:

v1.8.2
======

Usability, bells and whistles
-----------------------------
* We now automatically remove missing repositories from the
  "Select Repository" dialog.
  (`#145 <https://github.com/git-cola/git-cola/issues/145>`_)

* A new `git cola diff` sub-command was added for diffing changed files.

Fixes
-----
* The inotify auto-refresh feature makes it difficult to select text in
  the "diff" editor when files are being continually modified by another
  process.  The auto-refresh causes it to lose the currently selected text,
  which is not wanted.  We now avoid this problem by saving and restoring
  the selection when refreshing the editor.
  (`#155 <https://github.com/git-cola/git-cola/issues/155>`_)

* More strings have been marked for l10n.
  (`#157 <https://github.com/git-cola/git-cola/issues/157>`_)

* Fixed the Alt+D Diffstat shortcut.
  (`#159 <https://github.com/git-cola/git-cola/issues/159>`_)

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
  (`#156 <https://github.com/git-cola/git-cola/issues/156>`_)


.. _v1.8.1:

v1.8.1
======

Usability, bells and whistles
-----------------------------
* `git dag` got a big visual upgrade.

* `Ctrl+G` now launches the "Grep" tool.

* `Ctrl+D` launches difftool and `Ctrl+E` launches your editor
  when in the diff panel.

* git-cola can now be told to use an alternative language.
  For example, if the native language is German and we want git-cola to
  use English then we can create a `~/.config/git-cola/language` file with
  "en" as its contents: ``echo en >~/.config/git-cola/language``
  (`#140 <https://github.com/git-cola/git-cola/issues/140>`_)

* A new `git cola merge` sub-command was added for merging branches.

* Less blocking in the main UI

Fixes
-----
* Autocomplete issues on KDE
  (`#144 <https://github.com/git-cola/git-cola/issues/144>`_)

* The "recently opened repositories" startup dialog did not
  display itself in the absence of bookmarks.
  (`#139 <https://github.com/git-cola/git-cola/issues/139>`_)


.. _v1.8.0:

v1.8.0
======

Usability, bells and whistles
-----------------------------
* `git cola` learned to honor `.gitattributes` when showing and
  interactively applying diffs.  This makes it possible to store
  files in git using a non-UTF-8 encoding and `git cola` will
  properly accept them.  This must be enabled by settings
  `cola.fileattributes` to true, as it incurs a small performance
  penalty.
  (`#96 <https://github.com/git-cola/git-cola/issues/96>`_)

* `git cola` now wraps commit messages at 72 columns automatically.
  This is configurable using the `cola.linebreak` variable to enable/disable
  the feature, and `cola.textwidth` to configure the limit.
  (`#133 <https://github.com/git-cola/git-cola/pull/133>`_)

* A new "Open Recent" sub-menu was added to the "File" menu.
  This makes it easy to open a recently-edited repository.
  (`#135 <https://github.com/git-cola/git-cola/issues/135>`_)

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

v1.7.7
======

Usability, bells and whistles
-----------------------------
* New and improved `grep` mode lets you instantly find and edit files.
* New `git cola grep` standalone mode.
* Support for passing arguments to the configured editors, e.g. `gvim -p`
  This makes it possible to select multiple files in the status
  window and use `Ctrl + E` to edit them all at once.
* Remote operations now prompt on errors only.
* The `Tab` key now jumps to the extended description when editing the summary.
* More shortcut key labels and misc. UX improvements.

Fixes
-----
* Selecting an item no longer copies its filename to the copy/paste buffer.
  `Ctrl + C` or the "Copy" context-menu action can be used instead.
* The repository monitoring feature on Windows learned to ignore
  changes within the ".git" directory.  Thanks to Andreas Sommer.
  (`#120 <https://github.com/git-cola/git-cola/issues/120>`_)


.. _v1.7.6:

v1.7.6
======

Usability, bells and whistles
-----------------------------
* `git dag` learned to color-code branch edges.
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

v1.7.5
======

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

v1.7.4.1
========

Fixes
-----
* Detect Homebrew so that OS X users do not need to set PYTHONPATH.

* `git dag` can export patches again.


.. _v1.7.4:

v1.7.4
======

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

v1.7.3
======

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

* Files with a type change (e.g. symlinks that become files, etc.)
  are now correctly identified as being modified.

Packaging
---------
* The `cola.controllers` and `cola.views` packages were removed.


.. _v1.7.2:

v1.7.2
======

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
  (`#99 <https://github.com/git-cola/git-cola/issues/99>`_)

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

v1.7.1.1
========

Fixes
-----
* Further enhanced the staging/unstaging behavior in the status widget.
  (`#97 <https://github.com/git-cola/git-cola/issues/97>`_)

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

v1.7.1
======

Usability, bells and whistles
-----------------------------
* Refined the staging/unstaging behavior for code reviews.
  (`#97 <https://github.com/git-cola/git-cola/issues/97>`_)

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

v1.7.0
======

Usability, bells and whistles
-----------------------------
* Export a patch series from `git dag` into a `patches/` directory.

* `git dag` learned to diff commits, slice history along paths, etc.

* Added instant-preview to the `git stash` widget.

* A simpler preferences editor is used to edit `git config` values.
  (`#90 <https://github.com/git-cola/git-cola/issues/90>`_)
  (`#89 <https://github.com/git-cola/git-cola/issues/89>`_)

* Previous commit messages can be re-loaded from the message editor.
  (`#33 <https://github.com/git-cola/git-cola/issues/33>`_)

Fixes
-----
* Display commits with no file changes.
  (`#82 <https://github.com/git-cola/git-cola/issues/82>`_)

* Improved the diff editor's copy/paste behavior
  (`#90 <https://github.com/git-cola/git-cola/issues/90>`_)

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

v1.4.3.5
========

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
  (`#82 <https://github.com/git-cola/git-cola/issues/82>`_)

* Show the configured remote.$remote.pushurl in the GUI
  (`#83 <https://github.com/git-cola/git-cola/issues/83>`_)

* Removed usage of the "user" module.
  (`#86 <https://github.com/git-cola/git-cola/issues/86>`_)

* Avoids an extra `git update-index` call during startup.


.. _v1.4.3.4:

v1.4.3.4
========

Usability, bells and whistles
-----------------------------
* We now provide better feedback when `git push` fails.
  (`#69 <https://github.com/git-cola/git-cola/issues/69>`_)

* The Fetch, Push, and Pull dialogs now give better feedback
  when interacting with remotes.  The dialogs are modal and
  a progress dialog is used.

Fixes
-----
* More Unicode fixes, again.  It is now possible to have
  Unicode branch names, repository paths, home directories, etc.
  This continued the work initiated by Redhat's bugzilla #694806.

  https://bugzilla.redhat.com/show_bug.cgi?id=694806


.. _v1.4.3.3:

v1.4.3.3
========

Usability, bells and whistles
-----------------------------
* The `git cola` desktop launchers now prompt for a repo
  by default.  This is done by using the new `--prompt`
  flag which tells `git cola` to ignore any git repositories
  in the current directory and prompt for one instead.

Fixes
-----
* More Unicode fixes for repositories and home directories with
  embedded Unicode characters.  Thanks to Christian Jann for
  patience and helpful bug reports.

* Fix the 'Clone' button in the startup dialog.


.. _v1.4.3.2:

v1.4.3.2
========

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

* Fix Unicode errors when home or repository directories contain
  Unicode characters.
  (`#74 <https://github.com/git-cola/git-cola/issues/74>`_)
  (`bz #694806 <https://bugzilla.redhat.com/show_bug.cgi?id=694806>`_)


.. _v1.4.3.1:

v1.4.3.1
========

Usability, bells and whistles
-----------------------------
* The `cola classic` tool can be now configured to be dock-able.
  (`#56 <https://github.com/git-cola/git-cola/issues/56>`_)

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
* Fixed an error when trying to use "Get Commit Message Template"
  with an undefined "commit.template" git config variable.
  (`bz #67521 <https://bugzilla.redhat.com/show_bug.cgi?id=675721>`_)
  (`#72 <https://github.com/git-cola/git-cola/issues/72>`_)

* Properly raise the main window on Mac OS X.

* Properly handle staging a huge numbers of files at once.

* Speed up 'git config' usage by fixing cola's caching proxy.

* Guard against damaged ~/.cola files.


.. _v1.4.3:

v1.4.3
======

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
  (`#67 <https://github.com/git-cola/git-cola/issues/67>`_)

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


.. _v1.4.2.5:

v1.4.2.5
========

Usability, bells and whistles
-----------------------------
* Clicking on paths in the status widget copies them into the
  copy/paste buffer for easy middle-clicking into terminals.

* `Ctrl+C` in diff viewer copies the selected diff to the clipboard.

Fixes
-----
* Fixed the disappearing actions buttons on PyQt 4.7.4
  as reported by Arch and Ubuntu 10.10.
  (`#62 <https://github.com/git-cola/git-cola/issues/62>`_)

* Fixed mouse interaction with the status widget where some
  items could not be de-selected.

Packaging
---------
* Removed hard-coded reference to lib/ when calculating Python's
  site-packages directory.


.. _v1.4.2.4:

v1.4.2.4
========

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

v1.4.2.3
========

Usability, bells and whistles
-----------------------------
* Allow un/staging by right-clicking top-level items
  (`#57 <https://github.com/git-cola/git-cola/issues/57>`_)

* Running 'commit' with no staged changes prompts to allow
  staging all files.
  (`#55 <https://github.com/git-cola/git-cola/issues/55>`_)

* Fetch, Push, and Pull are now available via the menus
  (`#58 <https://github.com/git-cola/git-cola/issues/58>`_)

Fixes
-----
* Simplified the actions widget to work around a regression
  in PyQt4 4.7.4.
  (`#62 <https://github.com/git-cola/git-cola/issues/62>`_)


.. _v1.4.2.2:

v1.4.2.2
========

Usability, bells and whistles
-----------------------------
* `git dag` interaction was made faster.

Fixes
-----
* Added '...' indicators to the buttons for
  'Fetch...', 'Push...', 'Pull...', and 'Stash...'.
  (`#51 <https://github.com/git-cola/git-cola/issues/51>`_)

* Fixed a hang-on-exit bug in the cola-provided
  'ssh-askpass' implementation.


.. _v1.4.2.1:

v1.4.2.1
========

Usability, bells and whistles
-----------------------------
* Staging and unstaging is faster.
  (`#48 <https://github.com/git-cola/git-cola/issues/48>`_)

* `git dag` reads history in a background thread.

Portability
-----------
* Added `cola.compat.hashlib` for `Python 2.4` compatibility
* Improved `PyQt 4.1.x` compatibility.

Fixes
-----
* Configured menu actions use ``sh -c`` for Windows portability.


.. _v1.4.2:

v1.4.2
======

Usability, bells and whistles
-----------------------------
* Added support for the configurable ``guitool.<tool>.*``
  actions as described in the ``git config`` documentation.
  (`git-config(1) <https://git-scm.com/docs/git-config>`_)
  (`#44 <https://github.com/git-cola/git-cola/issues/44>`_)

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
  (`#17 <https://github.com/git-cola/git-cola/issues/17>`_)

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
  (`#45 <https://github.com/git-cola/git-cola/issues/45>`_)

* Log internal ``git`` commands when ``GIT_COLA_TRACE`` is defined.
  (`#39 <https://github.com/git-cola/git-cola/issues/39>`_)

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
  (`#43 <https://github.com/git-cola/git-cola/issues/43>`_)

Packaging
---------
* Removed colon (`:`) from the application name on Windows
  (`#41 <https://github.com/git-cola/git-cola/issues/41>`_)

* Fixed bugs with the Windows installer
  (`#40 <https://github.com/git-cola/git-cola/issues/40>`_)

* Added a more standard i18n infrastructure.  The install
  tree now has the common ``share/locale/$lang/LC_MESSAGES/git-cola.mo``
  layout in use by several projects.

* Started trying to accommodate Mac OS X 10.6 (Snow Leopard)
  in the ``darwin/`` build scripts but our tester is yet to
  report success building a `.app` bundle.

* Replaced use of ``perl`` in Sphinx/documentation Makefile
  with more-portable ``sed`` constructs.  Thanks to
  Stefan Naewe for discovering the portability issues and
  providing msysgit-friendly patches.


.. _v1.4.1.2:

v1.4.1.2
========

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

v1.4.1.1
========

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

v1.4.1
======

This feature release adds two new features directly from
`git cola`'s github issues backlog.  On the developer
front, further work was done towards modularizing the code base.

Usability, bells and whistles
-----------------------------
* Dragging and dropping patches invokes `git am`
  (`#3 <https://github.com/git-cola/git-cola/issues/3>`_)

* A dialog to allow opening or cloning a repository
  is presented when `git cola` is launched outside of a git repository.
  (`#22 <https://github.com/git-cola/git-cola/issues/22>`_)

* Warn when `push` is used to create a new branch
  (`#35 <https://github.com/git-cola/git-cola/issues/35>`_)

* Optimized startup time by removing several calls to `git`.


Portability
-----------
* `git cola` is once again compatible with PyQt 4.3.x.

Developer
---------
* `cola.gitcmds` was added to factor out git command-line utilities

* `cola.gitcfg` was added for interacting with `git config`

* `cola.models.browser` was added to factor out repo browser data

* Added more tests


.. _v1.4.0.5:

v1.4.0.5
========

Fixes
-----
* Fix launching external applications on Windows

* Ensure that the `amend` checkbox is unchecked when switching modes

* Update the status tree when amending commits


.. _v1.4.0.4:

v1.4.0.4
========

Packaging
---------
* Fix Lintian warnings


.. _v1.4.0.3:

v1.4.0.3
========

Fixes
-----
* Fix X11 warnings on application startup


.. _v1.4.0.2:

v1.4.0.2
========

Fixes
-----
* Added missing 'Exit Diff Mode' button for 'Diff Expression' mode
  (`#31 <https://github.com/git-cola/git-cola/issues/31>`_)

* Fix a bug when initializing fonts on Windows
  (`#32 <https://github.com/git-cola/git-cola/issues/32>`_)


.. _v1.4.0.1:

v1.4.0.1
========

Fixes
-----
* Keep entries in sorted order in the `cola classic` tool

* Fix staging untracked files
  (`#27 <https://github.com/git-cola/git-cola/issues/27>`_)

* Fix the `show` command in the Stash dialog
  (`#29 <https://github.com/git-cola/git-cola/issues/29>`_)

* Fix a typo when loading merge commit messages
  (`#30 <https://github.com/git-cola/git-cola/issues/30>`_)


.. _v1.4.0:

v1.4.0
======

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

v1.3.9
======

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

v1.3.8
======

Usability, bells and whistles
-----------------------------
* Fresh and tasty SVG logos

* Added `Branch Review` mode for reviewing topic branches

* Added diff modes for diffing between tags, branches,
  or arbitrary `git diff` expressions

* The push dialog selects the current branch by default.
  This is in preparation for `git 1.7.0` where `git push`
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

* Added Mac OS X application bundles to the download page


.. _v1.3.7:

v1.3.7
======

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
* More of the code base was updated to follow the `PEP-8` coding style

* Added more tests

Packaging
---------
* All resources are now installed into `$prefix/share/git-cola`.
  Closed Debian bug #519972

  https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=519972


.. _v1.3.6:

v1.3.6
======

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
