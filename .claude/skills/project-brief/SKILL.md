---
name: project-brief
description: Orientation for the git-fanta repository — what it is, how the codebase is laid out, the Qt/qtpy conventions, the test fixtures and how to run them, the verification gates, and the traps that repeatedly cost a cycle. Load this at the start of any session in this repo before writing code, planning a change, reviewing a plan, or answering questions about how something works here. Also use it when the user asks how to run the app or the tests, where a feature lives, what the commit or branch conventions are, or says things like "orientier dich mal", "wie läuft das hier", "was ist das für ein projekt". Prefer this over guessing from file names — several conventions here (cercis, single-line imports, offscreen Qt, the real-repo test fixture) are non-obvious and easy to violate.
---

# git-fanta

A fork of git-cola, the Qt desktop GUI for Git, renamed to **git-fanta**. Everything
user-facing carries the fork name: the `git-fanta` executable, the `git fanta` subcommand,
`fanta.*` git-config keys, `GIT_FANTA_*` environment variables and `~/.config/git-fanta`.
The Python package is still `cola` (`import cola`, `cola/`) and `[tool.setuptools] packages`
names it — that is deliberate, do not "fix" it. References to the upstream project
(github.com/git-cola/git-cola, `brew install git-cola`, `CHANGES.rst`, the remotes in
`garden.yaml`) are also deliberate and must stay. See
`docs/plans/2026-07-30-rename-to-git-fanta.md`.

The fork's own work so far is UI: making the commit history graph a first-class part of the main
window rather than a separate DAG window. Read `references/fork-history.md` when you need to know
what this fork changed and why — it also records the design decisions that later changes must not
undo.

## Layout

| Path | What lives there |
|---|---|
| `cola/widgets/` | All Qt views. `main.py` = MainView (the main window), `dag.py` = commit history + graph + the standalone DAG window, `diff.py`, `status.py`, `filelist.py`, `standard.py` (base classes + state mixins), `defs.py` (spacing constants), `qtutils`-adjacent helpers |
| `cola/models/` | Non-Qt data models: `main.py` (MainModel), `dag.py` (Commit/RepoReader), `graph.py` (the single graph engine, `build_graph()`), `prefs.py`, `selection.py` |
| `cola/` (top level) | `git.py` (Git process wrapper), `gitcmds.py` (git commands + output parsing), `cmds.py` (undoable commands), `qtutils.py` (widget factories, `Task`/`RunTask`, state helpers), `icons.py` (the **only** file naming icon assets), `hotkeys.py`, `app.py` (`ApplicationContext`), `settings.py`, `i18n.py` |
| `cola/icons/` | The SVG assets. Check here before assuming an icon exists |
| `test/` | 36 `*_test.py` files, flat, plus `helper.py`. No `conftest.py` — fixtures are defined per file or imported from `helper` |
| `docs/plans/` | Implementation plans (see Workflow below) |
| `bin/` | Launchers: `git-fanta`, `git-dag`, `git-fanta-sequence-editor` |

## Architecture in five sentences

`ApplicationContext` (`cola/app.py:805`) is the dependency container passed to nearly everything:
`context.git`, `.cfg`, `.model`, `.settings`, `.selection`, `.runtask`, `.view`, `.notifier`.
Widgets take `context` as their first constructor argument and read what they need from it.
Mutating operations go through `cmds.do(cmds.SomeCommand, context, ...)` rather than direct git
calls, so they can log and notify; read-only queries go through `gitcmds`. Widgets talk to each
other with Qt signals, frequently `type=Qt.QueuedConnection`, and long work runs on
`context.runtask.start(qtutils.Task(...))` or a `QThread`. UI state persists through
`export_state()` / `apply_state()` pairs defined by the mixins in `cola/widgets/standard.py`,
with each composite widget nesting its children's state under its own key.

## Conventions that will bite you

- **Qt binding is abstracted.** Always `from qtpy import QtWidgets` etc., never `PyQt6` directly.
  Code must work under PyQt5, PyQt6 and PySide6. CI runs a pyqt5/pyqt6 matrix.
- **Formatter is `cercis`, not black** (a black fork), line length 88, plus
  `isort --force-single-line-imports --py=39 --no-lines-before=STDLIB`. One import per line,
  alphabetical. Run `garden fmt`; do not hand-format.
- **Target is Python 3.9.** `pyupgrade --py39-plus` is a CI gate. No 3.10+ syntax.
- **User-visible strings go through `N_()`** from `cola.i18n`. Catalogs live in `cola/i18n/`.
- **`pytest.ini` sets `--doctest-modules`,** and `garden test` collects `cola` *and* `test`.
  A `>>>` in any docstring becomes a test. Don't put example REPL output in docstrings casually.
- **`pytest-ruff` runs as a plugin** via `pytest-enabler`. Focused local runs usually pass
  `-p no:ruff` (CI does too) and lint separately.
