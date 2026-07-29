# Commit-Dateiliste im History-Dock – Implementierungsplan

> **Für Hermes:** Verwende den `plan`-Skill und führe die Tasks mit TDD + unabhängigem Doppel-Review pro Task aus.

**Ziel:** Ein Datei-Panel, das pro ausgewähltem Commit im History-Dock des Hauptfensters die geänderten Dateien auflistet – inspiriert von GitKraken/SourceTree, ohne Diff-Inhalt (nur Dateinamen, +/- Statistik).

**Architektur:** Wiederverwendung des existierenden `filelist.FileWidget`, das bereits `commits_selected`-Signale verarbeitet und `git show --numstat`/`git diff` ausführt. Das Widget wird als eigener Dock („History-Dateien") in `MainView` eingebettet und über das `commits_selected`-Signal des `CommitHistoryWidget`-TreeWidgets angesteuert – exakt dasselbe Muster, das `GitDAG` bereits nutzt.

**Tech Stack:** Python 3, PyQt6/PySide6 (via qtpy), Git Cola/Fanta-eigene Widgets (`filelist.FileWidget`, `CommitHistoryWidget`, `qtutils.create_dock`).

---
> **Review-Status:** Critical Plan Review abgeschlossen (deleg_c0c66c6c). 4 BLOCKER + 4 MAJOR behoben.
> Änderungen: Test-Fixtures korrigiert, State-Persistenz mit setVisible/Default, Dock in Menü-Listen, Signal über CommitHistoryWidget, widget_version=3, return False bei Malformed-State.

## Architektur-Kontext

### Bestehende Komponenten (wiederverwenden)

| Komponente | Pfad | Rolle |
|---|---|---|
| `FileWidget` | `cola/widgets/filelist.py` | Listet geänderte Dateien via `commits_selected(commits)` – ruft `git show`/`git diff` auf und zeigt Dateinamen mit +/− Stats |
| `CommitHistoryWidget` | `cola/widgets/dag.py:1588` | History-Tree mit `commits_selected`-Signal (via `treewidget.commits_selected`) |
| `GitDAG` | `cola/widgets/dag.py:2015` | Referenz-Implementierung: verdrahtet `commits_selected` → `filewidget.commits_selected` (Zeile 2055–2056) |
| `MainView` | `cola/widgets/main.py` | Hauptfenster mit `historydock` (Zeile 111), besitzt `CommitHistoryWidget` |

### Signal-Fluss (Referenz: GitDAG)

```
CommitHistoryWidget.treewidget.commits_selected
  → GitDAG._history_selection_changed
    → GitDAG.commits_selected.emit(commits)
      → filewidget.commits_selected(commits)
      → diffwidget.commits_selected(commits)
      → graphview.select_commits(commits)
```

---

## Tasks

### Task 1: Bestehende `FileWidget`-Semantik charakterisieren

**Ziel:** Sicherstellen, dass das existierende `FileWidget`-Verhalten dokumentiert und rückwärtskompatibel getestet ist, bevor es in MainView eingebunden wird.

**Dateien:**
- Create: `test/widgets_history_filelist_test.py`

**RED – Schritt 1: Schreibe Charakterisierungstests**

```python
"""Characterization tests for FileWidget in history context."""

import pytest
from qtpy import QtCore, QtWidgets

from cola.widgets.filelist import FileWidget, FileTreeWidgetItem
from cola.models import dag


def test_filewidget_clears_on_empty_commits(qapp, app_context, managed_qobject):
    """FileWidget.clear() wird bei leerer Commit-Liste aufgerufen."""
    widget = managed_qobject(FileWidget(app_context, None))
    # Vorbereiten: ein Item einfügen
    widget.list_files(["src/foo.py\t10\t5"])
    assert widget.topLevelItemCount() > 0
    # Leere Liste → clear
    widget.commits_selected([])
    assert widget.topLevelItemCount() == 0


def test_filewidget_emits_files_selected_on_selection_change(
    qapp, app_context, managed_qobject
):
    """ItemSelectionChanged löst files_selected mit Pfaden aus."""
    widget = managed_qobject(FileWidget(app_context, None))
    emitted = []
    widget.files_selected.connect(lambda paths: emitted.append(paths))
    widget.list_files(["src/a.py\t3\t1", "src/b.py\t0\t10"])
    # Erstes Item selektieren
    widget.setCurrentItem(widget.topLevelItem(0))
    assert emitted == [["src/a.py"]]


def test_filewidget_top_level_items_are_filetreewidgetitem(
    qapp, app_context, managed_qobject
):
    """list_files erzeugt FileTreeWidgetItem-Einträge."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.list_files(["src/x.py\t5\t2"])
    item = widget.topLevelItem(0)
    assert isinstance(item, FileTreeWidgetItem)
```

**GREEN – Schritt 2:** Tests laufen lassen (sollten sofort grün sein – Charakterisierungstests).

```bash
LD_LIBRARY_PATH=/opt/data/sysroot/git-fanta/usr/lib/x86_64-linux-gnu \
  EGL_PLATFORM=surfaceless QT_QPA_PLATFORM=offscreen QT_API=pyqt6 \
  /opt/data/venvs/git-fanta/bin/python -B -m pytest \
  test/widgets_history_filelist_test.py -q
```

**Schritt 3 – Commit:**

```bash
git add test/widgets_history_filelist_test.py
git commit -m "test: characterize FileWidget commit-selection behavior"
```

---

### Task 2: RED-Test für MainView History-Files-Dock

**Ziel:** Schreibe einen Integrationstest, der belegt, dass MainView nach Auswahl eines Commits im History-Tree den zugehörigen `FileWidget`-Dock mit Dateien befüllt.

**Dateien:**
- Modify: `test/widgets_main_history_test.py`

**RED – Schritt 1: Schreibe fehlschlagenden Integrationstest**

```python
def test_history_files_dock_lists_changed_files_for_selected_commit(
    qapp, app_context, tmp_path_factory, managed_qobject, monkeypatch
):
    """Nach Commit-Auswahl im History-Tree zeigt der Files-Dock die Dateien."""
    # Temporäres Git-Repo mit zwei Commits
    import os, subprocess
    repo = tmp_path_factory.mktemp('history_files')
    subprocess.run(['git', 'init'], cwd=repo, capture_output=True, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test'], cwd=repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo, check=True)
    (repo / 'a.py').write_text('hello')
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
    subprocess.run(['git', 'commit', '-m', 'first'], cwd=repo, check=True)
    (repo / 'b.py').write_text('world')
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
    subprocess.run(['git', 'commit', '-m', 'second'], cwd=repo, check=True)

    # Model mit temporärem Repo — patche nur das git-Attribut
    from cola.models.main import MainModel
    tmp_model = MainModel(cwd=repo, mode=app_context.model.mode)
    monkeypatch.setattr(app_context.model, 'git', tmp_model.git)

    view = managed_qobject(MainView(app_context))
    view.show()
    qapp.processEvents()

    # Initialer Load abschließen
    import time
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        qapp.processEvents()
        if view.historywidget.treewidget.topLevelItemCount() >= 2:
            break

    # Commit auswählen
    tree = view.historywidget.treewidget
    first_commit = tree.topLevelItem(0)
    tree.setCurrentItem(first_commit)
    qapp.processEvents()

    # Verifiziere: Files-Dock existiert und zeigt Dateien
    assert hasattr(view, 'history_files_dock')
    filewidget = view.history_files_dock.widget()
    assert filewidget.topLevelItemCount() >= 1
    # Der erste Commit enthält a.py
    paths = [
        filewidget.topLevelItem(i).path
        for i in range(filewidget.topLevelItemCount())
    ]
    assert 'a.py' in paths


def test_history_files_dock_toggle_action_exists(
    qapp, main_context, managed_qobject
):
    """Das View-Menü enthält einen Toggle für den History-Files-Dock."""
    view = managed_qobject(MainView(main_context))
    view.show()
    # DockToggleAction im View-Menü finden
    view_menu = view.view_menu
    toggle_actions = [
        a for a in view_menu.actions()
        if 'History Files' in a.text()
    ]
    assert len(toggle_actions) >= 1
```

**Schritt 2: Verifiziere RED**

```bash
LD_LIBRARY_PATH=/opt/data/sysroot/git-fanta/usr/lib/x86_64-linux-gnu \
  EGL_PLATFORM=surfaceless QT_QPA_PLATFORM=offscreen QT_API=pyqt6 \
  /opt/data/venvs/git-fanta/bin/python -B -m pytest \
  test/widgets_main_history_test.py::test_history_files_dock_lists_changed_files_for_selected_commit \
  test/widgets_main_history_test.py::test_history_files_dock_toggle_action_exists -v
```

Erwartet: **FAIL** – `AttributeError: 'MainView' object has no attribute 'history_files_dock'`

**Schritt 3: Noch kein Commit** – Erst GREEN in Task 3.

---

### Task 3: GREEN – History-Files-Dock in MainView implementieren

**Ziel:** `FileWidget` als eigenen Dock in `MainView` einbetten, mit dem History-Tree verdrahten und im Layout platzieren.

**Dateien:**
- Modify: `cola/widgets/main.py`

**Schritt 1: Import hinzufügen**

In `cola/widgets/main.py`, ergänze den Import:

```python
from . import filelist
```

**Schritt 2: FileWidget und Dock in `__init__` erstellen**

Nach der `historydock`-Erzeugung (ca. Zeile 124, nach `self.historywidget = self.historydock.widget()`):

```python
        # "History Files" widget – lists changed files for the selected commit
        self.history_files_widget = filelist.FileWidget(
            context, self, remarks=False
        )
        self.history_files_dock = create_dock(
            'History Files',
            N_('History Files'),
            self,
            hide_title=True,
        )
        self.history_files_dock.setWidget(self.history_files_widget)
```

**Schritt 3: Signal-Verdrahtung**

Nach der Erzeugung von `history_tree` (ca. Zeile 125), das `commits_selected`-Signal des `CommitHistoryWidget` nutzen (identisch zum `GitDAG`-Muster, Zeile 2052–2055):

```python
        # Wire history selection to file list (same pattern as GitDAG)
        self.historywidget.commits_selected.connect(
            self.history_files_widget.commits_selected
        )
```

Das `CommitHistoryWidget.commits_selected`-Signal ist der dokumentierte Relay-Punkt (via `select_commits()` in Zeile 1910–1914). Direkte Verbindung mit `treewidget.commits_selected` würde zukünftige Filter-/Transform-Logik in `CommitHistoryWidget` umgehen.


**Schritt 4: Dock im Layout platzieren**

In der Dock-Anordnung (ca. Zeile 912), füge den Files-Dock hinzu – tabifiziert mit oder unter dem History-Dock:

```python
        self.addDockWidget(top, self.historydock)
        self.addDockWidget(top, self.history_files_dock)
        self.tabifyDockWidget(self.historydock, self.history_files_dock)
        self.historydock.raise_()  # History bleibt primär sichtbar
```

**Schritt 5: View-Menü-Eintrag und Dock-Shortcut**

In `build_view_menu()` (ca. Zeile 1055), den Dock der `dockwidgets`-Liste hinzufügen (Konsistenz mit allen anderen Docks):

```python
        self.history_files_dock,
```

In `setup_dockwidget_view_menu()` (ca. Zeile 1390), Shortcut-Tupel ergänzen:

```python
        self.history_files_dock,
```

Damit erhält der Dock automatisch einen Tastatur-Shortcut und ist konsistent mit dem Projekt-Muster.


**Schritt 6: State-Persistenz**

In `export_state()` (ca. Zeile 1307):

```python
        state['show_history_files'] = not self.history_files_dock.isHidden()
```

In `apply_state()` (ca. Zeile 1322), nach der History-Wiederherstellung:

```python
        show_history_files = state.get('show_history_files', True)
        if isinstance(show_history_files, bool):
            self.history_files_dock.setVisible(show_history_files)
            if show_history_files:
                self.history_files_dock.raise_()
```

Und in der Malformed-State-Validierung (ca. Zeile 1345), analog zu `show_history`:

```python
        if 'show_history_files' in state and not isinstance(
            state['show_history_files'], bool
        ):
            self.history_files_dock.show()
            self.history_files_dock.raise_()
            return False
```

**Schritt 7: Fallback bei State-Wiederherstellungsfehlern**

Im `else`-Zweig von `apply_state()` (ca. Zeile 1379–1380), den Files-Dock wie den History-Dock als Fallback sichtbar machen:

```python
        self.history_files_dock.show()
        self.history_files_dock.raise_()
```

**Schritt 8: Widget-Version erhöhen**

Da ein neuer Dock hinzugefügt wurde, muss `widget_version` von 2 auf 3 erhöht werden (ca. Zeile 80), damit alte gespeicherte Qt-Layout-States (`windowstate`) den neuen Dock korrekt initialisieren:

```python
        self.widget_version = 3
```

**Schritt 9: Aufräumen in `close()`**

In der `close()`-Methode (ca. Zeile 1030), keine zusätzliche Logik nötig – Qt kümmert sich um Dock-Cleanup via Parent-Ownership.

**Schritt 10: Verifiziere GREEN**

```bash
LD_LIBRARY_PATH=/opt/data/sysroot/git-fanta/usr/lib/x86_64-linux-gnu \
  EGL_PLATFORM=surfaceless QT_QPA_PLATFORM=offscreen QT_API=pyqt6 \
  /opt/data/venvs/git-fanta/bin/python -B -m pytest \
  test/widgets_main_history_test.py::test_history_files_dock_lists_changed_files_for_selected_commit \
  test/widgets_main_history_test.py::test_history_files_dock_toggle_action_exists -v
```

Erwartet: **PASS**

```bash
# Volle Main-History-Suite
LD_LIBRARY_PATH=/opt/data/sysroot/git-fanta/usr/lib/x86_64-linux-gnu \
  EGL_PLATFORM=surfaceless QT_QPA_PLATFORM=offscreen QT_API=pyqt6 \
  /opt/data/venvs/git-fanta/bin/python -B -m pytest \
  test/widgets_main_history_test.py test/widgets_history_filelist_test.py -p no:ruff -q
```

```bash
# PySide6-Gegenprobe
LD_LIBRARY_PATH=/opt/data/sysroot/git-fanta/usr/lib/x86_64-linux-gnu \
  EGL_PLATFORM=surfaceless QT_QPA_PLATFORM=offscreen QT_API=pyside6 \
  /opt/data/venvs/git-fanta-pyside6/bin/python -B -m pytest \
  test/widgets_main_history_test.py test/widgets_history_filelist_test.py -p no:ruff -q
```

**Schritt 11: Ruff & Diffcheck**

```bash
/opt/data/venvs/git-fanta/bin/ruff check test/widgets_main_history_test.py test/widgets_history_filelist_test.py cola/widgets/main.py
git diff --check
```

**Schritt 12 – Commit:**

```bash
git add cola/widgets/main.py test/widgets_main_history_test.py test/widgets_history_filelist_test.py
git commit -m "feat: show changed files for selected history commit"
```

---

### Task 4: Edge Cases und Regressionstests

**Ziel:** Leere Selektion, Multi-Select, Dock-Show/Hide-Persistenz und Kompatibilität mit bestehender Suite sicherstellen.

**Dateien:**
- Modify: `test/widgets_main_history_test.py`

**Schritt 1: Schreibe RED-Tests**

```python
def test_history_files_dock_clears_on_deselection(
    qapp, app_context, tmp_path_factory, managed_qobject, monkeypatch
):
    """Files-Dock leert sich, wenn History-Selektion aufgehoben wird."""
    # Setup via helper fixture (extrahiert aus Task 2, um DRY zu wahren):
    _setup_tmp_repo_with_commits(monkeypatch, app_context, tmp_path_factory)
    # dann:
    tree = view.historywidget.treewidget
    tree.setCurrentItem(tree.topLevelItem(0))
    qapp.processEvents()
    assert view.history_files_dock.widget().topLevelItemCount() > 0
    # Selektion aufheben
    tree.clearSelection()
    qapp.processEvents()
    assert view.history_files_dock.widget().topLevelItemCount() == 0


def test_show_history_files_persists_across_restart(
    qapp, app_context, managed_qobject, monkeypatch
):
    """show_history_files-State wird exportiert und wiederhergestellt."""
    view = managed_qobject(MainView(app_context))
    view.show()
    view.history_files_dock.hide()
    state = view.export_state()
    assert state.get('show_history_files') is False

    # Explizites apply_state mit gespeichertem State
    view2 = managed_qobject(MainView(app_context))
    view2.apply_state(state)
    view2.show()
    assert view2.history_files_dock.isHidden()  # bleibt hidden


def test_existing_gitdag_files_dock_unchanged(
    qapp, app_context, managed_qobject
):
    """GitDAG-FileWidget-Verhalten ist unverändert.
    
    Dieser Test gehört konzeptionell in test/widgets_dag_history_test.py,
    wird aber hier als Integrations-Gate geführt, um MainView-Änderungen
    gegen GitDAG-Regressionen abzusichern.
    """
    from cola.widgets.dag import GitDAG
    params = type('Args', (), {'ref': 'HEAD', 'count': 10, 'display_status': False})()
    dag_window = managed_qobject(GitDAG(app_context, params))
    assert dag_window.filewidget is not None
    assert dag_window.file_dock is not None
```

**Schritt 2: Verifiziere RED → GREEN**

```bash
LD_LIBRARY_PATH=/opt/data/sysroot/git-fanta/usr/lib/x86_64-linux-gnu \
  EGL_PLATFORM=surfaceless QT_QPA_PLATFORM=offscreen QT_API=pyqt6 \
  /opt/data/venvs/git-fanta/bin/python -B -m pytest \
  test/widgets_main_history_test.py -p no:ruff -q
```

**Schritt 3 – Commit:**

```bash
git add test/widgets_main_history_test.py
git commit -m "test: edge cases for history files dock"
```

---

### Task 5: Vollständige Verifikation

**Ziel:** Gesamtsuite grün, beide Bindings, Scope-Check, finaler Push.

**Schritt 1: Fokussierte Suites**

```bash
# PyQt6
LD_LIBRARY_PATH=/opt/data/sysroot/git-fanta/usr/lib/x86_64-linux-gnu \
  EGL_PLATFORM=surfaceless QT_QPA_PLATFORM=offscreen QT_API=pyqt6 \
  /opt/data/venvs/git-fanta/bin/python -B -m pytest \
  test/widgets_main_history_test.py \
  test/widgets_history_filelist_test.py \
  test/widgets_dag_history_test.py \
  -p no:ruff -q

# PySide6
LD_LIBRARY_PATH=/opt/data/sysroot/git-fanta/usr/lib/x86_64-linux-gnu \
  EGL_PLATFORM=surfaceless QT_QPA_PLATFORM=offscreen QT_API=pyside6 \
  /opt/data/venvs/git-fanta-pyside6/bin/python -B -m pytest \
  test/widgets_main_history_test.py \
  test/widgets_history_filelist_test.py \
  test/widgets_dag_history_test.py \
  -p no:ruff -q
```

**Schritt 2: Scope-Prüfung**

```bash
git diff --check
git status --short
# Sollte nur enthalten:
#  M cola/widgets/main.py
#  A test/widgets_history_filelist_test.py
#  M test/widgets_main_history_test.py
```

**Schritt 3: Ruff auf geänderte Dateien**

```bash
/opt/data/venvs/git-fanta/bin/ruff check \
  cola/widgets/main.py \
  test/widgets_main_history_test.py \
  test/widgets_history_filelist_test.py
```

**Schritt 4: mypy auf geänderte Produktionsdatei**

```bash
/opt/data/venvs/git-fanta/bin/python -m mypy --config-file pyproject.toml \
  cola/widgets/main.py
```

**Schritt 5: Push**

```bash
git push --set-upstream origin tree-ui-gemini-3-6
```

---

## Wahrscheinlich geänderte Dateien

| Datei | Änderung |
|---|---|
| `cola/widgets/main.py` | Import `filelist`, `FileWidget`-Erzeugung, Dock-Erstellung, Signal-Verdrahtung, View-Menü, State-Persistenz |
| `test/widgets_history_filelist_test.py` | **Neu:** Charakterisierungstests für `FileWidget` |
| `test/widgets_main_history_test.py` | Integrationstests: Dock-Existenz, Dateiliste nach Commit-Selektion, Toggle-Action, Deselektion, State-Persistenz, GitDAG-Unverändert |

---

## SOLID-/DRY-Leitplanken

- **SRP:** `FileWidget` bleibt zuständig für Dateiauflistung; `MainView` nur für Dock-Erzeugung und Verdrahtung.
- **OCP:** `FileWidget` wird unverändert wiederverwendet – keine Modifikation nötig.
- **DIP:** `MainView` hängt sich an das bestehende `commits_selected`-Signal – keine neuen Abhängigkeiten.
- **DRY:** Exakt dasselbe Signal-Muster wie `GitDAG` (Zeile 2055–2056) – keine Duplikation von Git-Kommando-Logik.
- **YAGNI:** Kein Diff-Inhalt, keine Datei-Vorschau, keine Kontextmenüs – nur Dateiliste. Das kommt später.

## Risiken

- **Qt-Dock-Verhalten:** `tabifyDockWidget` mit bestehenden Docks könnte Layout-Überraschungen verursachen. Lösung: separater Dock ohne Tabifizierung ist sicherer; Tabifizierung mit `historydock` als Fallback.
- **Git-Prozesse im Test:** E2E-Tests mit temporären Repos können langsam sein. Lösung: Timeout-Grenzen wie in bestehenden Main-History-Tests.
- **State-Migration:** Alte States ohne `show_history_files` müssen den Dock standardmäßig sichtbar machen. Im Plan: Default-Show, nur explizit `False` versteckt.

---

## Reviewer-Hinweise

1. **Spec-Compliance-Review:** Prüft, ob das Feature genau die Dateiauflistung (nicht Diff) liefert, ob der Dock korrekt tabifiziert/platziert ist, und ob die UX GitKraken/SourceTree entspricht (Dateinamen, +/- Spalten).
2. **Code-Quality-Review:** Prüft Wiederverwendung von `FileWidget`, Signal-Verdrahtung analog zu `GitDAG`, State-Persistenz, Testabdeckung (leer, deselektiert, Multi-Select, Persistenz).
