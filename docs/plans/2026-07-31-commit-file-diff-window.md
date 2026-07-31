---
status: completed
completed_at: 2026-07-31
plan_commit: 035e8cf1
implementation_branch: tree-ui/diff-view/minimax-M3
implementation_head: c73ec4a26b412577560323cf12e58accd53d3f79
ci_run: nicht ausgefuehrt (lokal gruen)
manual_verification: |
  - Doppelklick oeffnet das Fenster mit dem Diff genau dieser Datei
  - Diff bleibt nach 1 s der Dateidiff (Debounce-Falle geprueft)
  - Zweiter Doppelklick benutzt dasselbe Fenster
  - Geometrie ueberlebt Schliessen und erneutes Oeffnen
  - Bereichs-Diff bei zwei markierten Commits
  - im DAG-Fenster ebenfalls geprueft
---

# Doppelklick in der Commit-Dateiliste öffnet den Diff in einem Fenster

**Erstellt:** 2026-07-31
**Branch:** wird vor der Umsetzung manuell gesetzt — dieser Plan legt **keinen** Branch an.
**Betrifft:** die Dateiliste aus `View → Display Commit Files`

---

## 0. Wie dieser Plan zu lesen ist

Der Plan ist so geschrieben, dass er **ohne Vorwissen und ohne eigene Entscheidungen**
ausgeführt werden kann.

- **Tasks strikt in der Reihenfolge 0 → 8.** Nichts überspringen.
- **Ein Task = ein Commit.** Die Commit-Message steht am Ende jedes Tasks wörtlich da.
- **Jeder Task hat RED → GREEN → VERIFIKATION.** Steht beim RED-Schritt eine erwartete
  Fehlermeldung, muss die tatsächliche Ausgabe dazu passen. Passt sie nicht: **stoppen und
  melden**, nicht weitermachen.
- **Zeilennummern sind Orientierung, nicht Wahrheit.** Vor jedem Edit steht ein `grep`, der den
  Anker findet. Benutze den `grep`, nicht die Zeilennummer.
- **Nach jedem Task ist die volle Test-Suite grün.**
- Schlägt ein Befehl fehl und der Plan nennt keinen Ausweg: **stoppen und melden.**

Standard-Testbefehle:

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test
```

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_commit_file_diff_test.py test/widgets_history_filelist_test.py
```

---

## 1. Was gebaut wird

Ein Doppelklick auf eine Datei in der Commit-Dateiliste öffnet ein eigenständiges Fenster, das
den Diff **genau dieser Datei** für den aktuell ausgewählten Commit zeigt — in derselben
Diff-Ansicht, die das DAG-Fenster integriert benutzt (`CommitDiffWidget`: Gravatar, Autor,
Commit-ID, Zusammenfassung und der Diff-Text).

Festgelegte Entscheidungen:

| Frage | Entscheidung |
|---|---|
| Wo wirkt der Doppelklick? | In `FileWidget` selbst → die **beiden Listen der Commit-History**: das Panel im Hauptfenster *und* das `file_dock` im DAG-Fenster. Der dritte `FileWidget` im Sequenzeditor bleibt unverdrahtet, siehe §2. |
| Zweiter Doppelklick? | **Dasselbe Fenster** wird wiederverwendet, lädt die neue Datei und kommt nach vorn. Ein Fenster pro Host. |
| Geometrie? | Wird in `~/.config/git-cola/settings` gespeichert und beim nächsten Öffnen wiederhergestellt. |
| Mehrere Commits markiert? | Der Bereichs-Diff dieser Datei über die Auswahl — `CommitDiffWidget` kann das bereits. |

## 2. Nicht-Ziele

- **Kein Diff bei Einfachklick.** Die Auswahl in der Dateiliste bleibt wie sie ist.
- **Kein `diffwidget` am `CommitHistoryWidget`.** Siehe Falle **F1** — ein Test verbietet das.
- **Kein Ersatz für „Launch Diff Tool".** Der externe Difftool-Eintrag im Kontextmenü bleibt
  unangetastet.
- **Keine Bearbeitung im neuen Fenster.** Es ist eine reine Ansicht (`CommitDiffWidget`, nicht
  `DiffEditor`).
- **Kein `widget_version`-Bump.** Weder `MainView` noch `GitDAG` ändern ihre Dock-Topologie.
- **Der Rebase-Sequenzeditor bleibt unverändert.** `cola/sequenceeditor.py:173` legt einen
  **dritten** `FileWidget` an und befüllt ihn über `cola/sequenceeditor.py:226`
  (`self.tree.commits_selected.connect(self.filewidget.commits_selected)`). Nach Task 1 und 2
  merkt er sich also ebenfalls die Commits und sendet `file_diff_requested` — aber **niemand
  hört zu**, ein Doppelklick dort bleibt folgenlos. Das ist Absicht: der Sequenzeditor ist ein
  Rebase-Werkzeug, kein History-Browser. Wer es nachrüsten will, braucht dieselben drei Zeilen
  wie `MainView` in Task 5; die dort emittierten Objekte sind echte `dag.Commit`-Instanzen aus
  einem `RepoReader` (`cola/sequenceeditor.py:549-562`), haben also `.oid` und `.author`.

## 3. Fallen — alle empirisch verifiziert

