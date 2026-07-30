# Commit-Dateiliste im History-Panel – Implementierungsplan

> **Für Hermes:** Verwende den `plan`-Skill und führe die Tasks mit TDD + unabhängigem Doppel-Review pro Task aus.

**Ziel:** Neben der Commit-Tabelle der History zeigt ein schmales Panel die im ausgewählten Commit geänderten Dateien – mit Status-Symbol (hinzugefügt/geändert/gelöscht) und den bestehenden `+`/`−`-Spalten. Kein Diff-Inhalt.

**Architektur:** Das Panel ist **kein eigener Dock und kein Tab**. Es wird als rechte Hälfte eines `QSplitter` **in `CommitHistoryWidget`** (der wiederverwendbaren History-Graph-Komponente) untergebracht und lebt damit genau dort, wo auch der Commit-Tree lebt. Wiederverwendet wird das existierende `filelist.FileWidget`, das `commits_selected(commits)` bereits vollständig implementiert. Exakt dieses Layout- und Verdrahtungsmuster existiert bereits in `cola/sequenceeditor.py:199` (`splitter(Qt.Horizontal, tree, filewidget)` + `tree.commits_selected → filewidget.commits_selected`).

**Tech Stack:** Python 3, `qtpy` mit PyQt5/PyQt6/PySide6, bestehende Widget-Architektur (`filelist.FileWidget`, `CommitHistoryWidget`, `qtutils.splitter`, `qtutils.add_action_bool`), `pytest`, Qt-Offscreen-Tests, `garden`, `ruff`, `mypy`.

---

## 0. Planänderung gegenüber Revision 5 (Dock/Tab → Panel)

**Produktentscheidung (Nutzer):** Die Dateiliste soll **nicht in einem eigenen Tab neben dem History-Dock** erscheinen, sondern **in einem kleinen Fenster rechts neben der Commit-Tabelle** – vergleichbar mit dem Charakter der Status-View, aber **ausdrücklich keine eigenständige View**: die Liste braucht die History-Graph-Komponente, um zu existieren.

### Was dadurch ersatzlos entfällt

| Entfällt | Grund |
|---|---|
| `history_files_dock` / `create_dock('History Files', …)` | Ein Dock wäre eine eigenständige View. Genau das ist ausgeschlossen. |
| `tabifyDockWidget(historydock, history_files_dock)` | Es entsteht kein Tab mehr. |
| `widget_version` 2 → 3 | `QMainWindow.saveState()` serialisiert **nur** Dock-/Toolbar-Topologie. Ein `QSplitter` innerhalb eines Dock-Widgets taucht dort nicht auf. Ohne neuen Dock gibt es keinen Migrationsbedarf. |
| `LEGACY_MAINVIEW_V3_WINDOWSTATE` + Zwei-Phasen-Commit-Workflow | Hühnerei-Problem existiert nur wegen des `widget_version`-Bumps. |
| Anpassung `widget_version == 2` in zwei Testdateien | Dito. |
| `Ctrl+Y` / `setup_dockwidget_view_menu`-Tupel | Dock-Shortcuts gelten nur für Docks. Erfundene Tastenbelegung entfällt. |
| `dockwidgets`-Liste in `build_view_menu` | Dito. |
| `state['show_history_files']` auf MainView-Ebene inkl. Mirror-/`return False`-Semantik | Der Panel-Zustand gehört zur History-Komponente und wird in deren bestehendem `export_state()`/`apply_state()` mitgeführt. |
| Helper `_setup_tmp_repo_with_commits` mit `MainModel`-Konstruktion und `monkeypatch` von `context.git`/`context.model.git` | **Die Fixture `app_context` (`test/helper.py:85`) legt bereits ein echtes temporäres Git-Repo an und wechselt hinein.** Bestehende Tests in `test/widgets_main_history_test.py` committen dort einfach mit `_git(...)` und warten mit `_wait_for_history(...)`. Der gesamte Monkeypatch-Ordering-Komplex aus Revision 4/5 ist gegenstandslos. |

### Was neu hinzukommt