- **Icons are looked up by basename** through `icons.name_from_basename()` → `icons.from_name()`,
  and the `icons:` search path is only registered by `icons.install()` in `cola/app.py`. In tests
  no icon resolves, so assert on data, never on `QIcon.isNull()`.

## Running things

```bash
garden run                 # launch the app (env3 virtualenv)
garden run/qt6             # same, forcing QT_API=PyQt6
garden test                # offscreen pytest over cola/ and test/
garden fmt                 # cercis + isort, in place
garden check/fmt           # the same, --check only
garden check/mypy          # mypy --config-file pyproject.toml bin cola
garden check/pyupgrade     # py39 idiom check
garden doc/html            # Sphinx build
```

First-time setup: `garden dev/virtualenv && garden dev` (creates `env3/`).

Focused test runs without garden — the form used throughout this repo's plans and CI:

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_main_history_test.py -p no:ruff -q
```

Add `QT_API=pyqt5` or `QT_API=pyqt6` to reproduce the CI binding matrix.

## Testing conventions

`test/helper.py` provides the important pieces. Read them before writing new scaffolding —
reinventing these is the most common wasted work in this repo.

- **`app_context` fixture** (`test/helper.py:85`) creates a **real temporary git repository**,
  `chdir`s into it, runs `initialize_repo()` (which creates and stages files `A` and `B`), and
  builds a `Mock()` context with a real `git`, `cfg` and `MainModel`. You do **not** need to
  construct repos or monkeypatch `context.git` — just run `run_git(...)` / the local `_git(...)`
  helper and commit.
- **`qapp` and `managed_qobject`** are defined per test file (module-scoped `QApplication`;
  `managed_qobject` closes and deletes widgets and pumps `DeferredDelete`). Copy them from a
  neighbouring widget test rather than inventing a variant.
- Widget tests that need `Interaction` silenced use a local `main_context` fixture layered on
  `app_context` — see `test/widgets_main_history_test.py:111`.
- **Selection signals are often `QueuedConnection`.** After `setCurrentItem()` you must pump the
  event loop (`qapp.processEvents()` / `QtTest.QTest.qWait`) before asserting.
- Wait helpers exist (`_wait_for_history`, `_show`, `_git`) — reuse them; write a new one only
  when the exit condition is genuinely different, and check that something actually sets it.
- Some tests encode architectural contracts in their **names**
  (`..._synchronously`, `..._without_window_children`). Breaking one is a design decision, not
  a test-fixing chore.

## Workflow

- **Plans live in `docs/plans/YYYY-MM-DD-topic.md`**, written in German, task-structured with
  TDD RED/GREEN steps and explicit verification commands. Completed plans get a YAML frontmatter
  block (`status`, `completed_at`, `plan_commit`, `implementation_branch`, `implementation_head`,
  `ci_run`, `manual_verification`) and stay in place as design records.
- **Review a plan before executing it** with the personal `plan-review` skill. Plans in this repo
  have historically shipped with wrong line references and non-terminating test helpers.
- **Branches**: `tree-ui/<agent>/<model>/<topic>` for feature work (e.g.
  `tree-ui/claude/opus5/minimax-M3`), plus `main` and `dev`. Never commit to `main` directly.
- **Commits are conventional-commit style** with a domain prefix that matches the work:
  `feat:`, `fix:`, `test:`, `style:`, `docs:`, `chore:`, `ci:`, and `plan:` for plan documents.
  One task per commit; the plan's task boundaries are the commit boundaries.
- CI (`.github/workflows/ci.yml`) runs `garden test -- -p no:ruff`, ruff on the history tests,
  the Sphinx build, a Windows installer build, `check/fmt`, `check/pyupgrade`, `check/mypy`, plus
  a pyqt5/pyqt6 paint-smoke matrix and a macOS job. `build.yml` adds SonarQube.

## Traps that have already cost a cycle

Consult `references/gotchas.md` for the full list with evidence. The short version:

- `QMainWindow.saveState()` serializes **only dock/toolbar topology**. Splitters inside a dock
  are not part of it, so adding one needs no `widget_version` bump — and bumping it invalidates
  every user's saved layout plus two hard-coded test assertions.
- `git show --raw` emits **nothing for merge commits** while `--numstat` still emits the combined
  diff. Any parser over that output must tolerate numstat without raw.
- `qtutils.add_action_bool` connects `triggered[bool]`, not `toggled` — `setChecked()` in a
  constructor does **not** invoke the callback. Existing code calls the handler explicitly.
- Shortcuts from `qtutils.add_action` are `Qt.WidgetWithChildrenShortcut`-scoped, so duplicate
  widgets in one window do not collide.
- `FileWidget.commits_selected` runs git **synchronously** and a test name says so. Schedule
  policy belongs in the host, not in the shared widget.