| # | Falle | Beleg |
|---|---|---|
| **F1** | `test_history_widget_owns_history_state_without_window_children` (`test/widgets_dag_history_test.py:200`) prüft per `assert not hasattr(history, name)` unter anderem `'diffwidget'`. Das `CommitHistoryWidget` darf kein Diff-Widget besitzen. Deshalb hängt das Fenster am **Host**, nicht am History-Widget. | `test/widgets_dag_history_test.py:225-233` |
| **F2** | **Die Debounce-Falle.** `CommitDiffWidget.commits_selected()` startet einen 100-ms-Timer (`DIFF_DEBOUNCE_MSEC`). Ruft man danach `files_selected([pfad])`, lädt der Dateidiff sofort — und **100 ms später überschreibt der Timer ihn mit dem ungefilterten Commit-Diff**. Gemessen: `filename = 'src/a.py'` direkt danach, `filename = None` nach 200 ms, 2 git-Aufrufe statt 1. **Deshalb darf `set_commit_file()` niemals `commits_selected()` benutzen.** | Probe, siehe Task 3 |
| **F3** | `standard.Widget(parent).isWindow()` ist **`False`**. Ohne `setWindowFlags(Qt.Window)` wird daraus kein Fenster, sondern ein unsichtbares Kind-Widget im Elternlayout. | Probe: `standard.Widget(host).isWindow() = False`, nach `setWindowFlags(Qt.Window)` → `True` |
| **F4** | Die Basisklasse ist **`standard.Widget`**, nicht `standard.Dialog`. Gründe: `Browser` (`cola/widgets/browse.py:57`) ist das einzige persistierte, nicht-modale Werkzeugfenster im Projekt und ist ein `standard.Widget`; `Dialog` bringt eine `accept()`/`reject()`-Ergebnissemantik mit, die für einen Betrachter bedeutungslos ist, und `ApplyPatches` zeigt, dass `Dialog` mit Elternteil gern `setWindowModality(Qt.WindowModal)` bekommt — Modalität ist hier ausdrücklich unerwünscht. **Nicht der Grund:** beide Klassen speichern beim Schließen. Gemessen (`close()` *und* echtes Fenster-X): `Widget` → `WidgetMixin.closeEvent` → `save_settings()`; `Dialog` → `QDialog::closeEvent` → `reject()` → `save_settings()`. Je 1 Aufruf. | Probe über beide Schließwege; `cola/widgets/browse.py:57-76`, `cola/widgets/diff.py:2275` |
| **F5** | Es gibt **drei** `FileWidget`-Instanzen in der App, nicht zwei. `GitDAG` hat die eigene im `file_dock` (`cola/widgets/dag.py:2134`) **und** die des enthaltenen `CommitHistoryWidget` (`cola/widgets/dag.py:1667`, dort standardmäßig unsichtbar) — beide müssen in Task 6 verdrahtet werden, sonst funktioniert der Doppelklick je nach eingeschalteter Ansicht mal ja, mal nein. Die dritte sitzt im Rebase-Sequenzeditor (`cola/sequenceeditor.py:173`) und bleibt bewusst unverdrahtet, siehe §2. | `git grep -In "FileWidget(" -- cola` |
| **F6** | `FileWidget` kennt die Commit-ID **nicht**. `commits_selected(commits)` benutzt das Argument nur lokal und speichert nichts. Ohne Task 1 gibt es keinen Weg vom Doppelklick zur OID. | `cola/widgets/filelist.py:67-148` |
| **F7** | In den Tests ist `context.runtask` ein `MagicMock`; `start()` führt den Task **nie aus**. Tests prüfen deshalb den **erzeugten Task** (`runtask.start.call_args`), nicht den Difftext. Genau so macht es `test/diff_debounce_test.py`. | `test/diff_debounce_test.py:42-45` |
| **F8** | **Die Fixture-Falle.** `app_context` (`test/helper.py:85`) setzt **kein** `settings`, es bleibt ein roher `Mock`. Ein `Mock` ist truthy, also nimmt `restore_state()` den Wiederherstellungs-Zweig und reicht `Mock`-Objekte in `QByteArray.fromBase64()` — `TypeError` schon beim Konstruieren des Fensters. Jeder Test, der ein Fenster mit `init_state(context.settings, …)` baut, **muss** vorher `app_context.settings.get_gui_state.return_value = {}` setzen. | Traceback: `fromBase64(...): argument 1 has unexpected type 'Mock'`; die Konvention steht bereits in `test/widgets_dag_history_test.py:293`, `:321`, `:340`, `:373`, `:405` und in `test/widgets_main_history_test.py:114` |
| **F9** | **Zeilennummern verschieben sich innerhalb eines Tasks.** In Task 6 fügen Anker 1 und Anker 2 zusammen 17 Zeilen in `cola/widgets/dag.py` ein, *bevor* Anker 3 drankommt. `GitDAG.closeEvent` wandert dadurch von 2525 auf 2542, und `sed -n '2525,…'` zeigt dann `grab_file`. **Jeder Anker in diesem Plan steuert deshalb über Inhalt, nie über eine Zeilennummer.** Die Nummern in §3 und §4 sind Belege für den Ist-Zustand, keine Sprungziele. | Gemessen an einer Kopie: `grep -n "^    def closeEvent"` liefert vorher `2098, 2525`, nach Anker 1+2 `2098, 2542` |

## 4. Vorhandenes, das wiederverwendet wird (nicht neu bauen)

| Vorhanden | Wo | Rolle in diesem Plan |
|---|---|---|
| `CommitDiffWidget` | `cola/widgets/diff.py:1968` | **Ist** die Diff-Ansicht. Verifiziert: lässt sich mit `options=None` eigenständig bauen. Nichts daran ändern. |
| `CommitDiffWidget.files_selected(filenames)` | `cola/widgets/diff.py:2150` | Filtert den Diff auf eine Datei und beherrscht Einzel-Commit **und** Bereich. Genau die gesuchte API. |
| `CommitDiffWidget.set_details(...)` | `cola/widgets/diff.py:2131` | Setzt OID/Autor/Datum/Zusammenfassung im Kopfbereich. |
| `ApplyPatches` | `cola/widgets/diff.py:2268` | **Präzedenzfall**: ein eigenständiges Fenster in genau dieser Datei, das ein `CommitDiffWidget` hostet. Layout und Aufbau von dort übernehmen. |
| `Browser` | `cola/widgets/browse.py:57` | **Präzedenzfall** für ein persistiertes, nicht-modales Werkzeugfenster: `standard.Widget` + `init_state(context.settings, self.resize, 720, 420)`. Genau dieses Muster kopieren. |
| `qtutils.add_close_action` | `cola/qtutils.py:838` | Gibt dem Fenster Esc/Strg-W zum Schließen. |
| `test/diff_debounce_test.py` | ganze Datei | **Vorlage** für die Fenster-Tests: `qapp`-Fixture, `_make_commit()`-Helfer, `app_context.runtask = MagicMock()`. Nicht neu erfinden. |
| `test/widgets_history_filelist_test.py` | `:20-48` | **Vorlage** für die `FileWidget`-Tests: `qapp` und `managed_qobject` von dort kopieren. |
| `context.browser_windows` | `cola/app.py:823`, `cola/widgets/browse.py:34` | Zeigt das Projektmuster „Host schließt seine Kindfenster im `closeEvent`". Wir brauchen **keine Liste** (nur ein Fenster), übernehmen aber das Schließen. |

---

# TASKS

## Task 0 — Entwicklungsumgebung herstellen

> **Blockierend. Kein Commit.**

1. Prüfen:

```bash
ls -d /home/hermes-agent/Projects/git-fanta/env3 2>/dev/null && echo VORHANDEN || echo FEHLT
```

2. Falls `FEHLT`:

```bash
cd /home/hermes-agent/Projects/git-fanta && garden dev/virtualenv && garden dev
```

3. Falls `garden` fehlt:

```bash
cd /home/hermes-agent/Projects/git-fanta && python3 -m venv --system-site-packages env3 && ./env3/bin/python -m ensurepip --upgrade && ./env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -5
```

**Erwartet:** `NNN passed`, kein `failed`, kein `error`. **Notiere `NNN` als Baseline.**

> Wird das nicht grün: **STOPP.** Ohne Testrunner ist TDD nicht durchführbar.

---

## Task 1 — `FileWidget` merkt sich die angezeigten Commits

**Warum zuerst:** Ohne die Commits gibt es keinen Weg vom Doppelklick zur Commit-ID (Falle **F6**).

