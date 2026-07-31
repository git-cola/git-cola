# What this fork changed, and the decisions behind it

git-fanta tracks git-fanta and adds UI work around the commit history. Two features have shipped
so far. Both have a plan document in `docs/plans/` that records the reasoning; read the plan
before changing the feature, because several constraints in the code look arbitrary until you
see why they were chosen.

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

**Single-clicking a file still does not show its diff** — the selection stays a selection.
**Double-clicking does**: `FileWidget.file_diff_requested` carries `(commits, path)` to the host,
which opens a reusable `CommitFileDiffWindow` (`cola/widgets/diff.py`). See
`docs/plans/2026-07-31-commit-file-diff-window.md`.

Two things about that window are load-bearing:

- It is a `standard.Widget` with `Qt.Window`, **not** a `standard.Dialog`. Only the former's
  `closeEvent` calls `save_settings()`, so only the former remembers its geometry.
- `set_commit_file()` seeds `oid`/`oid_start`/`oid_end` directly instead of calling
  `CommitDiffWidget.commits_selected()`. That method starts a 100 ms debounce which would fire
  after `files_selected()` and replace the single-file diff with the whole-commit diff.
  `test_set_commit_file_survives_the_debounce` guards this.

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
