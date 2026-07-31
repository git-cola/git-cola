# What this fork changed, and the decisions behind it

git-fanta is a fork of git-cola and adds UI work around the commit history, plus the
rename that gave the fork its own name. Four work packages have shipped. Each has a plan document
in `docs/plans/` that records the reasoning; read the plan before changing the feature, because
several constraints in the code look arbitrary until you see why they were chosen.

Verify anything here against the tree before relying on it — this file is a map, not a mirror.

## 1. Inline commit history in the main window

Plan: `docs/plans/2026-07-28-git-fanta-ui-history-graph.md` (completed, frontmatter has the
implementation branch and CI run).

**What it delivered.** The main window has a History dock that is visible by default, showing an
inline commit graph over `ref='--all'`, 1000 commits, without WORKTREE/STAGE pseudo-commits. The
history UI that used to belong to the standalone DAG window was extracted into a reusable
`CommitHistoryWidget` (`cola/widgets/dag.py`), now shared by `MainView` and `GitDAG`.

**Decisions that later work must not undo:**

- **`cola/models/graph.py:build_graph()` is the single graph engine.** An earlier chunked
  variant dropped edges beyond ~2048 commits. The worker collects the full commit list and calls
  `build_graph()` exactly once; only the final result is applied to the view.
- **Each `RepoReader` owns its own `CommitFactory`.** A process-global commit cache collided
  between parallel reads.
- **Latest-desired-state loading.** Immutable `HistoryRequest`/`HistoryResult`, a run id, one
  active worker and exactly one coalesced pending request. Stale results are dropped rather than
  applied.
- **Failures preserve the last good history** and surface the return code plus the exact stderr
  non-modally. A successful *empty* history clears the visible state atomically.
- **The inline graph is palette-based and cache-free**, so light/dark themes work without
  invalidation logic. It is covered by semantic offscreen paint tests that run under both PyQt5
  and PyQt6 (`test/widgets_dag_history_test.py`, selected by `-k semantic_paint_smoke` in CI).
- **The standalone DAG window keeps everything it had** — its large `GraphView`, its Diff and
  Files docks, and its "Display Worktree Status" option.

`MainView` deliberately disconnects `model.updated` from `historywidget.model_updated`
(`cola/widgets/main.py`) and drives history reloads itself, and it hides history context-menu
actions that make no sense in the main window via `_MAIN_HISTORY_UNSUPPORTED_ACTIONS`.

## 2. Commit file panel next to the history table

Plan: `docs/plans/2026-07-29-history-commit-files.md`. Implemented across
`35633a02 → 86b9863d`, with follow-ups for layout and formatting.

**Shape.** The list of files changed in the selected commit is *not* a dock and not a tab. It is
the right pane of a horizontal splitter inside `CommitHistoryWidget`, so it cannot exist without
the history component. The precedent it follows is `cola/sequenceeditor.py`, which already lays
out the rebase tree and a `FileWidget` in exactly this way.

**Decisions that later work must not undo:**

- **Opt-in per host.** `CommitHistoryWidget(..., display_files=False)` by default; `MainView`
  passes `True`. The standalone DAG keeps its own `file_dock`, so its inline panel stays hidden.
  The parameter is **last** in the signature because tests construct the widget positionally.
- **No `widget_version` bump.** Both `MainView` and `GitDAG` are still at `widget_version = 2`.
  A splitter inside a dock is not part of `QMainWindow.saveState()`, so no layout migration is
  needed — and a bump would discard every user's saved geometry.
- **Panel state rides in the existing history state channel**: `display_files` and `files_sizes`
  in `CommitHistoryWidget.export_state()`, validated in `is_valid_state()`, applied in
  `apply_state()`. The `display_files` default on restore comes from the **action's current
  state**, i.e. from the host, which is why legacy states need no migration marker.
- **Debounce plus visibility guard.** A 100 ms single-shot timer coalesces rapid selection
  changes, and a hidden panel never runs git at all. The guard is a correctness requirement, not
  just an optimization: without it the DAG window would issue two `git show` calls per selection
  and break its "exactly once" assertion.
- **`FileWidget` stays synchronous.** Scheduling policy lives in the host
  (`_schedule_files` / `_load_pending_files` / `refresh_files` on `CommitHistoryWidget`),
  because a DAG test asserts synchronous population by name.
- **Status icons come from one git call.** `--raw` and `--numstat` are requested together, so
  status letters and +/- counts arrive without a second process. `parse_status_and_numstat()` in
  `cola/widgets/filelist.py` splits the two blocks; `icons.diff_status()` maps the letter to an
  existing asset and falls back to the file-type icon when the status is unknown.

`MainView` hides the file context-menu actions that would need host wiring, via
`_MAIN_HISTORY_UNSUPPORTED_FILE_ACTIONS` (`cola/widgets/main.py:65`), keeping only
"Launch Editor", which works standalone.

## 3. The rename to git-fanta

Plan: `docs/plans/2026-07-30-rename-to-git-fanta.md`. Implemented across `11e04304 → 54331885`.

**Scope.** Everything user-facing carries the fork name; the Python package does not.