### Schritt 1.1 (RED) — Test schreiben

Hänge an `test/widgets_history_filelist_test.py` an:

```python
def _fake_commit(oid, summary='summary'):
    """Ein Commit-Stellvertreter mit den Feldern, die die Diff-Ansicht liest."""
    commit = MagicMock()
    commit.oid = oid
    commit.author = 'A U Thor'
    commit.email = 'author@example.com'
    commit.authdate = '2026-01-01'
    commit.summary = summary
    return commit


def test_commits_selected_remembers_the_commits(qapp, app_context, managed_qobject):
    """Die angezeigten Dateien gehoeren zu einem Commit - der wird gemerkt."""
    widget = managed_qobject(FileWidget(app_context, None))
    commit = _fake_commit('a' * 40)

    widget.commits_selected([commit])

    assert widget.commits == [commit]


def test_empty_selection_forgets_the_commits(qapp, app_context, managed_qobject):
    """Ohne Auswahl bleibt kein Commit uebrig, an dem ein Doppelklick haengt."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.commits_selected([_fake_commit('a' * 40)])

    widget.commits_selected([])

    assert widget.commits == []


def test_new_widget_starts_without_commits(qapp, app_context, managed_qobject):
    widget = managed_qobject(FileWidget(app_context, None))

    assert widget.commits == []
```

Ergänze oben in der Datei den Import. `test/widgets_history_filelist_test.py` hat **noch keinen**
`unittest.mock`-Import — gemessen. Füge **eine Zeile pro Import**, in der stdlib-Gruppe nach
`import sys`, ein:

```python
from unittest.mock import MagicMock
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -12
```

**Erwartete Fehlermeldung — alle drei neuen Tests scheitern mit:**

```
AttributeError: 'FileWidget' object has no attribute 'commits'
```

> Die 7 bestehenden Tests müssen weiterhin passen (`7 passed, 3 failed`).

### Schritt 1.2 (GREEN) — Feld anlegen und füllen

**Anker 1:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "self._columns_initialized = False" cola/widgets/filelist.py
```

Füge **direkt darunter** ein:

```python
        # Die angezeigten Dateien gehoeren zu diesen Commits. Der Doppelklick
        # braucht sie, um den Diff der Datei fuer den richtigen Commit zu oeffnen.
        self.commits = []
```

**Anker 2:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "def commits_selected" -A 5 cola/widgets/filelist.py
```

Ersetze den Kopf der Methode

```python
    def commits_selected(self, commits):
        if not commits:
            self.clear()
            return
```

durch

```python
    def commits_selected(self, commits):
        self.commits = list(commits)
        if not commits:
            self.clear()
            return
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py
```

**Erwartet:** `10 passed`.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 3 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: FileWidget merkt sich die Commits der angezeigten Dateien

Vorbereitung fuer den Doppelklick-Diff: ohne die Commit-ID kann die
Dateiliste keinen Diff fuer die richtige Revision anfordern."
```

---

## Task 2 — Doppelklick sendet ein Signal

### Schritt 2.1 (RED) — Test schreiben

Hänge an `test/widgets_history_filelist_test.py` an:

```python
def _double_click_first_item(widget):
    """Loest den Doppelklick so aus, wie Qt es beim Anwender tun wuerde."""
    item = widget.topLevelItem(0)
    widget.itemDoubleClicked.emit(item, 0)
    return item


def test_double_click_requests_the_file_diff(qapp, app_context, managed_qobject):
    """Ein Doppelklick meldet Commits und Pfad nach aussen."""
    widget = managed_qobject(FileWidget(app_context, None))
    commit = _fake_commit('a' * 40)
    widget.commits_selected([commit])
    widget.list_files(['3\t1\tsrc/a.py'])
    received = []
    widget.file_diff_requested.connect(
        lambda commits, path: received.append((commits, path))
    )

    _double_click_first_item(widget)
    qapp.processEvents()

    assert received == [([commit], 'src/a.py')]


def test_double_click_without_commits_is_ignored(qapp, app_context, managed_qobject):
    """Ohne bekannten Commit gibt es nichts zu diffen - kein Signal."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.list_files(['3\t1\tsrc/a.py'])
    received = []
    widget.file_diff_requested.connect(
        lambda commits, path: received.append((commits, path))
    )

    _double_click_first_item(widget)
    qapp.processEvents()

    assert received == []


def test_double_click_emits_a_copy_of_the_commits(qapp, app_context, managed_qobject):
    """Der Empfaenger bekommt eine Kopie, keine Referenz auf den Widget-Zustand."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.commits_selected([_fake_commit('a' * 40)])
    widget.list_files(['3\t1\tsrc/a.py'])
    received = []
    widget.file_diff_requested.connect(lambda commits, path: received.append(commits))

    _double_click_first_item(widget)
    qapp.processEvents()

    assert received[0] is not widget.commits
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -12
```

**Erwartete Fehlermeldung — alle drei neuen Tests:**

```
AttributeError: 'FileWidget' object has no attribute 'file_diff_requested'
```

### Schritt 2.2 (GREEN) — Signal und Handler

**Anker 1 — Signalliste:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "difftool_selected = Signal" cola/widgets/filelist.py
```

Füge **direkt darunter** ein:

```python
    file_diff_requested = Signal(object, object)
```

**Anker 2 — Verbindung:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "self.itemSelectionChanged.connect" cola/widgets/filelist.py
```

Füge **direkt darunter** ein:

```python
        self.itemDoubleClicked.connect(self._file_double_clicked)
```

**Anker 3 — Handler:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    def selection_changed" -A 4 cola/widgets/filelist.py
```

Füge **direkt nach** der Methode `selection_changed` ein (also vor `def commits_selected`):

```python
    def _file_double_clicked(self, item, _column):
        """Fordert den Diff der doppelgeklickten Datei an.

        Die Liste der Commits wird kopiert, damit der Empfaenger sie behalten
        kann, waehrend sich die Auswahl im Widget weiterbewegt.
        """
        path = getattr(item, 'path', '')
        if not path or not self.commits:
            return
        self.file_diff_requested.emit(list(self.commits), path)
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py
```

**Erwartet:** `13 passed`.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 6 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: FileWidget meldet Doppelklick als file_diff_requested

Das Signal traegt die Commits und den Pfad. Was damit geschieht,
entscheidet der Host - wie bei difftool_selected und histories_selected."
```

---

## Task 3 — Das Diff-Fenster

**Ziel:** Eine Fensterklasse in `cola/widgets/diff.py`, die einen `CommitDiffWidget` hostet und
den Diff **einer** Datei zeigt.

> **Der wichtigste Teil dieses Tasks ist `set_commit_file()`.** Es darf `commits_selected()`
> **nicht** benutzen — siehe Falle **F2**. Der Test `test_set_commit_file_survives_the_debounce`
> ist genau dafür da.

### Schritt 3.1 (RED) — Testdatei anlegen

Neue Datei `test/widgets_commit_file_diff_test.py`:

```python
# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Tests fuer das eigenstaendige Diff-Fenster der Commit-Dateiliste."""

