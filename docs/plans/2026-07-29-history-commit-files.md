# Commit-Dateiliste im History-Dock – Implementierungsplan

> **Für Hermes:** Verwende den `plan`-Skill und führe die Tasks mit TDD + unabhängigem Doppel-Review pro Task aus.

**Ziel:** Ein Datei-Panel, das pro ausgewähltem Commit im History-Dock des Hauptfensters die geänderten Dateien auflistet – inspiriert von GitKraken/SourceTree, ohne Diff-Inhalt (nur Dateinamen, +/- Statistik).

**Architektur:** Wiederverwendung des existierenden `filelist.FileWidget`, das bereits `commits_selected`-Signale verarbeitet und `git show --numstat`/`git diff` ausführt. Das Widget wird als eigener Dock („History-Dateien") in `MainView` eingebettet und über das `commits_selected`-Signal des `CommitHistoryWidget`-TreeWidgets angesteuert – exakt dasselbe Muster, das `GitDAG` bereits nutzt.

**Tech Stack:** Python 3, PyQt6/PySide6 (via qtpy), Git Cola/Fanta-eigene Widgets (`filelist.FileWidget`, `CommitHistoryWidget`, `qtutils.create_dock`).

---
> **Review-Status:** Critical Plan Review (fünfte Iteration) abgeschlossen. 1 MAJOR + 2 MINOR + 7 NOTE behoben.
>
> **Iteration 4 → 5 (diese Iteration) — neu gefundene Issues (Sub-Agent):**
> - **MAJOR:** `apply_state` finale Return-Expression integriert `show_history_files_visibility_ok` nicht. Asymmetrisch zu `show_history` (das `visibility_ok` in den Return aufnimmt). Schritt 6a ergänzt.
> - **MINOR-1:** Bestehender Test `test_real_legacy_v2_state_preserves_existing_docks_and_reveals_history` manuall `tabifyDockWidget(historydock, commitdock)` — kollidiert mit Plan-Topologie (historydock bereits tabifiziert mit history_files_dock). Three-way-Tab-Gruppe entsteht. Test passt noch, aber Topologie divergiert. Schritt 4 dokumentiert.
> - **MINOR-2:** monkeypatch-Ordering fragil — monkeypatch MUSS vor `MainView(main_context)` erfolgen weil `self.git = context.git` zur Bauzeit kopiert wird. Kommentar in Task 2 + Helper ergänzt.
> - **NOTEs (alle bestätigt):** widget_version beide Stellen korrekt adressiert; v3-Blob Zwei-Phasen-WF korrekt; create_dock-Pattern korrekt; PySide6/PyQt6 kompatibel via qtpy; closeEvent cleanup via Qt-Parent-Ownership OK; managed_qobject-Fixture OK; qtutils.hide_dock nicht nötig für history_files_dock (Default-Visible).
>
> **Iteration 3 → 4 (diese Iteration) — neu gefundene Issues (Hauptsession + Sub-Agent):**
> - **BLOCKER-1:** `widget_version`-Bump 2→3 bricht AUCH `test/widgets_main_history_test.py:295` (`assert window.widget_version == 2`) — Plan adressierte nur `widgets_dag_history_test.py:1906`, nicht die zweite Stelle. **Schritt 7b muss BEIDE Test-Dateien listen.**
> - **BLOCKER-2:** Helper `_setup_tmp_repo_with_commits` Race Condition: Polling ohne `qapp.processEvents()` lässt `CommitHistoryWidget` Background-Thread nie liefern → `topLevelItemCount()` bleibt 0 → Tests scheitern nach 10s-Timeout. **qapp-Parameter ZURÜCK + `qapp.processEvents()` + `QtTest.QTest.qWait(10)` im Loop.**
> - **MAJOR-1:** Task 4 Tests `test_existing_gitdag_files_dock_unchanged` und `test_show_history_files_persists_across_restart` nutzen `app_context` statt `main_context` → `Interaction.log`-Side-Effects.
> - **MAJOR-2:** `LEGACY_MAINVIEW_V3_WINDOWSTATE` ist Hühnerei-Problem — kann erst NACH main.py-Bump exportiert werden. **In zwei Phasen splitten:** (Phase A) Code + widget_version-Bumps, (Phase B) v3-Blob-Export + neuer Test.
> - **MAJOR-3:** Selber Plan sagt "qapp entfernen" UND "qapp nötig" — Widerspruch. NOTE zurückgenommen.
> - **MAJOR-4:** Idiom-Inkonsistenz: Tests nutzen `hide()`, Produktion nutzt `setVisible(False)`. Vereinheitlichen.
> - **MINOR-1:** `'History Files' in a.text()` Mnemonik-Robustheit — `&History Files` würde brechen.
> - **MINOR-2:** `'a.py' in paths` nicht robust gegen zusammengesetzte Pfade.
> - **MINOR-3:** Geänderte-Dateien-Tabelle unvollständig.
> - **Produktentscheidung:** `show_history_files` Mirror-Ansatz gewählt — non-bool → `return False` (analog `show_history`).
> - **NOTE-1:** Synchrones `git.show()` in FileWidget kann GUI blockieren.
> - **NOTE-2:** SetVisible(True) nach Restore ohne initial-history-loaded → Dock sichtbar aber leer.
> - **NOTE-3:** Hide/Show während ReaderThread läuft — undefiniertes Verhalten.
>
> **Iteration 2 → 3 (zuvor behoben):**
> - widget_version=3 Bump + Test-Update für widgets_dag_history_test.py (jetzt erweitert um widgets_main_history_test.py)
> - Schritt 4 Snippet vollständig (addDockWidget + tabifyDockWidget Sequenz)
> - malformed-state `return False` entfernt
> - Schritt 5a createPopupMenu-Redundanz dokumentiert
> - Ctrl+Y Mnemonik-Theater entfernt
> - Geänderte-Dateien-Tabelle um widgets_dag_history_test.py erweitert
>
> **Iteration 1 → 2 (zuvor behoben):**
> - Shortcut Ctrl+F → Ctrl+Y
> - Schritt 5 Codemix aufgeteilt
> - Test-Body main_context-Konsistenz
> - widget_version-Kommentar "added or removed"
> - Task 4 als "Akzeptanztests" deklariert
> - Signal-Routing-Test-Kommentar

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
    qapp, main_context, tmp_path_factory, managed_qobject, monkeypatch
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

    # MainModel mit temporärem Repo erzeugen und git-Attribute überschreiben.
    # MainModel.__init__(context, cwd=None) — cwd setzt das Arbeitsverzeichnis.
    # WICHTIG: monkeypatch MUSS vor `MainView(main_context)` erfolgen, weil
    # `MainView.__init__` in `self.git = context.git` (Zeile 72) die Referenz
    # zur Bauzeit kopiert. Nachträgliches Patchen hat keine Wirkung.
    from cola.models.main import MainModel
    from unittest.mock import Mock
    tmp_model = MainModel(main_context, cwd=str(repo))
    monkeypatch.setattr(main_context, 'git', tmp_model.git)
    monkeypatch.setattr(main_context.model, 'git', tmp_model.git)

    view = managed_qobject(MainView(main_context))  # main_context (nicht app_context) für Konsistenz mit Fixtures
    view.show()
    qapp.processEvents()

    # Initialer Load abschließen
    import time
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        qapp.processEvents()
        if view.historywidget.treewidget.topLevelItemCount() >= 2:
            break

    # Commit auswählen — via CommitHistoryWidget.commits_selected (Relay-Pfad),
    # nicht direkt via treewidget.commits_selected, um den dokumentierten
    # Routing-Pfad analog zu GitDAG._history_selection_changed zu verifizieren.
    tree = view.historywidget.treewidget
    first_commit = tree.topLevelItem(0)
    # setCurrentItem triggert CommitTreeWidget.commits_selected → CommitHistoryWidget.select_commits
    # → CommitHistoryWidget.commits_selected.emit → history_files_widget.commits_selected
    tree.setCurrentItem(first_commit)
    qapp.processEvents()

    # Verifiziere: Files-Dock existiert und zeigt Dateien
    assert hasattr(view, 'history_files_dock')
    filewidget = view.history_files_dock.widget()
    assert filewidget.topLevelItemCount() >= 1
    # Der erste Commit enthält a.py (endswith für Pfad-Robustheit)
    paths = [
        filewidget.topLevelItem(i).path
        for i in range(filewidget.topLevelItemCount())
    ]
    assert any(p.endswith('a.py') for p in paths)


def test_history_files_dock_toggle_action_exists(
    qapp, main_context, managed_qobject
):
    """Das View-Menü enthält einen Toggle für den History-Files-Dock."""
    view = managed_qobject(MainView(main_context))
    view.show()
    # DockToggleAction im View-Menü finden (Mnemonik-tolerant: &History Files)
    view_menu = view.view_menu
    toggle_actions = [
        a for a in view_menu.actions()
        if 'History Files' in a.text().replace('&', '')
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

> **Qt-Kontrakt:** `tabifyDockWidget(a, b)` erfordert, dass BEIDE Docks bereits via `addDockWidget` zum selben Dock-Area hinzugefügt wurden. Die `tabifyDockWidget`-Aufrufe müssen also NACH den `addDockWidget`-Aufrufen für die jeweiligen Docks erfolgen, nicht zwischendrin.

> **Test-Topologie-Hinweis (Sub-Agent Finding):** Der bestehende Test `test_real_legacy_v2_state_preserves_existing_docks_and_reveals_history` in `test/widgets_main_history_test.py:282` macht manuelles `window.tabifyDockWidget(window.historydock, window.commitdock)`. Nach dem Plan ist `historydock` bereits mit `history_files_dock` tabifiziert — der Test überschreibt das mit `commitdock` (Three-way-Tab-Gruppe). Test passt weiterhin (assertion ist auf `historydock` Active, nicht auf Tab-Partner), aber die Topologie divergiert von Production. Akzeptabel für Phase A; Cleanup in Phase B oder separatem Follow-up.

In der Dock-Anordnung (exakt nach `self.addDockWidget(top, self.historydock)` in Zeile 912, **vor** `self.addDockWidget(top, self.commitdock)` in Zeile 913), den Files-Dock einfügen und tabifizieren. **Exakter Block** (kein `...`):

```python
        self.addDockWidget(top, self.historydock)
        self.addDockWidget(top, self.history_files_dock)              # ← NEU: dock zuerst hinzufügen
        self.tabifyDockWidget(self.historydock, self.history_files_dock)  # ← NEU: dann tabifizieren
        self.historydock.raise_()  # History bleibt primär sichtbar
        self.addDockWidget(top, self.commitdock)
```

**Begründung Reihenfolge:**
1. `addDockWidget(top, self.history_files_dock)` — Dock muss zum Qt-Layout gehören, bevor `tabifyDockWidget` ihn referenzieren kann.
2. `tabifyDockWidget(self.historydock, self.history_files_dock)` — macht beide Docks zu Tab-Partnern im selben Bereich.
3. `self.historydock.raise_()` — sorgt dafür, dass beim Start der History-Tree sichtbar ist (nicht der Files-Dock).
4. Erst danach `addDockWidget(top, self.commitdock)` — Reihenfolge wie im Original (Commit-Dock bleibt eigener Tab).

**Schritt 5: View-Menü-Eintrag und Dock-Shortcut**

> **Hinweis:** `Ctrl+F` kollidiert mit `SEARCH` (`cola/hotkeys.py:76`). Verifikation per `grep "Ctrl.*Key_[A-Z]" cola/hotkeys.py` ergab freie Buchstaben (keine vorhandene Ctrl+<Buchstabe>-Bindung): N, O, V, X, Y. Gewählt: **`Ctrl+Y`** — ausschließlich nach Verfügbarkeit (Y ist der letzte freie Buchstabe, alle anderen haben etablierte Bindungen). Eine mnemonische Verbindung Y↔Files wird NICHT beansprucht.

**5a) View-Menü-Eintrag (`build_view_menu`, ca. Zeile 1068):**

Den Dock **nur als Dock-Objekt** in die `dockwidgets`-Liste einfügen — KEIN Tupel! Die Liste enthält reine `QDockWidget`-Objekte; das anschließende `toggleViewAction()`-Loop würde bei einem Tupel mit `AttributeError` fehlschlagen.

> **Hinweis zur Redundanz:** `createPopupMenu()` (Zeile 1053) auto-entdeckt bereits alle registrierten `QDockWidget`s und fügt ihre `toggleViewAction()`-Einträge dem Menü hinzu. Die explizite `dockwidgets`-Liste ist also strenggenommen redundant. Sie wird hier trotzdem erweitert, weil das Projekt-Muster genau so aussieht (alle bestehenden Docks sind dort explizit gelistet) — Konsistenz statt Minimalismus. Die `if toggleview not in menu.actions():`-Guard verhindert Duplikate.

```python
        dockwidgets = [
            self.logdock,
            self.historydock,
            self.commitdock,
            self.statusdock,
            self.diffdock,
            self.actionsdock,
            self.bookmarksdock,
            self.recentdock,
            self.branchdock,
            self.submodulesdock,
            self.history_files_dock,  # ← neue Zeile (Dock-Objekt, kein Tupel)
        ]
```

**5b) Shortcut (`setup_dockwidget_view_menu`, ca. Zeile 1390):**