- Status-Symbole pro Datei (Anforderung „passende Symbole"), gewonnen aus **einem einzigen** `git`-Aufruf.
- Debounce der Dateiliste (Anforderung „ohne Laufzeitprobleme").
- Sichtbarkeits-Guard: ein unsichtbares Panel startet **keinen** `git`-Prozess (Anforderung „ohne Laufzeit-/Speicherprobleme").

---

## 1. Architektur-Kontext (im Code verifiziert)

### Bestehende Komponenten – wiederverwenden, nicht nachbauen

| Komponente | Pfad | Rolle |
|---|---|---|
| `FileWidget` | `cola/widgets/filelist.py:14` | Fertige Dateiliste mit `commits_selected(commits)`, Spalten `Filename/+/−`, Kontextmenü, `files_selected`-Signal |
| `FileTreeWidgetItem` | `cola/widgets/filelist.py:210` | Zeilen-Item, parst `add\tdel\tpath` |
| `CommitHistoryWidget` | `cola/widgets/dag.py:1588` | Wiederverwendbare History-Komponente (Controls + Tree + Ladezustand + eigener State) |
| `CommitHistoryWidget.export_state/is_valid_state/apply_state` | `cola/widgets/dag.py:1924/1937/1965` | Bestehender, validierender State-Kanal der History-Komponente |
| `qtutils.splitter` | `cola/qtutils.py:211` | Splitter-Fabrik des Projekts |
| `icons.status()` / `icons.basename_from_filename()` | `cola/icons.py:135/102` | Bestehende Icon-Policy: Basename zurückgeben, Aufrufer macht `name_from_basename` → `from_name` |
| `CommitDiffWidget` Debounce | `cola/widgets/diff.py:1968-2124` | Etabliertes Muster: `DIFF_DEBOUNCE_MSEC`, `_pending_diff`, `QTimer(singleShot)` |

### Referenz-Implementierung für exakt dieses Layout

`cola/sequenceeditor.py:173-231` (interaktiver Rebase-Editor):

```python
self.filewidget = filelist.FileWidget(context, self, remarks=True)
top = qtutils.splitter(Qt.Horizontal, self.tree, self.filewidget)
top.setSizes([75, 25])
...
self.tree.commits_selected.connect(self.filewidget.commits_selected)
```

Das ist bereits „Commit-Tabelle links, Dateiliste rechts". Der Plan überträgt genau dieses Muster in `CommitHistoryWidget`.

### Signal-Fluss nach der Änderung

```
CommitTreeWidget.commits_selected            (dag.py:1456 selection_changed)
  → CommitHistoryWidget.select_commits       (dag.py:1910)
    → CommitHistoryWidget.commits_selected   (öffentliches Relay, unverändert)
      ├→ GitDAG._history_selection_changed   (unverändert)
      └→ CommitHistoryWidget._schedule_files (NEU, debounced + Sichtbarkeits-Guard)
           → self.filewidget.commits_selected(commits)
```

`apply_result()` (dag.py:1822-1847) emittiert `commits_selected` nach jedem History-Reload und selektiert dabei automatisch den Tip-Commit, wenn die alte Selektion verschwunden ist. Der Debounce sorgt dafür, dass daraus höchstens **ein** `git`-Aufruf pro Reload wird.

---

## 2. Design-Entscheidungen mit Begründung

### D1 – Das Panel gehört in `CommitHistoryWidget`

Die Alternativen wurden geprüft und verworfen:

- **Eigener Dock in `MainView`** → eigenständige View, vom Nutzer ausgeschlossen.
- **Wrapper-Widget** (`QWidget` mit Splitter aus `CommitHistoryWidget` + `FileWidget`, das als Dock-Inhalt dient) → wäre „drumrum gebaut"; bricht außerdem `test/widgets_main_history_test.py:316` (`historydock.widget() is historywidget`) und `cola/widgets/main.py:124`.
- **`FileWidget` von `MainView` erzeugt und von außen in das History-Layout injiziert** → Fernwirkung, keine Wiederverwendbarkeit.

> **Bewusste Architekturänderung, die im Review erwartbar auffällt:**
> `test/widgets_dag_history_test.py:200` (`test_history_widget_owns_history_state_without_window_children`) verbietet aktuell explizit `hasattr(history, 'filewidget')`. Diese Invariante stammt aus der History-Extraktion und meinte „keine Fenster-Komposition in der wiederverwendbaren Komponente". Sie wird **gezielt und dokumentiert** gelockert: `filewidget` wandert von der Verbotsliste in die Pflichtliste. **Unverändert verboten bleiben** `graphview`, `diffwidget`, `log_dock`, `diff_dock`, `file_dock`, `graphview_dock` sowie `history.findChildren(QtWidgets.QDockWidget) == []`. Ein `QSplitter` ist kein Dock; die Einbettbarkeit der Komponente bleibt vollständig erhalten.

### D2 – Opt-in per Konstruktor-Flag `display_files`, Default vom Host

Muster ist 1:1 `display_inline_graph` (dag.py:1602/1644-1650): Konstruktor-Flag + `qtutils.add_action_bool` + Laufzeit-Toggle.

- `MainView` konstruiert mit `display_files=True` → Panel sichtbar.
- `GitDAG` konstruiert mit Default `False` → Panel unsichtbar; das bestehende `file_dock` des DAG-Fensters bleibt unangetastet, es gibt keine doppelte Dateiliste.

> **Signatur-Falle:** `test/widgets_dag_history_test.py:1337` ruft `CommitHistoryWidget(app_context, '--all', 1000, False, parent)` **positional** auf. Der neue Parameter muss deshalb **als letzter** stehen: `(context, ref, count, display_status, parent, display_inline_graph, display_files)`.

> **Migrations-Marker entfällt:** `apply_state` liest `state.get('display_files', self.display_files_action.isChecked())` – exakt wie `display_status` (dag.py:1971-1973). Damit ist der Default **hostabhängig**: alte gespeicherte States ohne den Schlüssel zeigen das Panel im Hauptfenster (Default `True`) und lassen es im DAG-Fenster verborgen (Default `False`). Ein `HISTORY_INLINE_GRAPH_DEFAULT_VERSION`-artiger Marker ist **nicht** nötig, weil der Schlüssel bisher gar nicht existierte.

### D3 – Debounce im Host, **nicht** in `FileWidget`

`test/widgets_dag_history_test.py:368` heißt `test_public_selection_reaches_all_standalone_consumers_synchronously` und prüft nach `history.select_commits([commit])` **synchron** `window.filewidget.topLevelItemCount() == 1` **und** `len(show_calls) == 1`. Synchronität ist damit ein zugesicherter Vertrag von `FileWidget`. Insgesamt hängen fünf Assertions in vier DAG-Tests daran (`window.filewidget.topLevelItemCount()` in den Zeilen 364, 395, 424, 453 und 474).

→ Der Debounce (`FILE_LIST_DEBOUNCE_MSEC = 100`, Muster aus `CommitDiffWidget`) liegt in `CommitHistoryWidget`. `FileWidget.commits_selected` bleibt synchron. GitDAG-Verhalten ändert sich nicht.

### D4 – Sichtbarkeits-Guard (verhindert eine echte Regression)

Ohne Guard würde im DAG-Fenster **jede** Selektion zwei `git show`-Aufrufe auslösen (unsichtbares Panel + sichtbares `file_dock`) und `assert len(show_calls) == 1` sofort brechen. Der Guard ist deshalb nicht nur eine Performance-Maßnahme, sondern Korrektheitsbedingung:

- unsichtbares Panel → kein `git`-Aufruf, Selektion wird als „dirty" gemerkt;
- beim Sichtbarwerden (Toggle, `showEvent`, Dock wieder eingeblendet) → genau ein Nachladen;
- beim Ausblenden → Timer stoppen und `filewidget.clear()` (Items freigeben).

### D5 – Status-Symbole aus **einem** `git`-Aufruf

`git` akzeptiert `--raw` und `--numstat` gemeinsam und liefert erst den Raw-Block, dann den Numstat-Block. Verifiziert für alle vier Aufrufpfade von `FileWidget.commits_selected`:

```
git show <oid> --format= --numstat --raw -z --no-renames
:100644 100644 sha sha M\0cola/widgets/main.py\0…33\t0\tcola/widgets/main.py\0…

git diff-index HEAD --cached --raw --numstat          (ohne -z, Zeilen)
:100644 100644 sha sha M\ta.py
1\t0\ta.py
```

Damit entstehen **keine zusätzlichen Prozesse**. Status-Zeichen (`A`/`M`/`D`/`T`) werden auf bereits vorhandene Icon-Assets abgebildet.

> **Verifizierter Sonderfall Merge-Commit:** `git show <merge> --raw` liefert **nichts**, `--numstat` liefert den kombinierten Diff. Der Parser muss also „Numstat ohne Raw" vertragen; die Status-Map ist dann leer und jede Datei bekommt den Dateityp-Icon-Fallback. Das ist der gleiche Fallback, den `icons.status()` im `else`-Zweig benutzt – kein Sonderweg.

> **Rückwärtskompatibilität der bestehenden DAG-Tests:** Diese monkeypatchen `git.show` auf `(0, '1\t0\ttracked.txt\0', '')` – also Numstat ohne Raw. Sie durchlaufen dadurch automatisch den Fallback-Pfad und bleiben grün.

Mapping (alle Basenames existieren in `cola/icons/`):

| Status | Icon-Basename | Begründung |
|---|---|---|
| `D` | `circle-slash-red.svg` | identisch zu `icons.status()`s „deleted" |
| `A` | `plus.svg` | Asset von `icons.add()` |
| `M`, `T` | `modified.svg` | Asset von `icons.modified()` |
| `R`, `C` | `git-compare.svg` | defensiv; entsteht nur, falls `no_renames` je entfällt |
| unbekannt/leer | `basename_from_filename(path)` | identisch zum `else`-Zweig von `icons.status()` |

### D6 – Kein `widget_version`-Bump, keine Dock-Listen, kein Shortcut

Es entsteht kein `QDockWidget`. `saveState/restoreState`, `build_view_menu`s `dockwidgets`-Liste und `setup_dockwidget_view_menu` bleiben **unverändert**. Der einzige Menüeintrag ist die Toggle-Action neben `display_inline_graph_action` (`cola/widgets/main.py:1050`).

### D7 – Nicht verdrahtete Kontextmenü-Aktionen werden ausgeblendet, nicht liegen gelassen

`FileWidget` bringt `Show History`, `Launch Diff Tool`, `Grab File…`, `Grab File from Parent Commit…` und `Trace Evolution of Line Range…` mit. Diese emittieren Signale, die im DAG-Fenster von `GitDAG`-Handlern (dag.py:2398-2425) bedient werden und im Hauptfenster ohne Host-Verdrahtung **wirkungslos** wären – ein sichtbarer UX-Bug.

→ `MainView` blendet sie aus, exakt nach dem bereits existierenden Muster `_MAIN_HISTORY_UNSUPPORTED_ACTIONS` (`cola/widgets/main.py:59-63`, angewendet in 127-130). `Launch Editor` bleibt sichtbar, weil `edit_paths()` über `cmds.Edit` ohne Host-Verdrahtung funktioniert.

---

## 3. Tasks

Alle Tests laufen offscreen. Repo-Konvention (wie CI und der archivierte History-Graph-Plan):

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_history_filelist_test.py -p no:ruff -q
```

> Falls die Ausführungsumgebung dedizierte Virtualenvs bereitstellt, wird der Interpreter entsprechend vorangestellt; die Argumente bleiben identisch. `-p no:ruff` entspricht `garden test -- -p no:ruff` aus `.github/workflows/ci.yml`. `pytest.ini` setzt `--doctest-modules`: neue Docstrings dürfen **keine** `>>>`-Blöcke enthalten.

---

### Task 1 – Charakterisierung: heutiges `FileWidget`-Verhalten festnageln

**Ziel:** Den Ist-Zustand des gemeinsam genutzten Widgets absichern, bevor Task 2 es anfasst.

**Dateien:** Create `test/widgets_history_filelist_test.py`

**RED/GREEN – Schritt 1:** Charakterisierungstests schreiben. Diese Tests sind **absichtlich sofort grün** – sie sind kein RED-Zyklus, sondern das Sicherheitsnetz, gegen das Task 2 anschließend arbeitet. Ohne sie ist nicht nachweisbar, dass die Umstellung auf `--raw` das bestehende Verhalten des von drei Hosts genutzten Widgets nicht verändert.

Die Datei wird **komplett neu** angelegt. Die `qapp`- und `managed_qobject`-Fixtures werden aus `test/widgets_main_history_test.py:77-105` wortgleich übernommen; sie sind dort lokal definiert und stehen in einer neuen Datei nicht automatisch zur Verfügung (es gibt keine `conftest.py` mit diesen Fixtures). Die erste Zeile `# ruff: noqa: I001` übernimmt die Konvention der beiden bestehenden History-Testdateien (Garden erzwingt Single-Line-Importe in fester Reihenfolge).

```python
# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Characterization tests for FileWidget as used by the history file panel."""

import sys

import pytest

from cola.widgets.filelist import FileTreeWidgetItem
from cola.widgets.filelist import FileWidget
from qtpy import QtCore
from qtpy import QtWidgets

from .helper import app_context

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


def test_list_files_creates_file_tree_items(qapp, app_context, managed_qobject):
    """list_files() builds FileTreeWidgetItem rows with path and +/- columns."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.list_files(['3\t1\tsrc/a.py', '0\t10\tsrc/b.py'])

    assert widget.topLevelItemCount() == 2
    item = widget.topLevelItem(0)
    assert isinstance(item, FileTreeWidgetItem)
    assert item.path == 'src/a.py'
    assert item.text(0) == 'src/a.py'
    assert item.text(1) == '3'
    assert item.text(2) == '1'


def test_empty_commit_selection_clears_the_list(qapp, app_context, managed_qobject):
    """An empty selection clears the widget without running git."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.list_files(['1\t0\tsrc/a.py'])

    widget.commits_selected([])

    assert widget.topLevelItemCount() == 0


def test_selection_emits_selected_paths(qapp, app_context, managed_qobject):
    """itemSelectionChanged emits files_selected with the selected paths."""
    widget = managed_qobject(FileWidget(app_context, None))
    emitted = []
    widget.files_selected.connect(emitted.append)
    widget.list_files(['3\t1\tsrc/a.py', '0\t10\tsrc/b.py'])

    widget.setCurrentItem(widget.topLevelItem(0))

    assert emitted == [['src/a.py']]
```

> **Achtung, in Revision 5 falsch:** Die Numstat-Reihenfolge ist `adds\tdels\tpath` (`filelist.py:213-217`), **nicht** `path\tadds\tdels`. Die alten Snippets (`"src/foo.py\t10\t5"`) hätten `path` auf `'5'` gesetzt und wären am `IndexError`/falschen Pfad gescheitert.

**Schritt 2 – Verifikation:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_history_filelist_test.py -p no:ruff -q
```

**Schritt 3 – Commit:**

```bash
git add test/widgets_history_filelist_test.py
git commit -m "test: characterize FileWidget list and selection behavior"
```

---

### Task 2 – Status-Symbole in der Dateiliste

**Ziel:** Jede Zeile bekommt ein aussagekräftiges Symbol, ohne zusätzlichen `git`-Prozess.

**Dateien:** Modify `cola/icons.py`, `cola/widgets/filelist.py`, `test/widgets_history_filelist_test.py`

**RED – Schritt 1: Tests für Parser, Icon-Mapping und Item**

Die beiden neuen Importe kommen in den **Importblock am Dateikopf** (aus Task 1), nicht mitten in die Datei. Der Block sieht danach so aus – die Reihenfolge folgt der bestehenden Konvention „`cola`-Importe vor `qtpy`-Importen, je eine Zeile":

```python
from cola import icons
from cola.widgets.filelist import FileTreeWidgetItem
from cola.widgets.filelist import FileWidget
from cola.widgets.filelist import parse_status_and_numstat
from qtpy import QtCore
from qtpy import QtWidgets
```

> **Erwarteter RED-Zustand:** `parse_status_and_numstat` existiert noch nicht, der Import scheitert also schon beim Einsammeln des Moduls. Der Testlauf meldet einen **Collection-Error** (`ImportError: cannot import name 'parse_status_and_numstat'`) und dadurch fallen auch die Tests aus Task 1 aus. Das ist der korrekte RED-Zustand dieses Tasks; nach Schritt 5 sind alle Tests der Datei wieder grün. Wer den Zwischenzustand vermeiden will, legt Schritt 1 und die GREEN-Schritte in einem Arbeitsgang an – die Reihenfolge Test-zuerst bleibt davon unberührt.

Die folgenden Testfunktionen werden an das Ende der in Task 1 erstellten Datei angehängt:

```python
def test_parser_splits_nul_separated_raw_and_numstat():
    """"git show --raw --numstat -z" yields a status map plus numstat rows."""
    out = (
        ':100644 100644 aaa bbb M\0cola/main.py\0'
        ':000000 100644 000 ccc A\0cola/new.py\0'
        '33\t0\tcola/main.py\0'
        '10\t0\tcola/new.py\0'
    )

    status_by_path, numstat = parse_status_and_numstat(out, '\0')

    assert status_by_path == {'cola/main.py': 'M', 'cola/new.py': 'A'}
    assert numstat == ['33\t0\tcola/main.py', '10\t0\tcola/new.py']


def test_parser_splits_newline_separated_raw_and_numstat():
    """"git diff-index --raw --numstat" keeps the path inline, newline separated."""
    out = (
        ':100644 100644 aaa bbb M\ta.py\n'
        ':000000 100644 000 ccc A\tb.py\n'
        '1\t0\ta.py\n'
        '1\t0\tb.py\n'
    )

    status_by_path, numstat = parse_status_and_numstat(out, '\n')

    assert status_by_path == {'a.py': 'M', 'b.py': 'A'}
    assert numstat == ['1\t0\ta.py', '1\t0\tb.py']


def test_parser_tolerates_numstat_without_raw():
    """Merge commits emit numstat only; the status map stays empty."""
    status_by_path, numstat = parse_status_and_numstat('1\t0\tt.py\0', '\0')

    assert status_by_path == {}
    assert numstat == ['1\t0\tt.py']


@pytest.mark.parametrize(
    ('status', 'expected'),
    (
        ('A', 'plus.svg'),
        ('M', 'modified.svg'),
        ('T', 'modified.svg'),
        ('D', 'circle-slash-red.svg'),
        ('R', 'git-compare.svg'),
    ),
)
def test_diff_status_icon_names(status, expected):
    """Change status maps onto existing icon assets."""
    assert icons.diff_status('cola/main.py', status) == expected


def test_unknown_status_falls_back_to_the_filetype_icon():
    """Unknown or missing status uses the same fallback as icons.status()."""
    assert icons.diff_status('cola/main.py', '') == icons.basename_from_filename(
        'cola/main.py'
    )


def test_list_files_applies_the_status_map(qapp, app_context, managed_qobject):
    """list_files() stores the per-file status on the item."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.list_files(['1\t0\ta.py', '0\t5\tb.py'], {'a.py': 'A', 'b.py': 'D'})

    assert [widget.topLevelItem(i).status for i in range(2)] == ['A', 'D']
```

> **Icons nicht über `isNull()` prüfen:** `icons.install()` wird ausschließlich in `cola/app.py:275` aufgerufen, im Test also nie. `QIcon('icons:plus.svg')` ist ohne registrierte Suchpfade leer. Deshalb wird die reine Funktion `icons.diff_status()` und das Item-Attribut `status` geprüft, nicht das gerenderte `QIcon`.

**RED – Schritt 1b: RED nachweisen**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_history_filelist_test.py -p no:ruff -q
```

Erwartet: **Collection-Error** `ImportError: cannot import name 'parse_status_and_numstat' from 'cola.widgets.filelist'`. Erscheint stattdessen ein grüner Lauf, wurde der Import am Dateikopf vergessen.

**GREEN – Schritt 2: `cola/icons.py`** – zwei getrennte Einfügungen, damit der Aufbau der Datei erhalten bleibt:

**2a) Die Nachschlagetabelle zu den anderen Nachschlagetabellen**, also direkt hinter `KNOWN_FILE_EXTENSIONS` (endet Zeile 47) und **vor** der ersten Funktion:

```python
DIFF_STATUS_ICONS = {
    'A': 'plus.svg',
    'C': 'git-compare.svg',
    'D': 'circle-slash-red.svg',
    'M': 'modified.svg',
    'R': 'git-compare.svg',
    'T': 'modified.svg',
}
```

**2b) Die Funktion direkt hinter `status()`** (endet Zeile 148 mit `return icon_name`) und **vor** dem Trennkommentar `# Icons creators and SVG file references` (Zeile 148):

```python
def diff_status(filename: str, status: str) -> str:
    """Status icon for a file that changed in a commit diff

    Falls back to the file type icon when the status is unknown, which is what
    "git show" reports for merge commits.

    """
    return DIFF_STATUS_ICONS.get(status, '') or basename_from_filename(filename)
```

> Damit bleibt die Ordnung der Datei erhalten: Tabellen oben, Abfragefunktionen (`basename_from_filename`, `from_filename`, `status`, `diff_status`) in der Mitte, Icon-Fabriken hinter dem Trennkommentar. `cola/icons.py` hat `from __future__ import annotations` (Zeile 2), die Annotationen sind also zulässig.

**GREEN – Schritt 3: `cola/widgets/filelist.py`** – Parser als Modulfunktion:

```python
def parse_status_and_numstat(out, sep):
    """Split combined "--raw --numstat" output into status map and numstat rows

    Git emits the "--raw" block before the "--numstat" block. Raw entries start
    with ":" and carry the change status. With "-z" the path is a separate
    entry, otherwise it follows the info field after a tab. Merge commits emit
    numstat without any raw entries, so the status map can legitimately be
    empty.

    """
    entries = [entry for entry in out.rstrip(sep).split(sep) if entry]
    status_by_path = {}
    numstat = []
    index = 0
    total = len(entries)
    while index < total:
        entry = entries[index]
        index += 1
        if not entry.startswith(':'):
            numstat.append(entry)
            continue
        info, _, inline_path = entry.partition('\t')
        if inline_path:
            path = inline_path
        elif index < total:
            path = entries[index]
            index += 1
        else:
            continue
        status_by_path[path] = info.split(' ')[-1][:1]
    return status_by_path, numstat
```

**GREEN – Schritt 4:** `FileWidget.commits_selected` (`filelist.py:66-127`) vollständig durch die folgende Fassung ersetzen. Es ändern sich genau drei Dinge: (1) `status_by_path = {}` wird neben `paths = []` initialisiert, (2) jeder der vier `git`-Aufrufe bekommt `raw=True`, (3) die vier `paths = [f for f in … if f]`-Listenausdrücke werden durch `status_by_path, paths = parse_status_and_numstat(out, sep)` ersetzt – mit `'\0'` bei `show`/`diff` und `'\n'` bei `diff_index`/`diff_files`, exakt nach dem bereits im Code stehenden `NOTE:`-Kommentar. Der Kommentar selbst bleibt wortgleich erhalten.

```python
    def commits_selected(self, commits):
        if not commits:
            self.clear()
            return

        git = self.context.git
        paths = []
        status_by_path = {}

        if len(commits) > 1:
            # Get a list of changed files for a commit range.
            start_oid = commits[0].oid
            end = commits[-1].oid
            start = start_oid + '~'
            if end == dag.STAGE:
                status, out, _ = git.diff(
                    start,
                    cached=True,
                    z=True,
                    numstat=True,
                    raw=True,
                    no_renames=True,
                )
            elif end == dag.WORKTREE:
                if start_oid == dag.STAGE:
                    status, out, _ = git.diff(
                        z=True, numstat=True, raw=True, no_renames=True
                    )
                else:
                    status, out, _ = git.diff(
                        start, z=True, numstat=True, raw=True, no_renames=True
                    )
            else:
                status, out, _ = git.diff(
                    start, end, z=True, numstat=True, raw=True, no_renames=True
                )
            if status == 0:
                status_by_path, paths = parse_status_and_numstat(out, '\0')
        else:
            # Get the list of changed files in a single commit.
            commit = commits[0]
            oid = commit.oid
            # NOTE: The output from "git diff-files --numstat -z" is not equivalent
            # to the output of "git show --numstat -z". "git diff-files" does not
            # emit a NULL separator between each entry. That's why we use the
            # default output (without "-z") and split on newline instead.
            # This is also true for "git diff-index" as well.
            if oid == dag.STAGE:
                status, out, _ = git.diff_index(
                    'HEAD', cached=True, numstat=True, raw=True, _readonly=True
                )
                if status == 0:
                    status_by_path, paths = parse_status_and_numstat(out, '\n')
            elif oid == dag.WORKTREE:
                status, out, _ = git.diff_files(
                    numstat=True, raw=True, _readonly=True
                )
                if status == 0:
                    status_by_path, paths = parse_status_and_numstat(out, '\n')
            else:
                status, out, _ = git.show(
                    oid,
                    format='',
                    numstat=True,
                    raw=True,
                    no_renames=True,
                    z=True,
                    _readonly=True,
                )
                if status == 0:
                    status_by_path, paths = parse_status_and_numstat(out, '\0')

        self.list_files(paths, status_by_path)
```

> **Namensgebung beachten:** Die lokale Variable `status` ist in dieser Methode der **Git-Returncode** und behält diese Bedeutung. Die Datei-Status liegen ausschließlich in `status_by_path`. Beim Bearbeiten nicht verwechseln.
>
> **Zeilenlänge:** `pyproject.toml:86` setzt `line-length = 88`. Nach dem Editieren `garden check/fmt` laufen lassen und die Formatierung übernehmen, statt sie von Hand zu erraten.

**GREEN – Schritt 5:** `list_files` und `FileTreeWidgetItem`:

```python
    def list_files(self, files_log, status_by_path=None):
        self.clear()
        if not files_log:
            return
        status_by_path = status_by_path or {}
        files = []
        for filename in files_log:
            item = FileTreeWidgetItem(filename)
            item.set_status(status_by_path.get(item.path, ''))
            files.append(item)
        self.insertTopLevelItems(0, files)
```

```python
class FileTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, file_log, parent=None):
        QtWidgets.QTreeWidgetItem.__init__(self, parent)
        texts = file_log.split('\t')
        self.path = path = texts[2]
        self.status = ''
        self.setText(0, path)
        self.setText(1, texts[0])
        self.setText(2, texts[1])
        self.set_status('')

    def set_status(self, status):
        """Set the change status and its icon"""
        self.status = status
        basename = icons.diff_status(self.path, status)
        self.setIcon(0, icons.from_name(icons.name_from_basename(basename)))
        label = DIFF_STATUS_LABELS.get(status)
        if label:
            self.setToolTip(0, label)
```

mit dieser Tabelle als Modulkonstante am Kopf von `filelist.py`, direkt unter den Importen:

```python
DIFF_STATUS_LABELS = {
    'A': N_('Added'),
    'C': N_('Copied'),
    'D': N_('Deleted'),
    'M': N_('Modified'),
    'R': N_('Renamed'),
    'T': N_('Type changed'),
}
```

> Der Tooltip wird **nur** gesetzt, wenn ein Label existiert. Ohne diese Bedingung bekämen Merge-Commit-Zeilen den Dateipfad als Tooltip, was gegenüber „kein Tooltip" keinerlei Information hinzufügt.

**Import in `filelist.py`:** `from .. import icons` als **neue Zeile zwischen `from .. import hotkeys` und `from .. import qtutils`** (Zeilen 7-8). Die Datei nutzt Single-Line-Importe in alphabetischer Reihenfolge; jede andere Position lässt `garden check/fmt` bzw. Ruff anschlagen. `N_` ist über `from ..i18n import N_` (Zeile 9) bereits vorhanden.

> Der Default `set_status('')` bedeutet: **alle** Hosts von `FileWidget` (History-Panel, DAG-`file_dock`, Rebase-Editor `cola/sequenceeditor.py:173`) bekommen mindestens ein Dateityp-Icon; nur die Commit-Pfade bekommen zusätzlich das Status-Icon. Es entsteht keine Sonderbehandlung pro Host.
>
> **Kosten:** `icons.from_name` ist mit `@decorators.memoize` versehen (`cola/icons.py:74-77`), es entsteht also **ein** `QIcon` pro Basename für den gesamten Prozess – nicht eines pro Zeile. Bei einem Commit mit tausenden Dateien wachsen dadurch keine Icon-Objekte mit.

**Schritt 6 – Verifikation (Gegenprobe: DAG darf sich nicht ändern):**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest \
  test/widgets_history_filelist_test.py \
  test/widgets_dag_history_test.py \
  -p no:ruff -q
```

Erwartet: **alles grün**. Die bestehenden DAG-Tests monkeypatchen `git.show` auf `(0, '1\t0\ttracked.txt\0', '')` – also Numstat **ohne** Raw-Block (`test/widgets_dag_history_test.py:341-345` und `406-410`, dazu dieselbe Konstruktion in `test_failed_or_stale_result_preserves_all_standalone_views`). Sie durchlaufen damit exakt den Merge-Commit-Fallback und beweisen, dass die Umstellung rückwärtskompatibel ist. Schlägt einer dieser Tests fehl, ist der Parser zu streng.

**Schritt 6b – Manueller Rauchtest des dritten Hosts**

`cola/sequenceeditor.py:173` ist der dritte Nutzer von `FileWidget.commits_selected` und hat **keine** automatisierten Tests (`grep -rln sequenceeditor test/` liefert nichts). Der interaktive Rebase-Editor wird deshalb einmal von Hand geöffnet und geprüft, dass die Dateiliste rechts weiterhin Einträge samt neuem Symbol zeigt:

```bash
GIT_SEQUENCE_EDITOR="$PWD/bin/git-cola-sequence-editor" git rebase -i HEAD~3
```

Im Editor einen Commit auswählen, die Dateiliste rechts prüfen, dann „Cancel". Ergebnis im Task-Protokoll vermerken. `bin/git-cola-sequence-editor` ist der im Repository mitgelieferte Starter (`pyproject.toml:82`); ein `python3 -m cola.sequenceeditor` funktioniert nicht, das Modul hat keinen `__main__`-Block.

**Schritt 7 – Commit:**

```bash
git add cola/icons.py cola/widgets/filelist.py test/widgets_history_filelist_test.py
git commit -m "feat: show change-status icons in the commit file list"
```

---

### Task 3 – Dateien-Panel in `CommitHistoryWidget`

**Ziel:** Splitter mit Commit-Tabelle links und Dateiliste rechts, opt-in, debounced, mit Sichtbarkeits-Guard.

**Dateien:** Modify `cola/widgets/dag.py`, `test/widgets_dag_history_test.py`

**RED – Schritt 1: Tests** – ans Ende von `test/widgets_dag_history_test.py` anhängen. Alle verwendeten Namen sind dort bereits vorhanden: `CommitHistoryWidget` (Import Zeile 20 der Datei), `dag`, `_commit` (Zeile 88), `_graph_result` (Zeile 100), `QtTest`, `time`, `monkeypatch`, `managed_qobject`, `app_context`. Es ist **kein** neuer Import nötig.

```python
def test_history_widget_hides_the_file_panel_by_default(
    qapp, app_context, managed_qobject
):
    """Standalone hosts keep their own file dock; the inline panel stays off."""
    history = managed_qobject(CommitHistoryWidget(app_context))
    history.show()
    qapp.processEvents()

    assert history.files_splitter.indexOf(history.treewidget) == 0
    assert history.files_splitter.indexOf(history.filewidget) == 1
    assert not history.filewidget.isVisible()
    assert not history.display_files_action.isChecked()


def test_hidden_file_panel_never_runs_git(
    qapp, app_context, managed_qobject, monkeypatch
):
    """A hidden panel must not spawn a git process for a selection."""
    show_calls = []
    monkeypatch.setattr(
        app_context.git,
        'show',
        lambda *args, **kwargs: (
            show_calls.append((args, kwargs)) or (0, '1\t0\ta.py\0', '')
        ),
    )
    history = managed_qobject(CommitHistoryWidget(app_context))
    history.show()
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'tip')
    history.apply_result((commit,), _graph_result((commit,)))

    QtTest.QTest.qWait(CommitHistoryWidget.FILE_LIST_DEBOUNCE_MSEC * 2)
    qapp.processEvents()

    assert show_calls == []
    assert history.filewidget.topLevelItemCount() == 0


def test_visible_file_panel_lists_the_selected_commit(
    qapp, app_context, managed_qobject, monkeypatch
):
    """An enabled panel loads the file list once the selection settles."""
    monkeypatch.setattr(
        app_context.git,
        'show',
        lambda *_args, **_kwargs: (
            0, ':100644 100644 aaa bbb M\0a.py\0' '1\t0\ta.py\0', ''
        ),
    )
    history = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    history.show()
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'tip')

    history.apply_result((commit,), _graph_result((commit,)))
    _wait_for_files(qapp, history)

    assert history.filewidget.isVisible()
    assert history.filewidget.topLevelItemCount() == 1
    assert history.filewidget.topLevelItem(0).path == 'a.py'
    assert history.filewidget.topLevelItem(0).status == 'M'


def test_rapid_selection_changes_load_the_file_list_once(
    qapp, app_context, managed_qobject, monkeypatch
):
    """Stepping through commits must not spawn one git process per commit."""
    show_calls = []
    monkeypatch.setattr(
        app_context.git,
        'show',
        lambda *args, **kwargs: (
            show_calls.append(args) or (0, '1\t0\ta.py\0', '')
        ),
    )
    history = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    history.show()
    factory = dag.CommitFactory()
    root = _commit(app_context, factory, 'root')
    tip = _commit(app_context, factory, 'tip', (root,))
    history.apply_result((root, tip), _graph_result((root, tip)))
    _wait_for_files(qapp, history)
    show_calls.clear()

    history.select_commits([root])
    history.select_commits([tip])
    history.select_commits([root])
    assert show_calls == []

    _wait_for_files(qapp, history)
    assert len(show_calls) == 1


def test_empty_selection_clears_the_panel_immediately(
    qapp, app_context, managed_qobject, monkeypatch
):
    """Deselecting clears the list without waiting for the debounce."""
    monkeypatch.setattr(
        app_context.git, 'show', lambda *_a, **_k: (0, '1\t0\ta.py\0', '')
    )
    history = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    history.show()
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'tip')
    history.apply_result((commit,), _graph_result((commit,)))
    _wait_for_files(qapp, history)

    history.select_commits([])

    assert history.filewidget.topLevelItemCount() == 0
    assert not history._files_timer.isActive()


def test_toggling_the_panel_reloads_and_releases_the_list(
    qapp, app_context, managed_qobject, monkeypatch
):
    """Hiding frees the items; showing reloads the current selection."""
    monkeypatch.setattr(
        app_context.git, 'show', lambda *_a, **_k: (0, '1\t0\ta.py\0', '')
    )
    history = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    history.show()
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'tip')
    history.apply_result((commit,), _graph_result((commit,)))
    _wait_for_files(qapp, history)

    history.display_files(False)
    assert not history.filewidget.isVisible()
    assert history.filewidget.topLevelItemCount() == 0

    history.display_files(True)
    qapp.processEvents()
    assert history.filewidget.topLevelItemCount() == 1
```

Helper neben den bestehenden Wartehelfern der Datei (`_spy_count`, `_spy_payload`, `_tree` ab Zeile 109) einfügen:

```python
def _wait_for_files(qapp, history):
    """Pump the event loop until the debounced file list has been applied."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        qapp.processEvents()
        if not history._files_timer.isActive():
            break
        QtTest.QTest.qWait(10)
    qapp.processEvents()
    assert not history._files_timer.isActive()
```

> **Abbruchbedingung:** Der Helper wartet **ausschließlich** darauf, dass der Single-Shot-Timer nicht mehr aktiv ist. Qt stoppt einen Single-Shot-Timer, bevor `timeout` emittiert wird, und `processEvents()` führt den angehängten Slot synchron aus – nach dem Verlassen der Schleife ist das Laden also abgeschlossen. Es darf **keine** zusätzliche Bedingung auf ein „Pending"-Feld geprüft werden: die Implementierung unten hält die letzte Selektion bewusst in `self.selection` (bestehendes Attribut) und setzt kein Feld auf `None` zurück – eine solche Bedingung würde nie eintreten und den Helper in den Timeout laufen lassen.
>
> `time` und `QtTest` sind in `test/widgets_dag_history_test.py` bereits importiert; nichts Neues nötig.

**RED – Schritt 2: Strukturtest bewusst umstellen** (`test/widgets_dag_history_test.py:200`):

In `test_history_widget_owns_history_state_without_window_children`:

1. In der **ersten** Schleife (`for name in (...)`, aktuell `'revtext'` … `'last_successful_cache_key'`) die drei Namen `'filewidget'`, `'files_splitter'` und `'display_files_action'` ergänzen.
2. In der **zweiten** Schleife (`assert not hasattr(history, name)`, aktuell `'graphview'` … `'graphview_dock'`) den Eintrag `'filewidget'` **entfernen**. `'graphview'`, `'diffwidget'`, `'log_dock'`, `'diff_dock'`, `'file_dock'`, `'graphview_dock'` bleiben stehen.
3. `assert history.findChildren(QtWidgets.QDockWidget) == []` bleibt unverändert die letzte Zeile.
4. Docstring der Testfunktion ergänzen um: die Komponente besitzt ihre eigene Dateiliste, aber weiterhin keine Fenster-Komposition und keine Docks.

**RED – Schritt 3: RED nachweisen**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py \
  -k "file_panel or owns_history_state" -p no:ruff -q
```

Erwartet: **FAIL**. Konkret `AttributeError: 'CommitHistoryWidget' object has no attribute 'files_splitter'` in den neuen Tests und `AssertionError: filewidget` in `test_history_widget_owns_history_state_without_window_children`, weil dessen erste Schleife das noch fehlende Attribut verlangt.

**GREEN – Schritt 4: Konstruktor** (`dag.py:1595-1603`, neuer Parameter **zuletzt**):

```python
    FILE_LIST_DEBOUNCE_MSEC = 100

    def __init__(
        self,
        context,
        ref='--all',
        count=1000,
        display_status=False,
        parent=None,
        display_inline_graph=False,
        display_files=False,
    ):
```

**GREEN – Schritt 5: Widget, Action, Timer** – direkt nach `self.treewidget = CommitTreeWidget(context, self)` (Zeile 1642) und in unmittelbarer Nachbarschaft zu `display_inline_graph_action`:

```python
        self.filewidget = filelist.FileWidget(context, self)
        # Debounce the file list so that holding an arrow key in the commit
        # table does not spawn a "git show" for every commit passed over.
        self._files_dirty = False
        self._files_timer = QtCore.QTimer(self)
        self._files_timer.setSingleShot(True)
        self._files_timer.setInterval(self.FILE_LIST_DEBOUNCE_MSEC)
        self._files_timer.timeout.connect(self._load_pending_files)

        self.display_files_action = qtutils.add_action_bool(
            self,
            N_('Display Commit Files'),
            self.display_files,
            display_files,
        )
        self.display_files(display_files)
```

> **Kein eigenes „Pending"-Feld:** Die aktuelle Auswahl liegt bereits in `self.selection` (gesetzt in `__init__` Zeile 1610, in `select_commits` Zeile 1912 vor dem `emit` in Zeile 1914, und in `apply_result` Zeile 1843 vor dem `emit` in Zeile 1847). Ein zusätzliches `_pending_files` wäre eine Doppelhaltung desselben Zustands und wird deshalb bewusst nicht eingeführt. `_files_dirty` ist die einzige neue Zustandsvariable und beantwortet ausschließlich die Frage „wurde ein Laden übersprungen, weil das Panel unsichtbar war?".
>
> `qtutils.connect_action_bool` verbindet `triggered[bool]` (qtutils.py:61-63), **nicht** `toggled`. `setChecked()` im Konstruktor löst den Callback also nicht aus – deshalb der explizite Aufruf, exakt wie bei `display_inline_graph` (dag.py:1650).
>
> **Platzierung:** `self.selection = []` steht bereits in Zeile 1610, also weit vor Zeile 1642. `self.display_files(display_files)` darf `self.selection` daher gefahrlos lesen.

**GREEN – Schritt 6: Layout** – `self.treewidget` im vbox durch den Splitter ersetzen (Zeile 1668-1671):

```python
        self.files_splitter = qtutils.splitter(
            Qt.Horizontal, self.treewidget, self.filewidget
        )
        self.files_splitter.setChildrenCollapsible(False)
        self.files_splitter.setSizes([75, 25])
        layout = qtutils.vbox(
            defs.no_margin, defs.spacing, controls_widget, self.files_splitter
        )
        self.setLayout(layout)
```

> `setChildrenCollapsible(False)` verhindert, dass das Panel auf Breite 0 gezogen wird, während die Toggle-Action „an" anzeigt (Muster: `cola/widgets/stash.py:96`). Das Größenverhältnis 75/25 ist das des Rebase-Editors (`sequenceeditor.py:200`).
>
> **Reihenfolge geprüft:** `QSplitter.addWidget()` überschreibt eine zuvor gesetzte Sichtbarkeit **nicht** – offscreen unter PyQt5 verifiziert. `self.display_files(display_files)` darf deshalb wie bei `display_inline_graph` (dag.py:1650) direkt bei der Action stehen, also vor dem Splitter-Aufbau.

**GREEN – Schritt 7: Verdrahtung** – neben den bestehenden `connect`-Aufrufen (Zeile 1673 ff.):

```python
        self.commits_selected.connect(self._schedule_files)
```

**GREEN – Schritt 8: Methoden** – direkt hinter `select_commits` (dag.py:1910-1914) einfügen:

```python
    def display_files(self, enabled):
        """Show or hide the commit file list next to the commit table"""
        self.filewidget.setVisible(enabled)
        if enabled:
            self.refresh_files()
        else:
            self._files_timer.stop()
            # Release the items while hidden; reload when shown again.
            self._files_dirty = bool(self.selection)
            self.filewidget.clear()

    def _schedule_files(self, commits):
        """Debounce the file list update for a new selection"""
        if not commits:
            self._files_timer.stop()
            self._files_dirty = False
            self.filewidget.clear()
            return
        if self.stopping:
            return
        if self.filewidget.isVisible():
            self._files_timer.start()
        else:
            # A hidden panel never runs git; the selection is applied when the
            # panel becomes visible again.
            self._files_dirty = True

    def _load_pending_files(self):
        """Load the file list for the most recently selected commits"""
        if not self.selection or not self.filewidget.isVisible():
            return
        self._files_dirty = False
        self.filewidget.commits_selected(self.selection)

    def refresh_files(self):
        """Apply a selection that was skipped while the panel was hidden"""
        if self._files_dirty and self.filewidget.isVisible():
            self._files_timer.stop()
            self._load_pending_files()
```

> `if self.stopping: return` spiegelt die bestehende Schutzklausel in `request_history` (dag.py:1700-1701): nach `stop_and_wait()` wird keine neue Arbeit mehr eingeplant.

**GREEN – Schritt 9: Drei Einzeiler in bestehenden Methoden**

Diese drei Ergänzungen sind erforderlich, damit das Panel keinen Zustand überlebt, den die Komponente bereits verwirft:

**9a) `clear()`** (dag.py:1916-1922) – die Methode heißt laut Docstring „Clear the tree and all applied history state"; die Dateiliste ist Teil dieses Zustands. Nach `self.treewidget.clear()` ergänzen:

```python
        self.filewidget.clear()
```

> Aufrufer ist `apply_result` (dag.py:1838) und `GitDAG.clear()` (dag.py:2367).

**9b) `stop_and_wait()`** (dag.py:1849-1862) – direkt hinter `self.pending_cache_metadata = None` ergänzen:

```python
        self._files_timer.stop()
```

> Sonst kann der Single-Shot-Timer nach `MainView.closeEvent` → `historywidget.stop_and_wait()` (main.py:1031) noch einmal feuern und beim Herunterfahren ein `git show` starten.

**9c) `showEvent()`** (dag.py:2008-2013) – als letzte Zeile der Methode, **außerhalb** des `if not self._widgets_initialized`-Blocks:

