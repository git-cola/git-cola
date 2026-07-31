# Gotchas

Non-obvious behavior in this codebase and its toolchain, each with the evidence that established
it. These were found the expensive way. Re-verify before leaning on one — line numbers drift.

## Qt state persistence

**`QMainWindow.saveState()` covers dock and toolbar topology only.** Splitters, column widths and
anything inside a dock's widget are not in that blob. Consequences:

- Adding or removing a **dock** requires bumping `widget_version` (`cola/widgets/main.py`,
  `cola/widgets/dag.py` — both currently `2`).
- Adding a splitter, a pane, or a child widget does **not**.
- Bumping the version discards every user's saved geometry and breaks hard-coded assertions in
  the test suite. Check what actually gets serialized before proposing a migration.

**Composite widgets nest their children's state.** `MainView.export_state()` puts the history
widget's state under `state['history']`; `CommitHistoryWidget` puts the tree's under
`state['log']`. Adding a key to a nested exporter breaks every exact-dict assertion in the tests
that compare whole state blobs — grep for `== {` in `test/` before changing an exporter.

**`is_valid_state()` returns early.** `CommitHistoryWidget.is_valid_state` returns `True` as soon
as it sees no `'log'` key. Validation for new keys must go *above* that, or it silently never
runs for exactly the legacy states it was written for.

## Qt widget behavior

**`qtutils.add_action_bool` connects `triggered[bool]`, not `toggled`.** Calling `setChecked()`
during construction therefore does **not** invoke the handler. Existing code (the
`display_inline_graph` and `display_files` actions in `cola/widgets/dag.py`) calls the handler
explicitly right after creating the action. Copy that; don't rely on the signal.

**Shortcuts are widget-scoped.** `qtutils._add_action` sets `Qt.WidgetWithChildrenShortcut`, so
two instances of the same widget in one window do not produce ambiguous-shortcut warnings.

**Tree selection signals are queued.** `CommitTreeWidget` connects `itemSelectionChanged` with
`type=Qt.QueuedConnection`. In tests, `setCurrentItem()` does nothing observable until the event
loop is pumped.

**`QSplitter.addWidget()` does not override visibility** set before or after the call, and inside
a parent's `showEvent` the children already report `isVisible() == True` — Qt shows children
before delivering the parent's show event. Both verified offscreen under PyQt5.

**Instance-level method shadowing works on Qt objects** (`splitter.setSizes = spy`), which makes
`monkeypatch.setattr(obj, 'method', ...)` a usable test technique here.

**Splitter sizes are meaningless before the first layout.** A never-shown splitter reports `[0,0]`
or hint values depending on the binding. Never assert against fixed pixel numbers; compare
against the live value, or spy on `setSizes`.

**`CommitDiffWidget.commits_selected()` arms a 100 ms debounce that fires later and wins.**
Calling it and then `files_selected(['path'])` shows the single-file diff — until the timer fires
and reloads the whole-commit diff over it (measured: `filename=None`, two git calls). To show one
file's diff, set `oid` / `oid_start` / `oid_end` directly and call `files_selected()` once, the
way `CommitFileDiffWindow.set_commit_file()` does.

**A `standard.Widget` with a parent is not a window.** `isWindow()` is `False` until you call
`setWindowFlags(Qt.Window)`; without it the widget silently becomes a child in the parent's
layout. `standard.Dialog` is a window straight away. Both persist geometry on close — `Widget`
via `WidgetMixin.closeEvent`, `Dialog` via `closeEvent → reject()` — so state saving is *not*
what distinguishes them.

**Qt destroys child widgets without sending a close event.** A window that saves its state in
`closeEvent` therefore loses it when the parent goes away. Hosts close such children explicitly:
see the `browser_windows` loop and the `commit_file_diff_window` line in `MainView.closeEvent`.

## Git output

**`git show --raw` prints nothing for merge commits**, while `--numstat` still prints the combined
diff. Any parser reading both must tolerate numstat entries with no raw block — and the codebase
relies on that path, because several DAG tests monkeypatch `git.show` to return numstat only.

**`--raw` and `--numstat` can be requested together** in one invocation, for `show`, `diff`,
`diff-index` and `diff-files`. Git emits the raw block first, then numstat. With `-z` the raw path
is its own NUL-separated field; without `-z` it follows the info field after a tab.
`cola/widgets/filelist.py:parse_status_and_numstat()` handles both.

**`git diff-files` and `git diff-index` do not emit NUL separators between entries** even with
`-z` — there is a comment about this in `filelist.py`. Those two paths split on newline.