Das `(shortcut, dockwidget)`-Tupel an die `dockwidgets`-Tupel-Liste anhängen:

```python
        dockwidgets = (
            (optkey + '+0', self.logdock),
            (optkey + '+9', self.historydock),
            (optkey + '+1', self.commitdock),
            (optkey + '+2', self.statusdock),
            (optkey + '+3', self.diffdock),
            (optkey + '+4', self.actionsdock),
            (optkey + '+5', self.bookmarksdock),
            (optkey + '+6', self.recentdock),
            (optkey + '+7', self.branchdock),
            (optkey + '+8', self.submodulesdock),
            (optkey + '+Y', self.history_files_dock),  # ← neue Zeile (Shortcut-Tupel)
        )
```

Damit erhält der Dock automatisch einen Tastatur-Shortcut (`Shift+Ctrl+Y` zum Toggle, `Ctrl+Y` zum Fokus) und ist konsistent mit dem Projekt-Muster.


**Schritt 6: State-Persistenz (MIRROR-Ansatz)**

> **Designentscheidung (Mirror):** `show_history_files` spiegelt die existierende `show_history`-Semantik **exakt**. Das umfasst auch das strikte `return False` bei Non-Bool-Werten (siehe `test_non_bool_history_visibility_is_rejected_before_state_changes` in `test/widgets_main_history_test.py:1074-1086`, der genau dieses Verhalten für `show_history=0` verifiziert). Konsistenz schlägt Toleranz — ein neuer Dock-Flag mit weniger restriktiver Semantik wäre eine subtile Inkonsistenz.