```python
    def showEvent(self, event):
        super().showEvent(event)
        if not self._widgets_initialized:
            self._widgets_initialized = True
            self.maxresults.setMinimumHeight(self.revtext.height())
        self.refresh_files()
```

> Damit lädt das Panel nach, wenn das History-Dock wieder eingeblendet wird. `refresh_files()` ist ein No-op, solange `_files_dirty` False ist – `showEvent` feuert also nicht unkontrolliert `git`-Aufrufe.
>
> **Verifiziert:** Innerhalb des `showEvent` des Elternwidgets liefert das Kind bereits `isVisible() == True` – Qt zeigt die Kinder, bevor es das `QShowEvent` an das Elternwidget schickt. Offscreen unter PyQt5 mit genau dieser Splitter-Konstruktion geprüft (Ergebnis `[True, True]` für erstes Anzeigen und erneutes Anzeigen nach `hide()`). Der Sichtbarkeits-Guard in `_load_pending_files` blockiert das Nachladen an dieser Stelle also nicht.

**Schritt 10 – Verifikation:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py -p no:ruff -q
```

Erwartung: alle bestehenden DAG-Tests bleiben grün – insbesondere `test_public_selection_reaches_all_standalone_consumers_synchronously` mit `len(show_calls) == 1`. Schlägt genau dieser Test mit `2 != 1` fehl, greift der Sichtbarkeits-Guard aus Schritt 8 nicht.

**Schritt 11 – Commit:**

```bash
git add cola/widgets/dag.py test/widgets_dag_history_test.py
git commit -m "feat: add an opt-in commit file panel to CommitHistoryWidget"
```

---

### Task 4 – State-Persistenz im bestehenden History-State

**Ziel:** Sichtbarkeit und Splitter-Breite überleben den Neustart – über den vorhandenen State-Kanal der Komponente, ohne neue Ebene.

**Dateien:** Modify `cola/widgets/dag.py`, `test/widgets_dag_history_test.py`, `test/widgets_main_history_test.py`

**RED – Schritt 1: Tests** – ebenfalls ans Ende von `test/widgets_dag_history_test.py`.

```python
def test_history_state_round_trips_the_file_panel(
    qapp, app_context, managed_qobject
):
    """Panel visibility and splitter sizes survive an export/apply round trip."""
    first = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    second = managed_qobject(CommitHistoryWidget(app_context))

    state = first.export_state()

    assert state['display_files'] is True
    assert state['files_sizes'] == first.files_splitter.sizes()
    assert second.apply_state(state)
    assert second.display_files_action.isChecked()
    assert second.export_state()['display_files'] is True