| Renamed | Kept as `cola` |
|---|---|
| `bin/git-fanta`, `bin/git-fanta-sequence-editor`, the `git fanta` sub-command | the `cola/` package and every `import cola` |
| `pyproject.toml` `name = "git-fanta"` and the entry points | `[tool.setuptools] packages`, `cola/resources.py`'s `site-packages/cola` checks |
| `fanta.*` git-config keys (44 in `cola/models/prefs.py`, 34 more inline) | `icons.cola()` — see gotchas, renaming it breaks the toolbar silently |
| `GIT_FANTA_*` environment variables | `ColaApplication`, `ColaQApplication` |
| `~/.config/git-fanta`, `fanta-prepare-commit-msg` | upstream references (see below) |

**Decisions that later work must not undo:**

- **Nothing that points at the upstream project was rewritten.** `CHANGES.rst`, the ~40
  `github.com/git-cola/...` issue links in code comments, the remotes in `garden.yaml`, and
  `brew install git-cola` in the macOS CI job all refer to a real, still-existing project.
  `test/rename_guard_test.py` enforces both directions: no stray old product name, and the
  allow-listed upstream references still present.
- **Every user-facing rename has a backwards fallback**, so a pre-rename setup keeps working:
  `gitcfg._key_candidates()` probes `fanta.*` then `cola.*` (`cola/gitcfg.py:253`),
  `compat.getenv_with_legacy()` does the same for the env vars (`cola/compat.py:101`),
  `gitcmds.prepare_commit_message_hook()` still honours a `cola-prepare-commit-msg` hook, and
  `resources.migrate_config_home()` (`cola/resources.py:236`) copies (git-fanta was renamed from git-cola) `~/.config/git-cola` over
  once on first run.
- **`git fanta cola` still works.** The sub-command was renamed with an argparse alias
  (`cola/main.py:102`), so old scripts and shell history do not break.
- **The `.po` source references still say `cola/`,** because the package name did not change.
  Only the eight user-visible `msgid` strings were touched.

## 4. Double-click a commit file to see its diff

Plan: `docs/plans/2026-07-31-commit-file-diff-window.md`. Implemented across
`de79feca → c73ec4a2`.

**Single-clicking a file still does not show its diff** — the selection stays a selection.
**Double-clicking does**: `FileWidget.file_diff_requested` carries `(commits, path)` to the host,
which opens a reusable `CommitFileDiffWindow` (`cola/widgets/diff.py`).

**Decisions that later work must not undo:**

- **`set_commit_file()` seeds `oid`/`oid_start`/`oid_end` directly** instead of calling
  `CommitDiffWidget.commits_selected()`. That method starts a 100 ms debounce which fires *after*
  `files_selected()` and replaces the single-file diff with the whole-commit diff — measured:
  `filename=None`, two git calls instead of one. `test_set_commit_file_survives_the_debounce`
  guards it.
- **The window hangs off the host, not off `CommitHistoryWidget`.** `MainView` and `GitDAG` each
  own one `commit_file_diff_window` slot (`cola/widgets/main.py:145`, `cola/widgets/dag.py:2161`)
  and close it in their `closeEvent` so the geometry gets saved. The history widget may not own a
  `diffwidget` — `test_history_widget_owns_history_state_without_window_children` says so.
- **One window per host, reused.** `show_commit_file_diff(..., window=...)` returns the window it
  used; the host stores it. A second double-click reloads that window instead of opening another.
- **It is a `standard.Widget` with `Qt.Window`, not a `standard.Dialog`** — because `Browser`
  (`cola/widgets/browse.py:57`) is the project's pattern for a persisted, non-modal tool window,
  and `Dialog` brings an `accept()`/`reject()` result model plus a tendency toward modality that
  a viewer has no use for. **Not** because of state saving: both classes call `save_settings()`
  on close (`Dialog` routes through `closeEvent → reject()`), measured over both close paths.
- **`GitDAG` wires both of its file lists** — the `file_dock` one and the (hidden by default)
  inline panel of its `CommitHistoryWidget` — to the same window.
- **The rebase sequence editor is deliberately not wired.** `cola/sequenceeditor.py:174` holds a
  third `FileWidget` and does populate `FileWidget.commits`, so it emits `file_diff_requested`
  into nothing. A double-click there is a no-op by design.

## Where the fork's tests live

- `test/widgets_dag_history_test.py` — `CommitHistoryWidget`, `GitDAG`, state round-trips,
  the semantic paint smoke tests, and the structural invariant test that says what the reusable
  history widget may and may not own.
- `test/widgets_main_history_test.py` — `MainView` integration: dock visibility, state export,
  legacy windowstate restore, refresh-on-command behavior, the file panel in the main window.
- `test/widgets_history_filelist_test.py` — `FileWidget` characterization plus the
  `--raw --numstat` parser and the status-icon mapping.
- `test/widgets_commit_file_diff_test.py` — `CommitFileDiffWindow`, the single-file diff
  seeding, window reuse, and the debounce regression guard.
- `test/diff_debounce_test.py` — the debounce/supersede pattern in `CommitDiffWidget` that the
  file panel's scheduling was modeled on.
- `test/rename_guard_test.py` — the rename invariants: no stray old product name in the tracked
  sources or filenames, the allow-listed upstream references intact, `CHANGES.rst` untouched, no
  leftover `'cola.<key>'` config literals, and the coupling between `pyproject.toml`'s `name` and
  `cola/version.py`.
- `test/env_rename_test.py`, `test/config_home_migration_test.py`,
  `test/prepare_commit_msg_hook_test.py` — one file per backwards fallback introduced by the
  rename. If you remove a fallback, these are the tests that are supposed to stop you.