In `export_state()` (ca. Zeile 1307):

```python
        state['show_history_files'] = not self.history_files_dock.isHidden()
```

In `apply_state()` (ca. Zeile 1346, **analog zur `show_history`-Validierungsstelle**):

```python
        if 'show_history_files' in state and not isinstance(
            state['show_history_files'], bool
        ):
            # Non-Bool → State ist korrupt → vollständiger Abbruch
            # (analog show_history Zeile 1347-1349, siehe test/widgets_main_history_test.py:1074)
            self.history_files_dock.show()  # Fallback wie show_history
            self.history_files_dock.raise_()
            return False
        # Mirror-Pattern aus show_history Zeile 1374-1378:
        show_history_files = state.get('show_history_files', True)
        show_history_files_visibility_ok = isinstance(show_history_files, bool)
        if show_history_files_visibility_ok:
            self.history_files_dock.setVisible(show_history_files)
            if show_history_files:
                self.history_files_dock.raise_()
        else:
            self.history_files_dock.show()
            self.history_files_dock.raise_()
```

**Schritt 6a — Finale Return-Expression ergänzen (Sub-Agent Finding):**

> **KRITISCH:** Der finale `return` von `apply_state` (Zeile 1382) lautet:
> ```python
> return base_ok and diff_ok and commitmsg_ok and history_ok and visibility_ok
> ```
> `visibility_ok` ist die Variable für `show_history`. Für echte Mirror-Symmetrie muss `show_history_files_visibility_ok` ebenfalls in diese Expression aufgenommen werden. Ohne diese Integration wäre die Spiegelung nur "optisch" (gleiche Variablen-Namen) aber nicht "semantisch" (gleiche Return-Expression). Tests, die `apply_state(state) is True/False` assertieren, würden sonst nicht zwischen "show_history OK" und "show_history_files OK" unterscheiden können.