def test_missing_display_files_keeps_the_host_default(
    qapp, app_context, managed_qobject
):
    """Legacy state without the key keeps whatever the host asked for."""
    enabled = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    disabled = managed_qobject(CommitHistoryWidget(app_context))
    legacy = {
        'ref': 'HEAD',
        'count': 100,
        'display_inline_graph': False,
        'display_status': False,
        'log': {'column_widths': [240, 120]},
    }

    assert enabled.apply_state(dict(legacy))
    assert disabled.apply_state(dict(legacy))

    assert enabled.display_files_action.isChecked()
    assert not disabled.display_files_action.isChecked()


def test_apply_state_restores_the_splitter_sizes(
    qapp, app_context, managed_qobject, monkeypatch
):
    """Stored splitter sizes are handed back to the splitter on restore."""
    widget = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    applied = []
    monkeypatch.setattr(widget.files_splitter, 'setSizes', applied.append)
    state = widget.export_state()
    state['files_sizes'] = [640, 160]

    assert widget.apply_state(state)

    assert applied == [[640, 160]]



@pytest.mark.parametrize(
    ('key', 'value'),
    (
        ('display_files', 'yes'),
        ('files_sizes', 'wide'),
        ('files_sizes', [240, 'wide']),
        ('files_sizes', [240, True]),
    ),
)
def test_invalid_file_panel_state_is_rejected(
    key, value, qapp, app_context, managed_qobject
):
    """Corrupt panel state is rejected atomically, like every other key."""
    widget = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    state = widget.export_state()
    state[key] = value
    before = widget.export_state()

    assert not widget.is_valid_state(state)
    assert not widget.apply_state(state)
    assert widget.export_state() == before