import sys
from unittest.mock import MagicMock

import pytest

from cola.widgets.diff import CommitFileDiffWindow
from cola.widgets.diff import DiffInfoTask
from cola.widgets.diff import DiffRangeTask
from cola.widgets.diff import show_commit_file_diff
from qtpy import QtCore
from qtpy import QtTest
from qtpy import QtWidgets

from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


@pytest.fixture(scope='module')
def qapp():
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


@pytest.fixture
def managed_qobject(qapp):
    objects = []

    def manage(obj):
        objects.append(obj)
        return obj

    yield manage

    qapp.processEvents()
    for obj in reversed(objects):
        if isinstance(obj, QtWidgets.QWidget):
            obj.close()
    qapp.processEvents()
    for obj in reversed(objects):
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    qapp.processEvents()


def _fake_commit(oid, summary='summary'):
    commit = MagicMock()
    commit.oid = oid
    commit.author = 'A U Thor'
    commit.email = 'author@example.com'
    commit.authdate = '2026-01-01'
    commit.summary = summary
    return commit


def _prepare_context(app_context):
    """Macht app_context tauglich fuer ein Fenster mit gespeicherter Geometrie.

    app_context (test/helper.py) setzt kein settings, es bleibt also ein roher
    Mock. Ein Mock ist truthy, weshalb restore_state() den Wiederherstellungs-
    Zweig nimmt und Mocks in QByteArray.fromBase64() reicht - das wirft einen
    TypeError schon beim Konstruieren. Dieselbe Zeile benutzen die bestehenden
    DAG-Tests (test/widgets_dag_history_test.py:293 und weitere).
    """
    app_context.runtask = MagicMock()
    app_context.settings.get_gui_state.return_value = {}
    return app_context


def _window(app_context, managed_qobject):
    """Baut das Fenster und beobachtet die Diff-Tasks statt echtes git zu rufen."""
    _prepare_context(app_context)
    return managed_qobject(CommitFileDiffWindow(app_context))


def _last_task(app_context):
    return app_context.runtask.start.call_args[0][0]


def test_window_is_a_top_level_window(qapp, app_context, managed_qobject):
    """Das Fenster muss ein eigenes Fenster sein, kein eingebettetes Kind-Widget."""
    window = _window(app_context, managed_qobject)

    assert window.isWindow()


def test_set_commit_file_loads_only_that_file(qapp, app_context, managed_qobject):
    """Genau ein Diff-Task, gefiltert auf die uebergebene Datei."""
    window = _window(app_context, managed_qobject)
    commit = _fake_commit('a' * 40)

    window.set_commit_file([commit], 'src/a.py')

    assert app_context.runtask.start.call_count == 1
    task = _last_task(app_context)
    assert isinstance(task, DiffInfoTask)
    assert task.oid == 'a' * 40
    assert task.filename == 'src/a.py'


def test_set_commit_file_survives_the_debounce(qapp, app_context, managed_qobject):
    """Der Dateifilter darf nicht 100 ms spaeter vom Debounce ueberschrieben werden.

    CommitDiffWidget.commits_selected() startet einen Timer, der den Diff des
    ganzen Commits nachlaedt. Wuerde set_commit_file() diesen Weg nehmen, ersetzte
    der Timer den Dateidiff durch den Commit-Diff (filename=None).
    """
    window = _window(app_context, managed_qobject)

    window.set_commit_file([_fake_commit('a' * 40)], 'src/a.py')
    QtTest.QTest.qWait(3 * window.diffwidget.DIFF_DEBOUNCE_MSEC)
    qapp.processEvents()

    assert app_context.runtask.start.call_count == 1
    assert _last_task(app_context).filename == 'src/a.py'


def test_set_commit_file_uses_a_range_for_multiple_commits(
    qapp, app_context, managed_qobject
):
    """Bei mehreren markierten Commits wird der Bereichs-Diff der Datei geladen."""
    window = _window(app_context, managed_qobject)
    first = _fake_commit('a' * 40)
    last = _fake_commit('b' * 40)

    window.set_commit_file([first, last], 'src/a.py')

    task = _last_task(app_context)
    assert isinstance(task, DiffRangeTask)
    assert task.filename == 'src/a.py'


def test_set_commit_file_shows_the_commit_metadata(qapp, app_context, managed_qobject):
    """Der Kopfbereich zeigt den Commit, zu dem der Dateidiff gehoert.

    Die Zusammenfassung ist bewusst kurz: summary_label ist ein PlainTextLabel,
    das lange Texte fuer die Anzeige elidiert. Bei kurzem Text liefert text()
    nachweislich den vollen Wert zurueck.
    """
    window = _window(app_context, managed_qobject)

    window.set_commit_file([_fake_commit('a' * 40, summary='Titel')], 'src/a.py')

    assert window.diffwidget.summary_label.text() == 'Titel'


def test_set_commit_file_without_commits_does_nothing(
    qapp, app_context, managed_qobject
):
    window = _window(app_context, managed_qobject)

    window.set_commit_file([], 'src/a.py')

    app_context.runtask.start.assert_not_called()


def test_window_title_names_the_file(qapp, app_context, managed_qobject):
    window = _window(app_context, managed_qobject)

    window.set_commit_file([_fake_commit('a' * 40)], 'src/a.py')

    assert 'src/a.py' in window.windowTitle()


def test_window_geometry_survives_a_state_roundtrip(
    qapp, app_context, managed_qobject
):
    """Groesse und Position ueberleben Schliessen und erneutes Oeffnen.

    Das ist die Anforderung, wegen der das Fenster ein standard.Widget ist und
    kein standard.Dialog (siehe Falle F4). Ohne diesen Test wuerde ein Wechsel
    der Basisklasse unbemerkt die gespeicherte Geometrie verlieren.
    """
    window = _window(app_context, managed_qobject)
    window.resize(640, 400)

    state = window.export_state()

    assert state['width'] == 640
    assert state['height'] == 400

    # Ein zweites Fenster, das diesen State vorfindet, oeffnet in derselben Groesse.
    app_context.settings.get_gui_state.return_value = state
    restored = managed_qobject(CommitFileDiffWindow(app_context))

    assert (restored.width(), restored.height()) == (640, 400)