In der finalen `return`-Zeile (ca. Zeile 1382) `show_history_files_visibility_ok` ergänzen:

```python
        return (base_ok and diff_ok and commitmsg_ok and history_ok
                and visibility_ok and show_history_files_visibility_ok)
```

**Wichtig — Asymmetrie zur vorherigen Iteration:** Diese Iteration 4 hat die ursprünglich geplante "non-bool → default-true"-Liberal-Variante EXPLIZIT verworfen zugunsten der strikten Mirror-Variante. Die Begründung:
- Konsistenz mit `show_history` (etabliertes Pattern im Projekt seit Jahren)
- Korrupte Config → sichtbarer Fehler (`apply_state returns False`) statt verstecktes Default-Verhalten
- Test-Pattern existiert bereits (`show_history=0` Test) — kann 1:1 für `show_history_files=0` kopiert werden (siehe Schritt 6b)

**Schritt 6b: Test für non-bool `show_history_files` (Mirror-Pattern)**

> **Ergänzung zu Task 2/4 RED-Slice:** Ein zusätzlicher Akzeptanztest, der die non-bool-Reject-Semantik verifiziert (analog `test_non_bool_history_visibility_is_rejected_before_state_changes`):

```python
def test_non_bool_history_files_visibility_is_rejected(
    qapp, main_context, managed_qobject
):
    """Mirror-Pattern: non-bool show_history_files triggert apply_state is False."""
    view = managed_qobject(MainView(main_context))
    view.show()
    state = view.export_state()
    state['show_history_files'] = 0  # non-bool, wie show_history=0
    view.history_files_dock.setVisible(True)  # Pre-State

    assert view.apply_state(state) is False

    # Dock bleibt im Pre-State (kein partial apply)
    assert view.history_files_dock.isVisible()
```

**Schritt 7: Widget-Version erhöhen UND bestehende Tests anpassen**

> **BLOCKER-relevant:** Der Bump von `widget_version` 2 → 3 bricht den bestehenden Test in `test/widgets_dag_history_test.py:1906`, der hart `assert widget.widget_version == 2` codiert. Dieser Test muss ZWINGEND im selben Commit angepasst werden, sonst ist die Suite sofort rot.

**7a) `cola/widgets/main.py` — Version-Bump + Kommentar-Update (ca. Zeile 79-81):**

```python
        # The widget version is used by import/export_state().
        # Change this whenever dockwidgets are added or removed.
        self.widget_version = 3
```

**7b) Tests mit `widget_version == 2` Assertion anpassen — BEIDE Dateien:**

> **BLOCKER-relevant:** Es gibt **zwei** Test-Dateien mit hart codierter `widget_version == 2` Assertion. Beide müssen im SELBEN Commit aktualisiert werden:

**7b-i) `test/widgets_dag_history_test.py:1906`** — Suche `assert widget.widget_version == 2` und ersetze durch:

```python
        assert widget.widget_version == 3
```

**7b-ii) `test/widgets_main_history_test.py:295`** — Im Test `test_real_legacy_v2_state_preserves_existing_docks_and_reveals_history`, gleiche Ersetzung:

```python
        assert window.widget_version == 3
```

**Verifikation der Vollständigkeit** (vor Commit ausführen):

```bash
grep -rn 'widget_version == 2' test/
# Erwartete Ausgabe: LEER (keine Treffer mehr)
```