```

> **Warum kein Vergleich gegen feste Pixelwerte:** `QSplitter.sizes()` liefert erst nach dem ersten Layout aussagekräftige Werte; ein nie gezeigtes Widget liefert je nach Binding `[0, 0]` oder Hint-Werte. Deshalb prüft `test_history_state_round_trips_the_file_panel` den Export **gegen den Live-Wert des Splitters** und das Zurückschreiben wird separat über `test_apply_state_restores_the_splitter_sizes` mit einem geschatteten `setSizes` nachgewiesen. Die Instanz-Attribut-Schattierung an einem `QSplitter` wurde offscreen unter PyQt5 verifiziert und funktioniert unter PyQt6/PySide6 gleichermaßen.
>
> `apply_state` prüft `is_valid_state` als allererstes (dag.py:1967-1968) und kehrt vor jeder Zustandsänderung zurück – deshalb genügt `export_state() == before` als Nachweis der Atomarität.

**RED – Schritt 1b: RED nachweisen**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py \
  -k "file_panel or display_files or splitter_sizes" -p no:ruff -q
```

Erwartet: **FAIL** mit `KeyError: 'display_files'` bzw. `AssertionError`, weil `export_state()` die neuen Schlüssel noch nicht liefert und `is_valid_state` sie noch nicht prüft.