def test_window_saves_its_state_on_close(qapp, app_context, managed_qobject):
    """Beim Schliessen wird save_settings() gerufen - sonst gaebe es nichts zu laden.

    Bei standard.Widget laeuft das ueber WidgetMixin.closeEvent. Der Test haelt
    die Kette fest, damit ein Umbau der Basisklasse oder ein eigenes closeEvent
    das Speichern nicht stillschweigend abschaltet.
    """
    window = _window(app_context, managed_qobject)
    calls = []
    window.save_settings = lambda settings=None: calls.append(settings)

    window.close()

    assert len(calls) == 1
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_commit_file_diff_test.py 2>&1 | tail -12
```

**Erwartete Fehlermeldung — die ganze Datei scheitert schon beim Einsammeln:**

```
ImportError: cannot import name 'CommitFileDiffWindow' from 'cola.widgets.diff'
```

> Das ist ein **Collection-Error**, kein einzelner Testfehler — hier ist das korrekt und
> beabsichtigt, weil die Klasse noch gar nicht existiert. `show_commit_file_diff` kommt erst in
> Task 4 dazu; bis dahin bleibt der Import in der Testdatei rot. **Deshalb wird Task 3 und
> Task 4 zusammen grün**, siehe Hinweis am Ende von Task 3.

### Schritt 3.2 (GREEN) — Klasse anlegen

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^class ApplyPatches" cola/widgets/diff.py
```

Füge **direkt vor** `class ApplyPatches(standard.Dialog):` ein:

```python
class CommitFileDiffWindow(standard.Widget):
    """Zeigt den Diff einer einzelnen Datei fuer die ausgewaehlten Commits"""

    def __init__(self, context, parent=None):
        standard.Widget.__init__(self, parent)
        self.context = context
        # Ein standard.Widget mit Elternteil ist per Default KEIN eigenes Fenster.
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle(N_('Commit File Diff'))

        self.diffwidget = CommitDiffWidget(context, self, is_commit=True)
        self.main_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.diffwidget
        )
        self.setLayout(self.main_layout)
        qtutils.add_close_action(self)

        self.init_state(context.settings, self.resize, 720, 480)

    def set_commit_file(self, commits, filename):
        """Zeigt `filename` so, wie `commits` ihn veraendert haben"""
        if not commits or not filename:
            return
        diffwidget = self.diffwidget
        commit = commits[-1]
        diffwidget.set_details(
            commit.oid,
            commit.author or '',
            commit.email or '',
            commit.authdate or '',
            commit.summary or '',
        )
        # Der Commit-Zustand wird hier direkt gesetzt statt ueber
        # commits_selected(). Jenes startet einen 100-ms-Debounce, der nach
        # files_selected() feuern und den Dateidiff durch den Diff des ganzen
        # Commits ersetzen wuerde.
        # GitDAG setzt dieselben drei Felder ebenfalls direkt
        # (cola/widgets/dag.py:2291-2293); das ist der etablierte Zugriffsweg
        # auf CommitDiffWidget, kein Umgehen der Kapselung.
        diffwidget.oid = commit.oid
        if len(commits) > 1:
            diffwidget.oid_start = commits[0]
            diffwidget.oid_end = commits[-1]
        else:
            diffwidget.oid_start = None
            diffwidget.oid_end = None
        diffwidget.files_selected([filename])
        self.setWindowTitle(
            N_('%(filename)s - %(oid)s')
            % {'filename': filename, 'oid': commit.oid[:12]}
        )
```

> **Warum `standard.Widget` und nicht `standard.Dialog`:** siehe Falle **F4**. Kurz: `Browser`
> (`cola/widgets/browse.py:57-76`) ist das Projektmuster für ein persistiertes, nicht-modales
> Werkzeugfenster, und `Dialog` bringt eine `accept()`/`reject()`-Semantik plus die Neigung zur
> Modalität mit, die hier beide nichts zu suchen haben. **Beide Klassen speichern beim
> Schließen** — das ist kein Unterscheidungsmerkmal, auch wenn es naheliegt.

**Importe prüfen** — alle vier werden gebraucht und sind bereits vorhanden:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^from \.\. import qtutils$\|^from \.\.i18n import N_$\|^from \. import defs$\|^from \. import standard$\|^from qtpy.QtCore import Qt$" cola/widgets/diff.py
```

**Erwartet:** fünf Treffer. Fehlt einer, **stoppen und melden** — dann stimmt etwas anderes nicht.

> Task 3 endet **rot**, weil `test/widgets_commit_file_diff_test.py` zusätzlich
> `show_commit_file_diff` importiert. Das ist beabsichtigt und wird in Task 4 aufgelöst.
> **Committe Task 3 noch nicht** — Task 3 und Task 4 bilden zusammen einen Commit.

---

## Task 4 — Wiederverwendbares Öffnen

**Ziel:** Eine Funktion, die das Fenster anlegt **oder** wiederverwendet. Damit steht die
Wiederverwendungslogik an genau einer Stelle statt in jedem Host.

### Schritt 4.1 (RED) — Tests ergänzen

Hänge an `test/widgets_commit_file_diff_test.py` an:

```python
def test_show_creates_a_window_when_none_exists(qapp, app_context, managed_qobject):
    _prepare_context(app_context)

    window = show_commit_file_diff(
        app_context, None, [_fake_commit('a' * 40)], 'src/a.py'
    )
    managed_qobject(window)

    assert isinstance(window, CommitFileDiffWindow)
    assert window.isVisible()


def test_show_reuses_the_given_window(qapp, app_context, managed_qobject):
    """Der zweite Doppelklick oeffnet kein zweites Fenster."""
    _prepare_context(app_context)
    first = show_commit_file_diff(
        app_context, None, [_fake_commit('a' * 40)], 'src/a.py'
    )
    managed_qobject(first)

    second = show_commit_file_diff(
        app_context, None, [_fake_commit('b' * 40)], 'src/b.py', window=first
    )

    assert second is first
    assert 'src/b.py' in first.windowTitle()


def test_show_loads_the_new_file_into_the_reused_window(
    qapp, app_context, managed_qobject
):
    _prepare_context(app_context)
    window = managed_qobject(CommitFileDiffWindow(app_context))

    show_commit_file_diff(
        app_context, None, [_fake_commit('a' * 40)], 'src/b.py', window=window
    )

    assert _last_task(app_context).filename == 'src/b.py'
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_commit_file_diff_test.py 2>&1 | tail -8
```

**Erwartete Fehlermeldung — weiterhin der Collection-Error:**

```
ImportError: cannot import name 'show_commit_file_diff' from 'cola.widgets.diff'
```

### Schritt 4.2 (GREEN) — Funktion anlegen

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^def apply_patches" cola/widgets/diff.py
```

Füge **direkt vor** `def apply_patches(context, patches=None):` ein:

```python
def show_commit_file_diff(context, parent, commits, filename, window=None):
    """Zeigt den Diff einer Datei in einem wiederverwendbaren Fenster

    Ohne `window` wird eins angelegt. Der Rueckgabewert ist das benutzte Fenster;
    der Aufrufer haelt ihn fest, damit der naechste Aufruf dasselbe Fenster
    wiederverwendet statt ein zweites zu oeffnen.
    """
    if window is None:
        window = CommitFileDiffWindow(context, parent=parent)
    window.set_commit_file(commits, filename)
    window.show()
    window.raise_()
    window.activateWindow()
    return window
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_commit_file_diff_test.py
```