Falls die Suche weitere Treffer zeigt, MÜSSEN diese ebenfalls angepasst werden. Hinweis: `cola/widgets/dag.py:2023` (`self.widget_version = 2` in `GitDAG`) bleibt UNVERÄNDERT — GitDAG hat eigene Docks und braucht keinen v3-Bump.

**7c) Zwei-Phasen-WF für v3-Windowstate-Test (Hühnerei-Problem gelöst):**

> **Hintergrund:** `LEGACY_MAINVIEW_V3_WINDOWSTATE` kann erst NACH dem main.py-Bump existieren (Blob wird aus v3-MainView exportiert). TDD verlangt aber Tests vor Code. Lösung: Test wird im **zweiten Commit** nachgereicht.

**Phase A — ERSTER COMMIT (zusammen mit 7a + 7b):**

Nur Code-Änderung + `widget_version`-Test-Updates. **Kein** v3-Test in diesem Commit. Suite ist grün weil:
- v2-Tests funktionieren nicht mehr (Assertions upgedated)
- v3-Test fehlt → Coverage-Lücke, akzeptabel für Phase A

```bash
git add cola/widgets/main.py test/widgets_dag_history_test.py test/widgets_main_history_test.py
git commit -m "feat: add History Files dock to MainView (widget_version=3)

Wires FileWidget to CommitHistoryWidget.commits_selected. v3-windowstate
migration tests deferred to follow-up commit."
```

**Phase B — ZWEITER COMMIT (nach erfolgreicher Phase-A-Merge):**

7c-i) **v3-Blob exportieren** — One-Shot-Script ausführen, Base64-String kopieren:

```python
# In test/_export_v3_blob.py (one-shot, nicht committed):
import sys
sys.path.insert(0, '.')
from unittest.mock import Mock
from qtpy import QtGui, QtWidgets
from cola.interaction import Interaction
from cola.widgets.main import MainView
from test.helper import app_context

# main_context manuell aufsetzen (Mock-Fixture, kein pytest)
# ... siehe widgets_dag_history_test.py für genaues Setup ...

widget = MainView(ctx)
widget.show()
QtWidgets.QApplication.processEvents()
v3_blob = widget.saveState(3).toBase64().data().decode('ascii')
print(v3_blob)
```

7c-ii) **Base64-String in BEIDE Test-Dateien als Modul-Konstante ablegen:**

```python
# In test/widgets_dag_history_test.py (nach der v2-Konstante):
LEGACY_MAINVIEW_V3_WINDOWSTATE = '<base64-string-hier-einfügen>'

# In test/widgets_main_history_test.py (nach der v2-Konstante):
LEGACY_MAINVIEW_V3_WINDOWSTATE = '<base64-string-hier-einfügen>'
```

> **Synchronisations-Pflicht:** Beide Dateien haben historisch bedingt je eine lokale `LEGACY_MAINVIEW_V2_WINDOWSTATE`-Kopie (siehe `widgets_dag_history_test.py:46` UND `widgets_main_history_test.py:74`). Der v3-Blob MUSS in BEIDE Dateien kopiert werden, sonst divergieren die Tests.

7c-iii) **Neuen v3-Test hinzufügen** in `test/widgets_dag_history_test.py`:

```python
def test_mainview_legacy_v3_windowstate_restores_docks(
    qapp, main_context, managed_qobject, monkeypatch
):
    """Legacy v3 windowstate (with History Files dock) restores correctly."""
    monkeypatch.setattr(Interaction, 'log_status', Mock())
    monkeypatch.setattr(Interaction, 'log', Mock())
    main_context.settings.get_gui_state.return_value = {}
    main_context.browser_windows = []
    main_context.settings.bookmarks = []
    main_context.settings.recent = []
    main_context.app.theme.background_color_rgb.return_value = '#ffffff'
    main_context.app.theme.selection_color.return_value = QtGui.QColor('#4488cc')

    widget = managed_qobject(MainView(main_context))
    legacy_state = widget.export_state()
    legacy_state['windowstate'] = LEGACY_MAINVIEW_V3_WINDOWSTATE
    legacy_state.pop('history', None)
    legacy_state.pop('show_history', None)

    assert widget.widget_version == 3
    assert widget.apply_state(legacy_state)
    widget.show()
    qapp.processEvents()

    # History Files dock muss im Top-Bereich sein
    assert widget.dockWidgetArea(widget.history_files_dock) == QtCore.Qt.TopDockWidgetArea
    assert widget.history_files_dock in widget.tabifiedDockWidgets(widget.historydock)
```

7c-iv) **Phase-B-Commit:**

```bash
git add test/widgets_dag_history_test.py test/widgets_main_history_test.py
git commit -m "test: add v3-windowstate migration test for MainView"
```

**Schritt 8: Aufräumen in `close()`**

In der `close()`-Methode (ca. Zeile 1030), keine zusätzliche Logik nötig – Qt kümmert sich um Dock-Cleanup via Parent-Ownership.

**Schritt 9: Phase-A-Commit (siehe Schritt 7c-i)**

Der erste Commit enthält:
- Code-Änderungen aus Schritt 1-6 (ohne v3-Test)
- `widget_version = 3` + Kommentar (Schritt 7a)
- Test-Assertion-Updates in BEIDEN Test-Dateien (Schritt 7b-i + 7b-ii)