**GREEN – Schritt 2: `export_state`** (dag.py:1924-1934):

```python
        return {
            'ref': get(self.revtext),
            'count': get(self.maxresults),
            'display_inline_graph': self.display_inline_graph_action.isChecked(),
            'display_status': self.display_status_action.isChecked(),
            'display_files': self.display_files_action.isChecked(),
            'files_sizes': get(self.files_splitter),
            'log': log_state,
        }
```

**GREEN – Schritt 3: `is_valid_state`** (dag.py:1936-1963)

> **Einfügestelle exakt beachten – hier entsteht sonst ein stiller Fehler.** Der Block muss **unmittelbar nach** dem großen `if not ( isinstance(ref, str) and … ): return False` (endet Zeile 1953 mit `return False`) und **vor** `log_state = state.get('log')` (Zeile 1954) stehen. Steht er weiter unten, greift er nicht mehr: die Methode kehrt bei fehlendem `'log'`-Schlüssel mit `return True` vorzeitig zurück (Zeile 1955-1956), und die neue Prüfung würde für genau die Legacy-States übersprungen, für die sie gedacht ist.

```python
        display_files = state.get('display_files', False)
        if not isinstance(display_files, bool):
            return False
        files_sizes = state.get('files_sizes')
        if files_sizes is not None and not (
            isinstance(files_sizes, (list, tuple))
            and all(
                isinstance(size, int) and not isinstance(size, bool)
                for size in files_sizes
            )
        ):
            return False
```

> `is_valid_state` ist eine `@staticmethod` (Zeile 1936) und hat **kein** `self`. Der Default `False` in `state.get('display_files', False)` dient hier ausschließlich der Typprüfung – der hostabhängige Default wird in `apply_state` gesetzt (Schritt 4). Ein Zugriff auf `self.display_files_action` an dieser Stelle wäre ein `NameError`.
>
> `not isinstance(size, bool)` ist kein Zierrat: `isinstance(True, int)` ist in Python `True`. Ohne die Zusatzprüfung würde `[240, True]` als gültige Größenliste durchgehen. Dieselbe Konstruktion nutzt die Methode bereits für `count` (Zeile 1948) und für `column_widths` (Zeile 1961-1962).

**GREEN – Schritt 4: `apply_state`** (dag.py:1965-1985)

Die bestehende Methode liest ihre Werte in einem Block und wendet sie danach an. Genauso wird verfahren: die beiden Lesezeilen **zu den anderen `state.get`-Zeilen** (nach `display_inline_graph = ...`, Zeile 1975), die Anwendungszeilen **vor** das abschließende `return True`.

Lesen:

```python
        display_files = state.get(
            'display_files', self.display_files_action.isChecked()
        )
        files_sizes = state.get('files_sizes')
```

Anwenden:

```python
        self.display_files(display_files)
        with qtutils.BlockSignals(self.display_files_action):
            self.display_files_action.setChecked(display_files)
        if files_sizes:
            self.files_splitter.setSizes(list(files_sizes))
```

> **Präzisierung zum Default:** In derselben Methode benutzt `display_status` den Action-Zustand als Default (Zeile 1972-1974), `display_inline_graph` dagegen ein hartes `True` (Zeile 1975). Wir folgen **`display_status`** – nur der Action-Default macht das Verhalten hostabhängig und erspart damit einen Migrationsmarker (siehe D2). Ein hartes `True` würde im DAG-Fenster ein doppeltes Dateipanel einblenden.

**Schritt 5: Bestehende Erwartungen an den exportierten State nachziehen**

Der State bekommt zwei neue Schlüssel. Vier Stellen brechen dadurch. **Vollständige Liste mit exakter Anweisung:**

**5a) `test/widgets_main_history_test.py:33-39** – `HISTORY_KEYS` erweitern:

```python
HISTORY_KEYS = {
    'ref',
    'count',
    'display_inline_graph',
    'display_status',
    'display_files',
    'files_sizes',
    'log',
}
```

**5b) `test/widgets_main_history_test.py:991-997`** – der Exakt-Dict-Vergleich in `test_export_owns_visibility_and_nests_exact_canonical_history_state` (Zeile 970). Kein geratener Pixelwert, sondern der Live-Wert des Splitters:

```python
    assert state['history'] == {
        'ref': 'main --',
        'count': 321,
        'display_inline_graph': True,
        'display_status': True,
        'display_files': False,
        'files_sizes': history.files_splitter.sizes(),
        'log': {'column_widths': [211, 122]},
    }