**Erwartet:** `12 passed`.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 18 passed, 0 failed.

**Prüfen, dass Falle F1 nicht verletzt wurde:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k without_window_children
```

**Erwartet:** `1 passed`.

### Commit (Task 3 + Task 4 gemeinsam)

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: eigenstaendiges Fenster fuer den Diff einer Commit-Datei

CommitFileDiffWindow hostet den vorhandenen CommitDiffWidget. set_commit_file()
setzt den Commit-Zustand direkt statt ueber commits_selected(), weil dessen
100-ms-Debounce den Dateifilter sonst wieder ueberschreiben wuerde.

Basis ist standard.Widget, nicht standard.Dialog: nur ersteres speichert die
Fenstergeometrie beim Schliessen."
```

---

## Task 5 — Verdrahtung im Hauptfenster

### Schritt 5.1 (RED) — Test schreiben

Hänge an `test/widgets_main_history_test.py` an:

```python
def test_double_click_in_file_panel_opens_the_diff_window(
    qapp, main_context, managed_qobject
):
    """Ein Doppelklick im Datei-Panel oeffnet das Diff-Fenster des Hauptfensters."""
    main_context.runtask = Mock()
    view = managed_qobject(MainView(main_context))
    filewidget = view.historywidget.filewidget
    commit = Mock()
    commit.oid = 'a' * 40
    commit.author = 'A U Thor'
    commit.email = 'author@example.com'
    commit.authdate = '2026-01-01'
    commit.summary = 'summary'
    filewidget.commits_selected([commit])
    filewidget.list_files(['3\t1\tsrc/a.py'])

    filewidget.itemDoubleClicked.emit(filewidget.topLevelItem(0), 0)
    qapp.processEvents()

    assert view.commit_file_diff_window is not None
    assert 'src/a.py' in view.commit_file_diff_window.windowTitle()


def test_second_double_click_reuses_the_diff_window(
    qapp, main_context, managed_qobject
):
    main_context.runtask = Mock()
    view = managed_qobject(MainView(main_context))
    filewidget = view.historywidget.filewidget
    commit = Mock()
    commit.oid = 'a' * 40
    commit.author = 'A U Thor'
    commit.email = 'author@example.com'
    commit.authdate = '2026-01-01'
    commit.summary = 'summary'
    filewidget.commits_selected([commit])
    filewidget.list_files(['3\t1\tsrc/a.py', '0\t2\tsrc/b.py'])

    filewidget.itemDoubleClicked.emit(filewidget.topLevelItem(0), 0)
    qapp.processEvents()
    first_window = view.commit_file_diff_window
    filewidget.itemDoubleClicked.emit(filewidget.topLevelItem(1), 0)
    qapp.processEvents()

    assert view.commit_file_diff_window is first_window
    assert 'src/b.py' in first_window.windowTitle()


def test_main_view_starts_without_a_diff_window(qapp, main_context, managed_qobject):
    view = managed_qobject(MainView(main_context))

    assert view.commit_file_diff_window is None
```

> **Kein neuer Import nötig, und `Mock` gibt es hier bewusst nicht.**
> `test/widgets_main_history_test.py:10` importiert `Mock` (nicht `Mock`) — gemessen. Die
> Tests oben benutzen deshalb `Mock`. Schreibe **nicht** `Mock` in diese Datei und füge
> keinen Import hinzu.
>
> Die Fixtures sind vorhanden: `qapp` (`:80`), `managed_qobject` (`:90`), `main_context` (`:111`).
> Der Bau-Aufruf `managed_qobject(MainView(main_context))` ist der Bestandsstil (z. B. `:260`).
> Zur Kontrolle:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "^def main_context\|^def managed_qobject\|^def qapp\|from unittest.mock import" test/widgets_main_history_test.py
> ```
> **Erwartet:** vier Treffer — `Mock`-Import bei 10, `qapp` bei 80, `managed_qobject` bei 90,
> `main_context` bei 111. Weicht das ab, **stoppen und melden**.

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_main_history_test.py -k diff_window 2>&1 | tail -10
```

**Erwartete Fehlermeldung:**

```
AttributeError: 'MainView' object has no attribute 'commit_file_diff_window'
```

### Schritt 5.2 (GREEN) — Feld, Verbindung, Handler

**Anker 1:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "self.model.updated.disconnect(self.historywidget.model_updated)" cola/widgets/main.py
```

Füge **direkt darüber** ein:

```python
        # Ein wiederverwendetes Fenster fuer den Diff einer doppelgeklickten Datei.
        self.commit_file_diff_window = None
        self.historywidget.filewidget.file_diff_requested.connect(
            self._show_commit_file_diff, type=Qt.QueuedConnection
        )
```

**Anker 2 — Handler.** Suche das Ende der `closeEvent`-Methode:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    def create_view_menu" cola/widgets/main.py
```

Füge **direkt davor** ein:

```python
    def _show_commit_file_diff(self, commits, filename):
        """Zeigt den Diff der doppelgeklickten Datei in einem eigenen Fenster"""
        self.commit_file_diff_window = diff.show_commit_file_diff(
            self.context,
            self,
            commits,
            filename,
            window=self.commit_file_diff_window,
        )
```

**Anker 3 — Fenster beim Schließen mitschließen**, damit seine Geometrie gespeichert wird:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "for browser in list(self.context.browser_windows):" -A 2 cola/widgets/main.py
```

Füge **direkt nach** der `browser.close()`-Schleife ein:

```python
        if self.commit_file_diff_window is not None:
            self.commit_file_diff_window.close()
```

> **Warum explizit:** Qt zerstört Kind-Widgets zusammen mit dem Elternteil, **ohne** ein
> `closeEvent` zu senden. Ohne diesen Aufruf würde `WidgetMixin.closeEvent` nie laufen und die
> Fenstergeometrie nie gespeichert. Dasselbe Muster benutzt das Projekt schon für
> `context.browser_windows`.

**Prüfe die benötigten Importe** — beide sind vorhanden (`cola/widgets/main.py:41` `from . import
diff`, und `Qt` aus `qtpy.QtCore`):

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^from . import diff$\|^from qtpy.QtCore import Qt$" cola/widgets/main.py
```

**Erwartet:** zwei Treffer.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_main_history_test.py
```

**Erwartet:** alle passed.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 21 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: Doppelklick im Datei-Panel oeffnet den Diff im Hauptfenster

MainView haelt genau ein Diff-Fenster und schliesst es im closeEvent, damit
die Fenstergeometrie gespeichert wird."
```

---

## Task 6 — Verdrahtung im DAG-Fenster

**Ziel:** Derselbe Doppelklick im eigenständigen DAG-Fenster. Dort gibt es **zwei**
`FileWidget`-Instanzen (Falle **F5**) — beide werden verdrahtet, beide teilen sich ein Fenster.

### Schritt 6.1 (RED) — Test schreiben