```bash
git add \
  cola/widgets/main.py \
  test/widgets_dag_history_test.py \
  test/widgets_main_history_test.py
git commit -m "feat: add History Files dock to MainView (widget_version=3)

Wires FileWidget to CommitHistoryWidget.commits_selected. Bumps
widget_version to 3 to include the new dock in Qt layout state.

v3-windowstate migration test deferred to follow-up commit."
```

**Schritt 10: Verifiziere GREEN (Phase A)**

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

**Schritt 12 – Commit (Phase A abgeschlossen, Phase B dokumentiert):**

> **Phase A wurde bereits in Schritt 9 committed.** Hier ist nur eine **Verifikation**, dass alle Phase-A-Dateien committed sind, plus ein Hinweis auf Phase B:

```bash
git log --oneline -1
# Erwartet: feat: add History Files dock to MainView (widget_version=3)

git status
# Erwartet: working tree clean (oder nur untracked .hermes/, .bak-Dateien)
```

> **Phase B (v3-windowstate-Test)** wird in einem separaten, späteren Commit nachgereicht — siehe Schritt 7c-iv. Reihenfolge:
>
> 1. Code-Merge von Phase A in main
> 2. Phase B ausführen (v3-Blob exportieren, Konstante in beide Test-Dateien, neuer Test)
> 3. Phase-B-Commit: `test: add v3-windowstate migration test for MainView`

---

### Task 4: Edge Cases und Regressionstests (Akzeptanztests)

> **Hinweis:** Diese Tests sind **Akzeptanztests / zusätzliche Charakterisierung**, kein eigenständiger RED→GREEN-Zyklus, da die zugrunde liegende Implementierung bereits in Task 3 erfolgt. Sie werden unmittelbar nach Task 3 grün sein. Ihr Zweck ist **Regressionsabsicherung** für Deselection, Persistenz, Hide/Show-Zyklus und GitDAG-Kompatibilität.

**Ziel:** Leere Selektion, Multi-Select, Dock-Show/Hide-Persistenz und Kompatibilität mit bestehender Suite sicherstellen.

**Dateien:**
- Modify: `test/widgets_main_history_test.py`

**Schritt 1: Schreibe Tests**