```

> **Wichtig – in Task 4 lautet der Wert `'display_files': False`.** `MainView` aktiviert das Panel erst in Task 5; bis dahin exportiert die History-Komponente im Hauptfenster den Host-Default `False`. Erst Task 5 Schritt 5b zieht den Wert auf `True`. So bleibt die Suite nach **jedem** Task grün. `history` ist in diesem Test bereits als `window.historywidget` gebunden (Zeile 975).

**5c) `test/widgets_dag_history_test.py:1474-1494`** (`test_gitdag_applies_and_round_trips_nested_history_state`) – das `history`-Literal ist zugleich Eingabe für `apply_state` und Sollwert für `exported['history']`. Beide neuen Schlüssel ergänzen:

```python
    history = {
        'ref': 'stored-ref',
        'count': 321,
        'display_inline_graph': False,
        'display_status': False,
        'display_files': False,
        'files_sizes': widget.historywidget.files_splitter.sizes(),
        'log': {'column_widths': [240, 120]},
    }
```

**5d) `test/widgets_dag_history_test.py:1497-1517`** (`test_gitdag_migrates_legacy_flat_history_state_to_canonical_nested_state`) – hier ist der flache Legacy-Input bewusst **ohne** die neuen Schlüssel, es gibt also keinen Sollwert dafür. `assert exported['history'] == legacy` wird ersetzt durch:

```python
    assert {key: exported['history'][key] for key in legacy} == legacy
    assert exported['history']['display_files'] is False
```

**Vollständigkeitsprüfung vor dem Commit:**

```bash
grep -rn "'display_inline_graph':" test/
```

Jeder Treffer, der Teil eines Vergleichs mit `export_state()` ist, muss die neuen Schlüssel führen. Reine Eingabe-Literale für `apply_state` dürfen sie weglassen.

> `test/widgets_dag_history_test.py:1464` prüft `{'ref','count','display_inline_graph','display_status','log'} & state.keys()` – dieses Literal bleibt unverändert korrekt, weil es nur nachweist, dass die History-Schlüssel **nicht** flach im DAG-State landen.
>
> `GitDAG.apply_state`s Legacy-Pfad (`dag.py:2232-2238`) bleibt ebenfalls unverändert: flache Legacy-States können die neuen Schlüssel nicht enthalten, und `is_valid_state` akzeptiert ihr Fehlen.

**Schritt 6 – Verifikation & Commit:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest \
  test/widgets_dag_history_test.py test/widgets_main_history_test.py -p no:ruff -q
```

```bash
git add cola/widgets/dag.py test/widgets_dag_history_test.py test/widgets_main_history_test.py
git commit -m "feat: persist commit file panel visibility and width"
```

---

### Task 5 – Aktivierung im Hauptfenster

**Ziel:** Das Panel ist im Hauptfenster standardmäßig sichtbar, im View-Menü umschaltbar, und es gibt keine wirkungslosen Kontextmenü-Einträge.

**Dateien:** Modify `cola/widgets/main.py`, `test/widgets_main_history_test.py`

**RED – Schritt 1: Integrationstests.** Es wird **kein** eigener Repo-Helper gebaut: die Fixture `app_context` (`test/helper.py:85-104`) legt bereits ein temporäres Repo an, wechselt hinein und ruft `initialize_repo()` (`test/helper.py:72-81`) auf – dort werden `A` und `B` erzeugt und gestaged. Die Datei bringt außerdem `_git` (Zeile 135), `_show` (Zeile 195) und `_wait_for_history` (Zeile 141) mit. Neue Dateien werden mit dem in der Datei üblichen `with open(..., 'w', encoding='utf-8')` erzeugt (Vorbild Zeile 714), **nicht** über einen neuen Import aus `helper`.

```python
def _wait_for_commit_files(qapp, window, expected):
    """Pump the event loop until the debounced file list matches expected."""
    history = window.historywidget
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        qapp.processEvents()
        paths = {
            history.filewidget.topLevelItem(i).path
            for i in range(history.filewidget.topLevelItemCount())
        }
        if not history._files_timer.isActive() and paths == expected:
            return paths
        QtTest.QTest.qWait(10)
    raise AssertionError(f'file list never became {expected}')


def test_main_history_lists_files_of_the_selected_commit(
    qapp, main_context, managed_qobject
):
    """The commit file panel lists the files of the selected commit."""
    _git('commit', '-m', 'base')
    main_context.model.update_status()
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    _wait_for_history(qapp, window)

    _wait_for_commit_files(qapp, window, {'A', 'B'})

    filewidget = window.historywidget.filewidget
    assert filewidget.isVisible()
    assert {
        filewidget.topLevelItem(i).status
        for i in range(filewidget.topLevelItemCount())
    } == {'A'}


def test_main_history_file_panel_follows_the_selection(
    qapp, main_context, managed_qobject
):
    """Selecting an older commit updates the file list."""
    _git('commit', '-m', 'base')
    with open('C', 'w', encoding='utf-8') as handle:
        handle.write('c\n')
    _git('add', 'C')
    _git('commit', '-m', 'second')
    main_context.model.update_status()
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    _wait_for_history(qapp, window)
    # The newest commit is the top row and is selected automatically.
    _wait_for_commit_files(qapp, window, {'C'})
    tree = window.historywidget.treewidget

    # Row 1 is the older commit; itemSelectionChanged is a QueuedConnection
    # (dag.py:1373), so the wait helper below pumps the event loop first.
    tree.setCurrentItem(tree.topLevelItem(1))

    assert _wait_for_commit_files(qapp, window, {'A', 'B'}) == {'A', 'B'}


def test_main_history_file_panel_lives_inside_the_history_dock(
    qapp, main_context, managed_qobject
):
    """The panel is part of the history widget, not a dock of its own."""
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    history = window.historywidget

    assert window.historydock.widget() is history
    assert history.files_splitter.indexOf(history.filewidget) == 1
    assert history.findChildren(QtWidgets.QDockWidget) == []
    assert window.widget_version == 2


def test_main_history_hides_unsupported_file_actions(
    qapp, main_context, managed_qobject
):
    """Context menu entries without a main-window handler are not offered."""
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    filewidget = window.historywidget.filewidget

    assert not filewidget.show_history_action.isVisible()
    assert not filewidget.launch_difftool_action.isVisible()
    assert not filewidget.grab_file_action.isVisible()
    assert not filewidget.grab_file_from_parent_action.isVisible()
    assert not filewidget.select_line_range_action.isVisible()
    assert filewidget.launch_editor_action.isVisible()
```

**RED – Schritt 2: View-Menü im bestehenden Test mitprüfen, keinen Zwillingstest anlegen**

Für den View-Menü-Eintrag existiert bereits ein Test:
`test_view_menu_is_rebuilt_without_duplicates_and_finds_dynamic_toolbars`
(`test/widgets_main_history_test.py:1222-1248`). Er baut das Menü mit `window.build_view_menu(window.view_menu)` und prüft, dass `display_inline_graph_action` **genau einmal** darin vorkommt. Genau dieser Test wird erweitert – ein zweiter, fast identischer Test wäre Duplikation:

1. Nach `inline_graph = window.historywidget.display_inline_graph_action` (Zeile 1227) ergänzen:
   ```python
   commit_files = window.historywidget.display_files_action
   ```
2. In der `for _ in range(2)`-Schleife hinter dem `inline_graph`-Block ergänzen:
   ```python
        assert [action for action in actions if action is commit_files] == [
            commit_files
        ]
   ```

> `window.view_menu` wird sonst erst lazy über `aboutToShow` gefüllt (main.py:895); der direkte `build_view_menu`-Aufruf ist das etablierte Vorgehen der Datei. `MainView.create_view_menu()` wird **nicht** verwendet – es erzeugt jedes Mal ein neues Menüobjekt und wird von keinem Test benutzt.

**RED – Schritt 3: RED nachweisen**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_main_history_test.py \
  -k "commit_file or file_panel or unsupported_file or view_menu_is_rebuilt" \
  -p no:ruff -q
```

Erwartet: **FAIL**. `display_files` ist in `MainView` noch nicht aktiviert, also ist `filewidget.isVisible()` False, die Dateiliste bleibt leer (der Wait-Helper wirft `AssertionError: file list never became {'A', 'B'}`), die Aktionen sind noch sichtbar, und `display_files_action` fehlt im View-Menü.

**GREEN – Schritt 4: Panel aktivieren** (`cola/widgets/main.py:111-123`):

```python
        self.historydock = create_dock(
            'History',
            N_('History'),
            self,
            func=lambda dock: dag.CommitHistoryWidget(
                context,
                ref='--all',
                count=1000,
                display_status=False,
                display_inline_graph=True,
                display_files=True,
                parent=dock,
            ),
        )
```

**GREEN – Schritt 5: Nicht unterstützte Datei-Aktionen ausblenden** – neben der bestehenden Konstante (Zeile 59-63):

```python
_MAIN_HISTORY_UNSUPPORTED_FILE_ACTIONS = (
    'show_history_action',
    'launch_difftool_action',
    'grab_file_action',
    'grab_file_from_parent_action',
    'select_line_range_action',
)
```

und direkt hinter der bestehenden Schleife (Zeile 127-130):

```python
        for action_name in _MAIN_HISTORY_UNSUPPORTED_FILE_ACTIONS:
            file_action = getattr(self.historywidget.filewidget, action_name)
            file_action.setVisible(False)
            file_action.setShortcut(QtGui.QKeySequence())
```

> **Warum `getattr` und nicht ein Dict-Zugriff:** Die bestehende Schleife darüber greift mit `history_tree.menu_actions[action_name]` auf ein **Dict** zu, weil `dag.viewer_actions()` genau ein Dict liefert. `FileWidget` legt seine Aktionen dagegen als **Attribute** an (`filelist.py:29-46`). Der Zugriffsweg unterscheidet sich also, weil die Datenstrukturen sich unterscheiden – nicht aus Willkür. Das Muster „unsupported Actions im Hauptfenster ausblenden und Shortcut leeren" ist identisch.

**GREEN – Schritt 5b: Erwartungswert aus Task 4 nachziehen**

In `test/widgets_main_history_test.py` (Test `test_export_owns_visibility_and_nests_exact_canonical_history_state`, Zeile 991-997) wurde in Task 4 Schritt 5b `'display_files': False` eingetragen. Da `MainView` das Panel jetzt aktiviert, wird der Wert auf `True` gesetzt:

```python
        'display_files': True,