**Numstat field order is `adds<TAB>dels<TAB>path`.** `FileTreeWidgetItem` relies on it. Getting
this backwards produces test data that looks plausible and asserts nothing.

**The `git` wrapper turns kwargs into flags** (`cola/git.py:transform_kwargs`): `raw=True` →
`--raw`, `no_renames=True` → `--no-renames`, `foo=False` is dropped, `foo='bar'` → `--foo=bar`.
Single-character keys get one dash. `_readonly=True` is a wrapper hint, not a git flag.

## Icons

**`cola/icons.py` is the only file that names icon assets** — that is stated in its module
docstring, and it is a rule worth keeping. Add a lookup table plus a small function there rather
than spreading basenames across widgets.

**Icons do not resolve in tests.** `icons.install()` registers the `icons:` search path and is
only called from `cola/app.py`. In a test, `QIcon('icons:plus.svg')` is null. Assert on the data
(a status field, the basename returned by a pure function), never on the rendered icon.

**Check the asset exists** in `cola/icons/` before referencing a basename. The set is small and
does not include everything you would expect.

## Tests

**`app_context` gives you a real repository.** It creates a temp dir, `chdir`s in, runs
`initialize_repo()` (files `A` and `B`, staged, branch `main`, gpgsign off) and yields a `Mock()`
context wired to a real `git`, `cfg` and `MainModel`. Building your own repo or monkeypatching
`context.git` is almost always redundant work.

**There is no `conftest.py`.** `qapp`, `managed_qobject` and `main_context` are defined
per test file. Copy them from a neighbouring widget test verbatim instead of writing variants.

**`app_context.settings` is a raw `Mock`, and a `Mock` is truthy.** Any widget that calls
`init_state(context.settings, ...)` therefore takes the restore branch and hands `Mock` objects
to `QByteArray.fromBase64()` — a `TypeError` at construction time, with a message that says
nothing about your test. Set `app_context.settings.get_gui_state.return_value = {}` first; that
is what `main_context` and every `GitDAG` test already do.

**`--doctest-modules` is on and `garden test` collects `cola/` too.** A `>>>` in any production
docstring becomes a test case.

**`pytest-ruff` runs by default** via `pytest-enabler`; focused runs pass `-p no:ruff`, matching
CI, and lint is a separate step.

**Test names can encode contracts.** `test_public_selection_reaches_all_standalone_consumers_
synchronously` and `test_history_widget_owns_history_state_without_window_children` are
architectural decisions written down as tests. Violating one is a design change requiring
justification, not a test to be edited into agreement.

## Toolchain

**The formatter is `cercis`, not black** (`[tool.cercis]` in `pyproject.toml`, plus the
pre-commit hook). Line length 88, `function-definition-extra-indent = false`.

**isort runs with `--force-single-line-imports --py=39 --no-lines-before=STDLIB`.** One import per
line. Some test files carry `# ruff: noqa: I001` at the top because of this — keep it when editing
those files.

**mypy is pinned to 1.19.1** and configured leniently (`disallow_untyped_defs = false`, several
error codes disabled). It checks `bin` and `cola`, not `test`.

**Python 3.9 is the floor**, enforced by `pyupgrade --py39-plus` in CI and pre-commit.

## The git-fanta rename

**`icons.cola()` keeps its name on purpose.** `cola/widgets/toolbar.py:254` resolves icon names
with `getattr(icons, name, None)` and `cola/widgets/toolbarcmds.py:283`/`:285` pass `'icon':
'cola'`. Renaming the function removes the toolbar icon silently — no exception, no log entry.
The asset it returns is `git-fanta.svg`; the function name is not user-visible.

**`cola/version.py` asks `metadata.version('git-fanta')`,** which must match `name` in
`pyproject.toml`. If the two drift, `importlib.metadata` raises `PackageNotFoundError` and the
version display falls back to the builtin value without saying so.
`test_distribution_name_matches_pyproject` guards it.

**`brew install git-cola` in `.github/workflows/ci.yml` is not a leftover.** It installs the real
upstream Homebrew formula as a dependency of the macOS job. Renaming it breaks that job.

**A forgotten `'cola.<key>'` literal will not turn a test red.** `cola/gitcfg.py` falls back to
the old prefix by design, so the stale key keeps working and the rename is quietly incomplete.
`test_no_legacy_config_key_literals` in `test/rename_guard_test.py` is the only thing that
notices — there are 34 such literals outside `cola/models/prefs.py`, spread over 16 files.

**The upstream references are load-bearing.** `CHANGES.rst`, the `github.com/git-cola/...` links
in code comments, and the remotes in `garden.yaml` point at a project that still exists.
`test_upstream_references_are_preserved` fails if a future rename sweep eats them.