```python
def _setup_tmp_repo_with_commits(qapp, ctx, tmp_path_factory, managed_qobject, monkeypatch):
    """Erzeugt temporäres Git-Repo mit 2 Commits und einen MainView.

    Wichtig: CommitHistoryWidget liest `self.model.git` für Repo-Operationen,
    FileWidget liest `self.context.git`. Beide müssen auf das tmp_model.git
    zeigen, sonst lädt der History-Tree keine Commits aus dem Temp-Repo.

    KRITISCH: `qapp` ist erforderlich, weil `CommitHistoryWidget` in einem
    Background-Thread läuft (siehe `cola/widgets/dag.py:ReaderThread`).
    Ohne `qapp.processEvents()` im Polling-Loop bleibt die Event-Loop blockiert
    und der Worker kann seine Ergebnisse nicht liefern → `topLevelItemCount()`
    bleibt 0 → 10s-Timeout. Pattern analog `_wait_for_history()` in
    `test/widgets_main_history_test.py:140`.
    """
    import os, subprocess, time
    from unittest.mock import Mock
    from cola.models.main import MainModel
    from qtpy import QtTest
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
    tmp_model = MainModel(ctx, cwd=str(repo))
    # Beide Git-Referenzen müssen auf das tmp_model zeigen:
    # (MainModel.git ist reguläres Attribut, kein Property — verifiziert)
    # WICHTIG: monkeypatch MUSS vor `MainView(ctx)` erfolgen — `MainView.__init__`
    # kopiert `self.git = context.git` (Zeile 72) zur Bauzeit.
    monkeypatch.setattr(ctx, 'git', tmp_model.git)              # für FileWidget.context.git
    monkeypatch.setattr(ctx.model, 'git', tmp_model.git)         # MainModel.git (CommitHistoryWidget indirekt)
    view = managed_qobject(MainView(ctx))
    view.show()
    # Polling mit Event-Pump, sonst blockiert ReaderThread
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        qapp.processEvents()
        QtTest.QTest.qWait(10)
        if view.historywidget.treewidget.topLevelItemCount() >= 2:
            break
    return view


def test_history_files_dock_clears_on_deselection(
    qapp, main_context, tmp_path_factory, managed_qobject, monkeypatch
):
    """Files-Dock leert sich, wenn History-Selektion aufgehoben wird."""
    # Setup via helper fixture (extrahiert aus Task 2, um DRY zu wahren):
    view = _setup_tmp_repo_with_commits(
        qapp, main_context, tmp_path_factory, managed_qobject, monkeypatch
    )
    tree = view.historywidget.treewidget
    tree.setCurrentItem(tree.topLevelItem(0))
    qapp.processEvents()
    assert view.history_files_dock.widget().topLevelItemCount() > 0
    # Selektion aufheben
    tree.clearSelection()
    qapp.processEvents()
    assert view.history_files_dock.widget().topLevelItemCount() == 0


def test_show_history_files_persists_across_restart(
    qapp, main_context, managed_qobject, monkeypatch
):
    """show_history_files-State wird exportiert und wiederhergestellt."""
    # main_context (nicht app_context) weil MainView Interaction.log aufruft
    view = managed_qobject(MainView(main_context))
    view.show()
    view.history_files_dock.setVisible(False)
    state = view.export_state()
    assert state.get('show_history_files') is False

    # Explizites apply_state mit gespeichertem State
    view2 = managed_qobject(MainView(main_context))
    view2.apply_state(state)
    view2.show()
    assert not view2.history_files_dock.isVisible()  # bleibt hidden
def test_history_files_dock_shows_correct_files_after_hide_show_cycle(
    qapp, main_context, tmp_path_factory, managed_qobject, monkeypatch
):
    """Files-Dock zeigt aktuelle Dateien nach Hide/Show-Zyklus."""
    view = _setup_tmp_repo_with_commits(
        qapp, main_context, tmp_path_factory, managed_qobject, monkeypatch
    )
    tree = view.historywidget.treewidget

    # Erstes Commit selektieren
    tree.setCurrentItem(tree.topLevelItem(0))
    qapp.processEvents()
    first_files = [
        view.history_files_dock.widget().topLevelItem(i).path
        for i in range(view.history_files_dock.widget().topLevelItemCount())
    ]

    # Dock verstecken (Idiom-Konsistenz mit apply_state)
    view.history_files_dock.setVisible(False)

    # Zweites Commit selektieren (während Dock versteckt)
    tree.setCurrentItem(tree.topLevelItem(1))
    qapp.processEvents()

    # Dock wieder zeigen — muss Dateien des zweiten Commits zeigen
    view.history_files_dock.setVisible(True)
    qapp.processEvents()
    second_files = [
        view.history_files_dock.widget().topLevelItem(i).path
        for i in range(view.history_files_dock.widget().topLevelItemCount())
    ]

    # commit 0: a.py, commit 1: a.py (modified) + b.py (new)
    assert any(p.endswith('a.py') for p in first_files)
    assert any(p.endswith('b.py') for p in second_files)
    # Die Dateilisten müssen sich unterscheiden (verschiedene Commits)
    assert first_files != second_files



def test_existing_gitdag_files_dock_unchanged(
    qapp, main_context, managed_qobject
):
    """GitDAG-FileWidget-Verhalten ist unverändert.

    Dieser Test gehört konzeptionell in test/widgets_dag_history_test.py,
    wird aber hier als Integrations-Gate geführt, um MainView-Änderungen
    gegen GitDAG-Regressionen abzusichern.

    main_context (nicht app_context) weil GitDAG ebenfalls Interaction.log aufruft.
    """
    from cola.widgets.dag import GitDAG
    params = type('Args', (), {'ref': 'HEAD', 'count': 10, 'display_status': False})()
    dag_window = managed_qobject(GitDAG(main_context, params))
    assert dag_window.filewidget is not None
    assert dag_window.file_dock is not None
```

**Schritt 2: Verifiziere GREEN (Akzeptanztests)**

```bash
LD_LIBRARY_PATH=/opt/data/sysroot/git-fanta/usr/lib/x86_64-linux-gnu \
  EGL_PLATFORM=surfaceless QT_QPA_PLATFORM=offscreen QT_API=pyqt6 \
  /opt/data/venvs/git-fanta/bin/python -B -m pytest \
  test/widgets_main_history_test.py -p no:ruff -q
```

Erwartet: **PASS** (Implementierung existiert bereits aus Task 3).

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

| Datei | Änderung | Grund |
|---|---|---|
| `cola/widgets/main.py` | Import `filelist`, `FileWidget`-Erzeugung, Dock-Erstellung (`create_dock('History Files', ...)`), Signal-Verdrahtung (`historywidget.commits_selected → history_files_widget.commits_selected`), Layout (`addDockWidget` + `tabifyDockWidget` mit `historydock`), View-Menü-Eintrag (Dock-Objekt in `build_view_menu`), Shortcut-Tupel (`optkey+'+Y'`) in `setup_dockwidget_view_menu`, **State-Persistenz** (`export_state` schreibt `show_history_files`, `apply_state` liest `show_history_files` mit **Mirror-Semantik** analog `show_history`), **`widget_version = 3`** + Kommentar-Update (`added or removed`) | Feature-Implementierung |
| `test/widgets_history_filelist_test.py` | **Neu:** Charakterisierungstests für `FileWidget` | TDD Foundation |
| `test/widgets_main_history_test.py` | Integrationstests: Dock-Existenz, Dateiliste nach Commit-Selektion via Relay-Pfad, Toggle-Action, Deselektion, State-Persistenz, GitDAG-Unverändert, Hide/Show-Zyklus. Verwendet konsistent `main_context`-Fixture. **Helper `_setup_tmp_repo_with_commits` mit `qapp`-Parameter und `processEvents()`-Loop.** Außerdem: Assertion `assert window.widget_version == 2` (Zeile 295) → `== 3` wegen widget_version-Bump. | TDD-RED + Cross-File-Anpassung |
| `test/widgets_dag_history_test.py` | Assertion `assert widget.widget_version == 2` (Zeile 1906) → `== 3`. **Phase B:** Neuer v3-windowstate-Test mit `LEGACY_MAINVIEW_V3_WINDOWSTATE`. | Cross-File-Anpassung + Migration-Test |