```

Ohne diesen Einzeiler schlägt der Test mit `False != True` fehl.

**GREEN – Schritt 6: View-Menü** (`cola/widgets/main.py:1050`):

```python
        menu.addAction(self.historywidget.display_inline_graph_action)
        menu.addAction(self.historywidget.display_files_action)
```

> Im DAG-Fenster wird die Action **bewusst nicht** ins Menü aufgenommen (`dag.py:2124-2134` bleibt unverändert): dort erfüllt das vorhandene `file_dock` diese Aufgabe, ein zweiter Dateibaum wäre eine Doppelung.

**Schritt 7 – Verifikation & Commit:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_main_history_test.py -p no:ruff -q
```

```bash
git add cola/widgets/main.py test/widgets_main_history_test.py
git commit -m "feat: show commit files next to the main window history"
```

---

### Task 6 – Vollständige Verifikation

**Schritt 1: Fokussierte Suite, beide Bindings**

```bash
QT_QPA_PLATFORM=offscreen QT_API=pyqt6 python3 -B -m pytest \
  test/widgets_history_filelist_test.py \
  test/widgets_dag_history_test.py \
  test/widgets_main_history_test.py \
  test/dag_test.py test/graph_test.py test/main_test.py \
  -p no:ruff -q
```

```bash
QT_QPA_PLATFORM=offscreen QT_API=pyqt5 python3 -B -m pytest \
  test/widgets_history_filelist_test.py \
  test/widgets_dag_history_test.py \
  test/widgets_main_history_test.py \
  -p no:ruff -q
```

**Schritt 2: Gesamtsuite wie in CI**

```bash
garden test -vv -- -p no:ruff
```

**Schritt 3: Lint, Typen, Format**

```bash
python3 -m ruff check \
  cola/icons.py cola/widgets/filelist.py cola/widgets/dag.py cola/widgets/main.py \
  test/widgets_history_filelist_test.py \
  test/widgets_dag_history_test.py \
  test/widgets_main_history_test.py
```

```bash
garden check/mypy -vv
```

```bash
garden check/fmt -vv
```

**Schritt 4: Scope-Prüfung**

```bash
git diff --check && git status --short
```

Erwartet werden ausschließlich:

```
 M cola/icons.py
 M cola/widgets/dag.py
 M cola/widgets/filelist.py
 M cola/widgets/main.py
 M test/widgets_dag_history_test.py
 M test/widgets_main_history_test.py
 A test/widgets_history_filelist_test.py
```

**Schritt 5: Push**

```bash
git push --set-upstream origin ag-tree-ui-cc
```

---

## 4. Geänderte Dateien

| Datei | Änderung | Grund |
|---|---|---|
| `cola/icons.py` | `DIFF_STATUS_ICONS` + `diff_status()` neben `status()` | Icon-Policy gehört in das Icon-Modul |
| `cola/widgets/filelist.py` | `parse_status_and_numstat()`, `raw=True` in den vier `git`-Aufrufen, `list_files(files_log, status_by_path=None)`, `FileTreeWidgetItem.set_status()` + Tooltip | Status-Symbole ohne zusätzlichen Prozess |
| `cola/widgets/dag.py` | `CommitHistoryWidget`: Parameter `display_files` (als letzter), `filewidget`, `files_splitter`, `display_files_action`, Debounce-Timer, neue Methoden `display_files`/`_schedule_files`/`_load_pending_files`/`refresh_files`, je ein Einzeiler in `clear()`, `stop_and_wait()` und `showEvent()`, State-Schlüssel `display_files`/`files_sizes` in `export_state`/`is_valid_state`/`apply_state` | Panel lebt in der History-Komponente |
| `cola/widgets/main.py` | `display_files=True`, `_MAIN_HISTORY_UNSUPPORTED_FILE_ACTIONS`, View-Menü-Eintrag | Aktivierung im Hauptfenster |
| `test/widgets_history_filelist_test.py` | **neu**: Charakterisierung, Parser, Icon-Mapping | TDD-Fundament |
| `test/widgets_dag_history_test.py` | Strukturtest (`filewidget` von Verbots- in Pflichtliste), Panel-Tests, zwei State-Literale | Architekturentscheidung + neue Schlüssel |
| `test/widgets_main_history_test.py` | `HISTORY_KEYS`, Exakt-Dict, MainView-Integrationstests | Neue Schlüssel + Feature |

**Nicht angefasst:** `widget_version`, `windowstate`-Blobs, `build_view_menu`s `dockwidgets`-Liste, `setup_dockwidget_view_menu`, `MainView.export_state`/`apply_state`, `GitDAG`.

---

## 5. Risiken und bewusste Nicht-Ziele

### Risiken

- **Gelockerte Strukturinvariante:** `CommitHistoryWidget` besitzt künftig ein `filewidget`. Der zugehörige Test wird bewusst umgestellt (D1). Die harte Grenze „keine `QDockWidget`-Kinder, keine `graphview`/`diffwidget`" bleibt bestehen und wird weiterhin getestet.
- **Zwei `FileWidget`-Instanzen im DAG-Fenster:** `window.filewidget` (Dock, sichtbar) und `window.historywidget.filewidget` (Panel, unsichtbar). Der Sichtbarkeits-Guard stellt sicher, dass nur eines lädt. Die bestehende Zusicherung `len(show_calls) == 1` ist genau dafür das Gate. Shortcut-Kollisionen entstehen nicht, weil `qtutils._add_action` `Qt.WidgetWithChildrenShortcut` setzt (`qtutils.py:796-798`).
- **Synchrones `git` im GUI-Thread:** `FileWidget.commits_selected` bleibt synchron (Vertrag aus D3). Bei sehr großen Commits kann die GUI kurz stocken. Der Debounce reduziert das auf einen Aufruf je stabilisierter Selektion; die Asynchronisierung wäre eine eigene Änderung an `FileWidget` inklusive Anpassung der DAG-Tests und ist hier bewusst nicht enthalten. Der Weg dorthin ist vorgezeichnet: `qtutils.Task` + `context.runtask.start(task, result=…)` + Supersede-Token, exakt wie `CommitDiffWidget.start_diff_task` (`diff.py:2062-2071`).
- **Merge-Commits ohne Status:** `git show --raw` liefert für Merges nichts (verifiziert). Die Dateien werden weiterhin gelistet, erhalten aber den Dateityp-Fallback statt A/M/D. Kein Fehlerfall, aber sichtbarer Unterschied.
- **Dritter Host ohne Testabdeckung:** `cola/sequenceeditor.py:173` nutzt `FileWidget.commits_selected` ebenfalls, hat aber keine automatisierten Tests (`grep -rln sequenceeditor test/` → leer). Die Änderung an `FileWidget` wirkt dort ungetestet. Deshalb der verpflichtende manuelle Rauchtest in Task 2 Schritt 6b.
- **Neue `N_()`-Strings:** `Display Commit Files`, `Added`, `Modified`, `Deleted`, `Renamed`, `Copied`, `Type changed` sind zunächst unübersetzt. Es gibt kein CI-Gate darauf; die Katalogpflege läuft separat über `garden`.
- **`pytest.ini` erzwingt `--doctest-modules`:** neue Docstrings dürfen keine `>>>`-Beispiele enthalten.
- **Reihenfolge von Task 4 und Task 5:** Der Exakt-Dict-Test in `test/widgets_main_history_test.py:991-997` prüft den von `MainView` exportierten History-State. `display_files` steht dort nach Task 4 auf `False` und nach Task 5 auf `True`. Wird das übersehen, ist die Suite zwischen den Tasks rot. Die Anweisung dazu steht in Task 4 Schritt 5b.

### Bewusste Nicht-Ziele

- **Kein Diff-Inhalt.** `files_selected` bleibt im Hauptfenster unverdrahtet. Der Anschlusspunkt für später ist `historywidget.filewidget.files_selected` → `MainView.diffviewer`; das ist ein eigenes Feature mit eigener Modus-/`DiffLoading`-Semantik.
- **Keine Konsolidierung des DAG-`file_dock`** auf das neue Panel. Möglich, aber eine separate Aufräumarbeit.
- **Keine Obergrenze für die Anzahl gelisteter Dateien.** Der Speicherbedarf ist durch die Dateizahl **eines** Commits begrenzt und wird beim Ausblenden/Deselektieren wieder freigegeben – dasselbe Verhalten wie beim bestehenden DAG-`file_dock`.

---

## 6. Reviewer-Hinweise

1. **Spec-Compliance:** Erscheint die Dateiliste als Panel rechts neben der Commit-Tabelle **innerhalb** des History-Docks – ohne neuen Dock, ohne Tab, ohne Wrapper-Widget? Ist sie ohne die History-Komponente nicht instanziierbar?
2. **Reuse statt Neubau:** Wurde `filelist.FileWidget` unverändert in seiner Rolle belassen (nur um Status-Icons erweitert)? Folgen Splitter, Toggle-Action, Debounce und State-Kanal jeweils einem im Repo belegten Vorbild (`sequenceeditor`, `display_inline_graph`, `CommitDiffWidget`, `CommitHistoryWidget.export_state`)?
3. **Laufzeit:** Löst schnelles Durchsteppen der Commit-Tabelle genau **einen** `git`-Aufruf aus? Löst ein unsichtbares Panel **keinen** aus? Bleibt `len(show_calls) == 1` im DAG-Test unverändert?
4. **State:** Funktioniert der Restart-Roundtrip in beiden Hosts, und behalten Alt-States ohne die neuen Schlüssel den jeweiligen Host-Default?
5. **Kein Kollateralschaden:** `widget_version` unverändert 2, `windowstate`-Blobs unverändert, GitDAG-Verhalten unverändert.