Hänge an `test/widgets_dag_history_test.py` an:

```python
def test_dag_file_dock_double_click_opens_the_diff_window(
    qapp, app_context, managed_qobject
):
    """Der Doppelklick im file_dock des DAG-Fensters oeffnet das Diff-Fenster."""
    app_context.runtask = MagicMock()
    # Roher Mock als settings -> restore_state() reicht Mocks in die Qt-Geometrie-API.
    # Gleiche Zeile wie in den bestehenden DAG-Tests (:293 und weitere).
    app_context.settings.get_gui_state.return_value = {}
    view = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))
    filewidget = view.filewidget
    commit = _dag_commit_stub()
    filewidget.commits_selected([commit])
    filewidget.list_files(['3\t1\tsrc/a.py'])

    filewidget.itemDoubleClicked.emit(filewidget.topLevelItem(0), 0)
    qapp.processEvents()

    assert view.commit_file_diff_window is not None
    assert 'src/a.py' in view.commit_file_diff_window.windowTitle()


def test_dag_inline_file_panel_shares_the_same_diff_window(
    qapp, app_context, managed_qobject
):
    """Beide Dateilisten des DAG-Fensters benutzen dasselbe Diff-Fenster."""
    app_context.runtask = MagicMock()
    # Roher Mock als settings -> restore_state() reicht Mocks in die Qt-Geometrie-API.
    # Gleiche Zeile wie in den bestehenden DAG-Tests (:293 und weitere).
    app_context.settings.get_gui_state.return_value = {}
    view = managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))
    commit = _dag_commit_stub()
    for filewidget, path in (
        (view.filewidget, 'src/a.py'),
        (view.historywidget.filewidget, 'src/b.py'),
    ):
        filewidget.commits_selected([commit])
        filewidget.list_files([f'3\t1\t{path}'])

    view.filewidget.itemDoubleClicked.emit(view.filewidget.topLevelItem(0), 0)
    qapp.processEvents()
    first_window = view.commit_file_diff_window
    inline = view.historywidget.filewidget
    inline.itemDoubleClicked.emit(inline.topLevelItem(0), 0)
    qapp.processEvents()

    assert view.commit_file_diff_window is first_window
    assert 'src/b.py' in first_window.windowTitle()
```

Und den Commit-Stellvertreter, falls die Datei noch keinen passenden hat:

```python
def _dag_commit_stub():
    commit = MagicMock()
    commit.oid = 'a' * 40
    commit.author = 'A U Thor'
    commit.email = 'author@example.com'
    commit.authdate = '2026-01-01'
    commit.summary = 'summary'
    return commit
```

> **Import ergänzen — gemessen: `test/widgets_dag_history_test.py` hat noch gar keinen
> `unittest.mock`-Import.** Füge in der stdlib-Gruppe, eine Zeile pro Import, ein:
> ```python
> from unittest.mock import MagicMock
> ```
> Der Bau-Aufruf `managed_qobject(GitDAG(app_context, dag.DAG('HEAD', 1000)))` ist der
> Bestandsstil dieser Datei (z. B. Zeile 296). Zur Kontrolle:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "GitDAG(app_context, dag.DAG('HEAD', 1000))\|from unittest.mock import" test/widgets_dag_history_test.py | head -4
> ```
> **Erwartet vor deiner Änderung:** mehrere `GitDAG(...)`-Treffer, **kein** `unittest.mock`-Import.
>
> Es gibt in der Datei bereits einen Helfer `_commit(app_context, factory, ...)` — der baut
> **echte** Commits über eine `CommitFactory` und braucht ein Repo. Für diese beiden Tests
> reicht der leichtgewichtige Stellvertreter oben; benutze **nicht** `_commit`.

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k diff_window 2>&1 | tail -10
```

**Erwartete Fehlermeldung:**

```
AttributeError: 'GitDAG' object has no attribute 'commit_file_diff_window'
```

### Schritt 6.2 (GREEN) — beide Dateilisten verdrahten

**Anker 1:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "self.filewidget.difftool_selected.connect" -B 4 cola/widgets/dag.py
```

Füge **direkt vor** der `difftool_selected`-Verbindung ein:

```python
        # Ein wiederverwendetes Fenster fuer beide Dateilisten dieses Fensters:
        # das file_dock und das (standardmaessig verborgene) Panel im History-Widget.
        self.commit_file_diff_window = None
        for file_widget in (self.filewidget, self.historywidget.filewidget):
            file_widget.file_diff_requested.connect(
                self._show_commit_file_diff, type=Qt.QueuedConnection
            )
```

**Anker 2 — Handler.** Suche eine bestehende Methode von `GitDAG`, hinter die er passt:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    def export_state" cola/widgets/dag.py | tail -1
```

Füge **direkt vor** dieser `export_state`-Methode ein:

```python
    def _show_commit_file_diff(self, commits, filename):
        """Zeigt den Diff der doppelgeklickten Datei in einem eigenen Fenster"""
        self.commit_file_diff_window = diff.show_commit_file_diff(
            self.context,
            self,
            commits,
            filename,
            window=self.commit_file_diff_window,
        )
```

**Anker 3 — beim Schließen mitschließen.**

> **Keine Zeilennummern benutzen.** Es gibt zwei `closeEvent`-Methoden in `cola/widgets/dag.py`,
> und die Einfügungen aus Anker 1 und Anker 2 verschieben die zweite um 17 Zeilen nach unten
> (gemessen: von 2525 auf 2542). Wer hier nach einer Zeilennummer greift, landet in
> `grab_file`. Deshalb wird über den **Inhalt** angesteuert.

Der Rumpf von `GitDAG.closeEvent` ist im Projekt eindeutig — `self.historywidget.close_popup()`
kommt in der ganzen Datei genau einmal vor:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -c "self.historywidget.close_popup()" cola/widgets/dag.py
```

**Erwartet:** `1`.

Ersetze diesen **kompletten Block**:

```python
    def closeEvent(self, event):
        self.historywidget.close_popup()
        self.historywidget.stop_and_wait()
        standard.MainWindow.closeEvent(self, event)
```

durch:

```python
    def closeEvent(self, event):
        if self.commit_file_diff_window is not None:
            self.commit_file_diff_window.close()
        self.historywidget.close_popup()
        self.historywidget.stop_and_wait()
        standard.MainWindow.closeEvent(self, event)
```

**Kontrolle:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n -A 5 "^    def closeEvent" cola/widgets/dag.py | grep -B 2 "close_popup"
```

**Erwartet:** die neue `if`-Zeile steht direkt über `self.historywidget.close_popup()`.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py
```

**Erwartet:** alle passed — **inklusive** `test_history_widget_owns_history_state_without_window_children`.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 23 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: Doppelklick-Diff auch im eigenstaendigen DAG-Fenster

Beide Dateilisten des DAG-Fensters - das file_dock und das inline-Panel des
History-Widgets - teilen sich ein wiederverwendetes Diff-Fenster."
```