---

## SOLID-/DRY-Leitplanken

- **SRP:** `FileWidget` bleibt zuständig für Dateiauflistung; `MainView` nur für Dock-Erzeugung und Verdrahtung.
- **OCP:** `FileWidget` wird unverändert wiederverwendet – keine Modifikation nötig.
- **DIP:** `MainView` hängt sich an das bestehende `commits_selected`-Signal – keine neuen Abhängigkeiten.
- **DRY:** Exakt dasselbe Signal-Muster wie `GitDAG` (Zeile 2055–2056) – keine Duplikation von Git-Kommando-Logik.
- **YAGNI:** Kein Diff-Inhalt, keine Datei-Vorschau, keine Kontextmenüs – nur Dateiliste. Das kommt später.

## Nicht verdrahtete Kontextmenü-Aktionen (YAGNI für v1)

`FileWidget` bringt per Rechtsklick Aktionen mit („Show History", „Launch Diff Tool", „Launch Editor", „Grab File"). Diese sind im History-Files-Dock verfügbar, aber bewusst NICHT mit MainViews Diff-Viewer verdrahtet. Nur `files_selected`-Signal wird vom FileWidget emittiert. Die Verknüpfung mit dem Diff-Viewer kommt in einem späteren Feature („Diff-Inhalt anzeigen").

## Risiken

- **Qt-Dock-Verhalten:** `tabifyDockWidget` mit bestehenden Docks könnte Layout-Überraschungen verursachen. Lösung: separater Dock ohne Tabifizierung ist sicherer; Tabifizierung mit `historydock` als Fallback.
- **Git-Prozesse im Test:** E2E-Tests mit temporären Repos können langsam sein. Lösung: Timeout-Grenzen wie in bestehenden Main-History-Tests.
- **State-Migration:** Alte States ohne `show_history_files` müssen den Dock standardmäßig sichtbar machen. Im Plan: Default-Show, nur explizit `False` versteckt. Non-Bool-Werte triggern `apply_state returns False` (Mirror-Pattern, analog `show_history`).
- **`widget_version`-Migration:** Bump 2 → 3 triggert Qt's `saveState/restoreState`, alte v2-`windowstate`-Blobs zu ignorieren. **ZWEI** bestehende Tests müssen im selben Commit aktualisiert werden (`widgets_dag_history_test.py:1906` UND `widgets_main_history_test.py:295` — siehe Task 3 Schritt 7b). Alte gespeicherte Qt-Geometrie wird auf Default zurückgesetzt — Feature ist dennoch funktional.
- **v3-windowstate-Test-Blobs:** Der neue `LEGACY_MAINVIEW_V3_WINDOWSTATE` muss erst durch Export der v3-MainView erzeugt werden. Zwei-Phasen-WF (siehe Task 3 Schritt 7c): (Phase A) Code-Änderung main.py + widget_version-Bumps, (Phase B) v3-Blob-Export + neuer Test.
- **Synchrones `git.show()` in FileWidget:** `cola/widgets/filelist.py:67-114` ruft `git.show()` synchron im GUI-Thread. Bei großen Repos (z.B. Linux-Kernel) kann das UI für mehrere Sekunden einfrieren. Identisch mit GitDAG-Verhalten — kein neuer Bug, aber bewusste Designentscheidung. Optimierung (z.B. QThread + async) wäre separates Feature.
- **SetVisible(True) vor initial-history-loaded:** Wenn `apply_state` mit `show_history_files=True` aufgerufen wird, bevor `CommitHistoryWidget._initial_history_loaded=True`, ist der Dock sichtbar aber leer. Kein Crash (FileWidget zeigt leere Tabelle), aber visuell unschön. Mitigation: Dock wird automatisch gefüllt sobald Commit geladen. Edge-Case-Test fehlt aktuell.
- **Hide/Show während ReaderThread läuft:** Kein expliziter Lock zwischen Dock-Visibility und Worker-Thread. In der Praxis sicher (Qt serialisiert GUI-Operationen), aber kein dedizierter Test. Falls Probleme auftauchen, `QSignalBlocker` für den Zeitraum des Visibility-Toggle erwägen.

---

## Reviewer-Hinweise

1. **Spec-Compliance-Review:** Prüft, ob das Feature genau die Dateiauflistung (nicht Diff) liefert, ob der Dock korrekt tabifiziert/platziert ist, und ob die UX GitKraken/SourceTree entspricht (Dateinamen, +/- Spalten).
2. **Code-Quality-Review:** Prüft Wiederverwendung von `FileWidget`, Signal-Verdrahtung analog zu `GitDAG`, State-Persistenz, Testabdeckung (leer, deselektiert, Multi-Select, Persistenz).