---

## Task 7 — Alle Gates lokal durchlaufen

```bash
cd /home/hermes-agent/Projects/git-fanta && garden check/fmt
```

**Erwartet:** keine Änderungsvorschläge.

```bash
cd /home/hermes-agent/Projects/git-fanta && garden check/pyupgrade && garden check/mypy
```

**Erwartet:** keine Ausgabe bzw. `Success` oder dieselbe Fehlerzahl wie vor Task 1. **Neue**
mypy-Fehler müssen behoben werden.

```bash
cd /home/hermes-agent/Projects/git-fanta && ./env3/bin/python -m ruff check test/widgets_commit_file_diff_test.py test/widgets_history_filelist_test.py cola/widgets/diff.py cola/widgets/filelist.py
```

**Erwartet:** `All checks passed!`

**Qt-Bindings-Matrix wie in der CI:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_API=pyqt5 QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_API=pyqt6 QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

> Ist PyQt6 nicht installiert, bricht der Lauf mit einem Import-Fehler ab. Das ist dann **kein**
> Feature-Problem — melden und weitermachen.

### Manueller Smoke-Test — Pflicht

Kein Test deckt das echte Fenster ab. Starte die App:

```bash
cd /home/hermes-agent/Projects/git-fanta && garden run
```

Prüfe der Reihe nach:

1. `View → Display Commit Files` ist eingeschaltet, rechts neben der History steht die Dateiliste.
2. Einen Commit auswählen → Dateien erscheinen.
3. **Doppelklick auf eine Datei** → ein neues Fenster geht auf, zeigt Autor, Commit-ID,
   Zusammenfassung und den Diff **nur dieser Datei**.
4. **Eine Sekunde warten.** Der Diff muss der Dateidiff bleiben und darf **nicht** zum Diff des
   ganzen Commits umspringen. (Das ist Falle **F2** von Hand geprüft.)
5. **Doppelklick auf eine zweite Datei** → dasselbe Fenster zeigt jetzt die zweite Datei und
   kommt nach vorn. Es öffnet sich **kein** zweites Fenster.
6. Fenster verschieben und in der Größe ändern, schließen, erneut doppelklicken →
   Größe und Position sind erhalten.
7. **Zwei Commits markieren**, dann doppelklicken → der Diff zeigt die Änderungen der Datei
   über den Bereich.
8. Hauptfenster schließen → das Diff-Fenster verschwindet mit.

Dann dasselbe im eigenständigen DAG-Fenster (`View → Git DAG` bzw. `git dag`), Punkt 3 und 5.

### Commit

Nur falls die Gates Änderungen erzwungen haben:

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "style: garden fmt nach dem Doppelklick-Diff-Feature"
```

---

## Task 8 — Dokumentation und Planabschluss

### Schritt 8.1 — `fork-history.md` korrigieren

Die Datei behauptet aktuell das Gegenteil des neuen Zustands.

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "Deliberately not done" .claude/skills/project-brief/references/fork-history.md
```

Ersetze den Absatz

```
**Deliberately not done:** clicking a file does not show its diff. The hook for that later is
`historywidget.filewidget.files_selected` → `MainView.diffviewer`, and it carries its own
mode/`DiffLoading` semantics.
```

durch

```
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
```

### Schritt 8.2 — neue Testdatei im Brief eintragen

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "test/diff_debounce_test.py" .claude/skills/project-brief/references/fork-history.md
```

Füge unter „Where the fork's tests live" eine Zeile hinzu:

```markdown
- `test/widgets_commit_file_diff_test.py` — `CommitFileDiffWindow`, the single-file diff
  seeding, window reuse, and the debounce regression guard.
```

### Schritt 8.3 — Frontmatter ergänzen

Setze **an den Anfang** dieser Plandatei:

```yaml
---
status: completed
completed_at: <YYYY-MM-DD>
plan_commit: <sha des plan:-Commits>
implementation_branch: <der beim Coding gesetzte Branch>
implementation_head: <sha des letzten Commits>
ci_run: <URL oder "nicht ausgefuehrt">
manual_verification: |
  - Doppelklick oeffnet das Fenster mit dem Diff genau dieser Datei
  - Diff bleibt nach 1 s der Dateidiff (Debounce-Falle geprueft)
  - Zweiter Doppelklick benutzt dasselbe Fenster
  - Geometrie ueberlebt Schliessen und erneutes Oeffnen
  - Bereichs-Diff bei zwei markierten Commits
  - im DAG-Fenster ebenfalls geprueft
---
```

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "docs: dokumentiere den Doppelklick-Diff im project-brief"
```

---

## Abschluss-Checkliste

| # | Prüfung | Wie |
|---|---|---|
| 1 | Doppelklick liefert Commits + Pfad | `test_double_click_requests_the_file_diff` |
| 2 | Genau ein git-Aufruf, gefiltert auf die Datei | `test_set_commit_file_loads_only_that_file` |
| 3 | **Debounce überschreibt den Filter nicht** | `test_set_commit_file_survives_the_debounce` |
| 4 | Bereichs-Diff bei mehreren Commits | `test_set_commit_file_uses_a_range_for_multiple_commits` |
| 5 | Es ist wirklich ein Fenster | `test_window_is_a_top_level_window` |
| 6 | Zweiter Doppelklick öffnet kein zweites Fenster | `test_second_double_click_reuses_the_diff_window` |
| 7 | History-Widget besitzt weiterhin kein Diff-Widget | `test_history_widget_owns_history_state_without_window_children` |
| 8 | Beide DAG-Dateilisten teilen ein Fenster | `test_dag_inline_file_panel_shares_the_same_diff_window` |
| 9 | Volle Suite grün | `pytest -q cola test` |
| 10 | fmt / pyupgrade / mypy / ruff | `garden check/fmt check/pyupgrade check/mypy` |
| 11 | pyqt5 + pyqt6 | `QT_API=… pytest -q cola test` |
| 12 | Manueller Smoke-Test, 8 Punkte | Task 7 |

## Bewusst offengelassen

- **Kein Diff bei Einfachklick.** Der `files_selected`-Hook bleibt frei; wer den integrierten
  Diffviewer des Hauptfensters daran hängen will, braucht eigene `DiffLoading`-Semantik.
- **Kein Tastaturweg.** Enter/Return in der Dateiliste öffnet das Fenster nicht. Wenn das
  gewünscht ist: `itemActivated` zusätzlich zu `itemDoubleClicked` verbinden — auf manchen
  Plattformen feuert `itemActivated` allerdings auch bei Einfachklick, das braucht dann einen
  eigenen Test.
- **Ein Fenster pro Host, nicht pro Datei.** Zwei Dateien nebeneinander vergleichen geht nicht.
  Dafür bräuchte es eine Fensterliste am `ApplicationContext` nach dem Vorbild von
  `context.browser_windows` (`cola/app.py:823`).
