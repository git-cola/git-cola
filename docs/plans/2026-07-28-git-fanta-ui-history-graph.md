# Git-Fanta: Sichtbarer Commit-Graph – überarbeiteter Implementierungsplan

> **For implementing agents:** Execute this plan task-by-task with strict RED-GREEN-REFACTOR cycles and preserve a green tree after every task.

**Goal:** Den vorhandenen Commit-Graphen direkt im Hauptfenster anzeigen und zurückhaltend GitKraken-inspiriert aufwerten, ohne die bestehende Qt-Architektur oder das separate DAG-Fenster zu beschädigen.

**Architecture:** Vor der UI-Integration werden der prozessglobale `CommitFactory`-State, der Worker-Lifecycle und die fehlerhafte Graphberechnung über Reader-Chunks testgetrieben korrigiert. Danach wird die bestehende Inline-History als `CommitHistoryWidget` extrahiert und von `GitDAG` sowie `MainView` gemeinsam verwendet. `build_graph()` bleibt die einzige Graph-Engine.

**Tech Stack:** Python 3.9+, `qtpy` mit PyQt5/PyQt6, vorhandene `QDockWidget`-Architektur, `pytest`, Qt-Offscreen-Tests, `garden`, `mypy`.

---

## 1. Verbindliche Produktentscheidungen

```text
Main-History-Dock:
  Revisionen: --all
  Maximale Commits: 1000
  WORKTREE-/STAGE-Pseudo-Commits: deaktiviert
```

- `--all` macht lokale und Remote-Branches, Forks und Merges sichtbar.
- 1.000 Commits begrenzen Start- und Renderkosten.
- Uncommittete und gestagte Änderungen bleiben im vorhandenen Statusbereich.
- Das separate DAG-Fenster behält seine optionale Pseudo-Commit-Anzeige.
- Relevante `model.updated`-Signale aktualisieren das Main-History-Dock automatisch; schnelle Folgen werden zusammengeführt.
- Ein fehlgeschlagener Refresh lässt die letzte erfolgreiche Historie sichtbar und zeigt einen nichtmodalen Fehlerstatus.
- Ein erfolgreicher leerer Refresh löscht Items, Graph und Auswahl.

## 2. Akzeptanzkriterien

- Beim normalen Start ist genau ein Dock mit `objectName='History'` sichtbar.
- Es enthält tatsächlich geladene Commit-Zeilen mit `GRAPH_ROW_ROLE`.
- Initialer Load: `ref='--all'`, `count=1000`, `display_status=False`.
- `HEAD`, Branches, Remotes, Tags, Forks und Merges sind klar erkennbar.
- Main-History und separates DAG-Fenster können gleichzeitig laden.
- Das Dock ist über `View` genau einmal ein-/ausblendbar.
- Sichtbarkeit, Ref, Count, Inline-Modus und Spalten werden gespeichert.
- Alte MainView-Layouts bleiben erhalten; `widget_version` bleibt `2`.
- Git- und Graphberechnung laufen außerhalb des GUI-Threads.
- Light/Dark sowie Qt5/Qt6 bleiben unterstützt.

## 3. Nichtziele

- kein vollständiges GitKraken-Layout;
- kein globaler Theme-Umbau;
- kein neues Toolkit, WebView oder Dependency;
- keine zweite Graph-Engine;
- kein Drag-and-drop oder PR-/Hosting-Panel;
- keine Pseudo-Commits im neuen Hauptfenster-Dock;
- keine Entfernung von großer `GraphView`, Diff oder Files aus `GitDAG`.

---

## 4. Korrigiertes Ownership-Modell

```text
RepoReader instance
└── CommitFactory instance
    └── Commit objects for one read only

CommitHistoryWidget
├── immutable HistoryRequest per run
├── active run id and one active ReaderThread
├── one coalesced pending request
├── commit list, cache key and selection
├── child state: ref/count/inline/columns
└── stop_and_wait() lifecycle endpoint

MainView / GitDAG
├── window and dock geometry/visibility
├── state["history"] delegation
└── explicit historywidget.stop_and_wait() from closeEvent
```

### Request und Result

```python
@dataclass(frozen=True)
class HistoryRequest:
    run_id: int
    ref: str
    count: int
    display_status: bool


@dataclass(frozen=True)
class HistoryResult:
    run_id: int
    successful: bool
    returncode: int
    error: str | None
    commits: tuple[dag.Commit, ...]
    graph: GraphResult | None
```

Der Worker liest nie mutable UI-Parameter. Resultate werden nur angewendet, wenn ihre `run_id` noch aktuell ist. Ein Fehlerresultat enthält keinen anwendbaren Graphen; `returncode` und `error` liefern die Diagnose für den nichtmodalen Status.

### Ergebnissemantik

```text
loading
  -> bisherige erfolgreiche Ansicht bleibt sichtbar

successful + commits
  -> Items, Graph, Cache und Selection atomar ersetzen

successful + empty
  -> Items, Graph, Cache und Selection leeren

failed
  -> letzte erfolgreiche Ansicht behalten
  -> Loading beenden
  -> nichtmodalen Fehlerstatus mit returncode/error anzeigen
  -> pending Request anschließend normal ausführen
```

Ein neuer erfolgreicher Lauf entfernt den vorherigen Fehlerstatus. Fehler, Empty und Pending-after-error erhalten getrennte RED-Tests.

### Worker-Zustände

```text
IDLE -> RUNNING
RUNNING + refresh -> pending request ersetzen
RUNNING + stale result -> ignorieren
RUNNING + current result -> anwenden; pending? neuer Run : IDLE
RUNNING + close -> STOPPING -> STOPPED
```

Ein normaler Refresh blockiert die GUI nicht. `stop_and_wait()` verhindert neue Runs, setzt das kooperative Interruption-Flag, ignoriert verspätete Signale und wartet beim finalen Schließen vollständig. Es ist eine sichere Abschlussbarriere, kein Versprechen, einen bereits in `core.run_command()` laufenden synchronen `git log`-Prozess sofort abzubrechen.

### Chunk-Regel

- Batches dürfen progressiv Commit-Items erzeugen.
- `CommitTreeWidget.add_commits()` berechnet keinen Teilgraphen.
- Der Worker sammelt alle Commits und berechnet `GraphResult` genau einmal.
- Das finale Result wendet den vollständigen Graphen im GUI-Thread nur noch als Rollen an.
- Ein Test deckt eine Parent-Kante über die 2048er-Grenze ab.

---

## 5. Tests und Gates

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest \
  test/graph_test.py \
  test/dag_test.py \
  test/widgets_dag_history_test.py \
  test/widgets_main_history_test.py \
  -q
```

```bash
garden test -- test/dag_test.py test/graph_test.py test/widgets_dag_history_test.py test/widgets_main_history_test.py
garden check
git diff --check
git status --short
```

`garden check` ist das kanonische Gesamt-Gate. Sein `check/pyupgrade`-Teilschritt kann Dateien ändern; deshalb anschließend Diff und fokussierte Suite erneut prüfen.

Characterization darf zuerst grün sein. Jede Produktionsänderung ab Task 2 beginnt mit einem Test, der wegen des fehlenden oder falschen Verhaltens rot ist.

---

## 6. Detaillierte Tasks

### Task 1: Bestehende Verträge charakterisieren

**Files:**
- Modify: `test/dag_test.py`
- Create: `test/widgets_dag_history_test.py`

Tests für:

- Inline-Delegate an/aus;
- `GRAPH_ROW_ROLE`, `GRAPH_PREV_ROW_ROLE`, `COMMIT_ROLE`;
- Selection-Signale;
- beide vorhandenen State-Schemata: flacher Standalone-`GitDAG`-State und MainView-Version-2-Dock-State;
- GitDAG-State für Count, Inline und Columns;
- Reader-Signale `begin/add/status/end`.

Diese Tests sind als Refactor-Sicherheitsnetz bereits grün.

```bash
git add test/dag_test.py test/widgets_dag_history_test.py
git commit -m "test: characterize dag history behavior"
```

### Task 2: `CommitFactory` pro Reader isolieren

**Files:**
- Modify: `cola/models/dag.py:19-45,93-160,236-313`
- Modify: `test/dag_test.py`

**RED:** Zwei Reader werden wirklich interleaved konsumiert und dürfen keine Commit-Objekte oder Parent-/Child-Beziehungen teilen. Ein zweiter Read nach `reset()` mit geändertem Input darf keine Objekte des ersten Laufs wiederverwenden.

```python
assert reader_a[oid] is not reader_b[oid]
assert reader_a[oid].parents == expected_a
assert reader_b[oid].parents == expected_b
assert second_read_commit is not first_read_commit
```

**GREEN:**

- `root_generation` und `commits` werden Instanzfelder von `CommitFactory`.
- `reset()`/`new()` werden Instanzmethoden.
- Jeder `RepoReader` besitzt eine Factory.
- Jeder `Commit` erhält diese Factory explizit; `parse()` erzeugt Parents darüber.
- Direkte STAGE-/WORKTREE-Konstruktionen in `get_worktree_commits()` verwenden dieselbe Reader-Factory.
- `RepoReader.reset()` leert Factory, `_objects`, `_topo_list`, `_top_commit` und Cache-Marker symmetrisch.
- Alle verbliebenen Klassenstate-Zugriffe werden entfernt.
- Keine globale Sperre und keine versteckte Fallback-Factory.

```bash
python3 -B -m pytest test/dag_test.py test/graph_test.py -q
git add cola/models/dag.py test/dag_test.py
git commit -m "fix: isolate dag commit factories per reader"
```

### Task 3: Resultatvertrag und Worker-Lifecycle serialisieren

**Files:**
- Modify: `cola/widgets/dag.py:1621-1641,1744-1795,1823-1836,1931-1982`
- Modify: `test/widgets_dag_history_test.py`

**RED – Ergebnissemantik:**

1. erfolgreicher leerer Lauf löscht alte Items, Graph, Cache und Auswahl;
2. fehlgeschlagener Lauf behält die letzte erfolgreiche Ansicht;
3. Fehler beendet Loading und liefert `returncode`/Fehlertext an einen nichtmodalen Status;
4. ein Erfolg entfernt den alten Fehlerstatus;
5. nach einem Fehler wird ein pending Request normal ausgeführt.

**RED – Lifecycle:**

1. Doppel-Refresh startet höchstens einen Worker;
2. der letzte pending Request gewinnt;
3. Worker erhält immutable Parameter;
4. stale `run_id` verändert die View nicht;
5. Close während Load und mit pending Request wartet sicher auf den Abschluss;
6. nach `stop_and_wait()` starten keine Runs und keine UI-Updates;
7. Close vor einem geplanten initialen `singleShot` startet keinen Worker.

**GREEN:** Ein Owner verwaltet `active_thread`, `active_run_id`, `pending_request`, `stopping` und Loading-/Error-State. Folgeläufe starten erst nach `finished`; Slots prüfen `run_id`. `thread_begin` leert die letzte erfolgreiche Ansicht nicht. Erst ein erfolgreiches Resultat ersetzt sie atomar.

`requestInterruption()` wird nur zwischen kooperativen Phasen geprüft. Der Test verwendet einen kontrolliert freigegebenen blockierenden Fake und behauptet nicht, dass das Flag einen laufenden `core.run_command()`-Prozess beendet.

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py -q
git add cola/widgets/dag.py test/widgets_dag_history_test.py
git commit -m "fix: define and serialize history load results"
```

### Task 4: Graph über Chunk-Grenzen korrigieren

**Files:**
- Modify: `cola/widgets/dag.py:1294-1343,1810-1832,1945-1982`
- Modify: `test/widgets_dag_history_test.py`

**RED:** Mehr als 2.048 Commits mit einer Parent-Kante über die Batch-Grenze. Prüfen: alle OIDs haben Graph-Zeilen, Kante vorhanden, `build_graph()` genau einmal und nicht im GUI-Thread.

**GREEN:** Items dürfen batchweise entstehen; vollständiger Graph wird einmal im Worker berechnet und final über `HistoryResult` angewendet. Große `GraphView` erhält weiterhin die vollständige Liste.

```bash
git add cola/widgets/dag.py test/widgets_dag_history_test.py
git commit -m "fix: build inline history graph across batches"
```

### Task 5: `CommitHistoryWidget` extrahieren

**Files:**
- Modify: `cola/widgets/dag.py:630-714,1138-1935`
- Modify: `test/widgets_dag_history_test.py`

**RED:**

```python
def test_history_widget_uses_all_refs_without_status(qapp, app_context):
    history = CommitHistoryWidget(
        app_context, ref='--all', count=1000, display_status=False
    )
    request = history.current_request()
    assert (request.ref, request.count, request.display_status) == ('--all', 1000, False)
```

**GREEN:** Widget besitzt Controls, `CommitTreeWidget`, Worker-State, Cache, Commitliste, Selection, Child-State und `stop_and_wait()`. Es besitzt keine große GraphView, Diff/Files oder Dock-Geometrie. Cache-/Selection-/Thread-State wird vollständig aus `GitDAG` verschoben, nicht kopiert.

```bash
git add cola/widgets/dag.py test/widgets_dag_history_test.py
git commit -m "refactor: extract reusable commit history widget"
```

### Task 6: `GitDAG` rekomponieren und alten State migrieren

**Files:**
- Modify: `cola/widgets/dag.py:1391-1935`
- Modify: `test/widgets_dag_history_test.py`

**RED:**

- Selection erreicht Diff/File/Graph.
- Pseudo-Commit-Option bleibt erhalten.
- Close ruft `stop_and_wait()`.
- Eine zweite History-Instanz beschädigt keine Beziehungen.
- `apply_state()` akzeptiert ein Fixture des bisherigen flachen GitDAG-Schemas (`count`, `display_inline_graph`, `display_status`, `log`).
- Neues `state['history']` wird symmetrisch gelesen und geschrieben.
- Altes Schema wird beim nächsten Export ausschließlich als neues kanonisches Schema ausgegeben.

**GREEN:** Log-Dock enthält das Widget. GitDAG besitzt nur zusätzliche Docks, downstream Selection und Window-State. `apply_state()` besitzt einen eng begrenzten Rückwärtslesepfad für das alte flache Schema; `export_state()` schreibt nur das neue Schema. Übergangs-Aliase nur für nachgewiesene externe Aufrufer.

```bash
git add cola/widgets/dag.py test/widgets_dag_history_test.py
git commit -m "refactor: compose dag window and migrate history state"
```

### Task 7: Main-History-Dock und v2-Layoutmigration gemeinsam einführen

**Files:**
- Modify: `cola/widgets/main.py:61-177,876-900,992-1032,1238-1335`
- Create: `test/widgets_main_history_test.py`

**RED – eine vertikale Migrationsscheibe:**

1. mit der alten MainView wird ein Version-2-State ohne History-Dock erzeugt;
2. der neue MainView restauriert daraus Position/Sichtbarkeit vorhandener Docks;
3. genau ein `historydock` mit `objectName='History'` existiert;
4. fehlt `show_history`, ist das neue Dock sichtbar und nicht tab-versteckt;
5. explizites `show_history=False` wird nach Qt-Restauration angewendet und bleibt verborgen;
6. `widget_version == 2` bleibt unverändert;
7. `state['history']` persistiert Ref, Count, Inline-Modus und Columns;
8. ungültiger State fällt auf ein sichtbares nutzbares Default-Layout zurück;
9. View-Menü enthält genau einen Toggle.

**GREEN:** `qtutils.create_dock('History', N_('History'), ...)` verwenden und sichtbar im oberen Zentrum einordnen. Window besitzt Qt-Blob, Dock-Geometrie und Sichtbarkeit; Child besitzt internen State.

```python
state['show_history'] = self.historydock.isVisible()
state['history'] = self.historywidget.export_state()
```

Kein Versions-Bump und kein Zwischencommit, der Dock ohne Migration einführt.

```bash
git add cola/widgets/main.py test/widgets_main_history_test.py
git commit -m "feat: add history dock without resetting layouts"
```

### Task 8: Initialen Load und automatische Repository-Updates anbinden

**Files:**
- Modify: `cola/widgets/main.py:901-905,1120-1169,1238-1335`
- Modify: `test/widgets_main_history_test.py`

**RED – End-to-End-Load:**

1. event-loop-ready startet genau einen Request `('--all', 1000, False)`;
2. nach erfolgreichem Result existieren Items mit `GRAPH_ROW_ROLE`;
3. MainView kennt weder `RepoReader` noch `ReaderThread`;
4. Close ruft `stop_and_wait()`;
5. Close vor dem initialen `singleShot` verhindert den Start.

**RED – laufende Updates:**

1. ein relevantes `model.updated` ruft die öffentliche History-Refresh-API auf;
2. mehrere schnelle Updates werden zum letzten pending Request zusammengeführt;
3. Commit, Checkout, Fetch/Rescan werden nach dem nächsten erfolgreichen Lauf sichtbar;
4. fehlgeschlagener Auto-Refresh behält die letzte Historie und zeigt den nichtmodalen Fehlerstatus;
5. erfolgreicher leerer Auto-Refresh leert die Ansicht.

**GREEN:** Initialen Load erst nach State-Restore/Event-Loop auslösen. `MainView.refresh()` beziehungsweise seine vorhandene `model.updated`-Verbindung ruft ausschließlich `historywidget.load_if_stale()` auf; MainView kennt keine Worker-Details. Coalescing bleibt alleiniger Owner im History-Widget. Verborgene Docks werden ebenfalls aktuell gehalten, damit Einblenden keinen veralteten Graph zeigt.

```bash
git add cola/widgets/main.py test/widgets_main_history_test.py
git commit -m "feat: keep main history synchronized"
```

### Task 9: Palettebewusstes Inline-Styling

**Files:**
- Modify: `cola/widgets/dag.py:786-1121,1138-1388`
- Modify: `test/widgets_dag_history_test.py`

**RED:** NORMAL/MERGE/HEAD visuell unterscheidbar; Palette als Quelle; Lane-Kontrast; Selection bleibt Qt-konform; Inline-Farben unabhängig von `EdgeColor.colors`; PaletteChange am echten Tree führt zu korrekter Neuzeichnung.

**GREEN:** kleine reine `inline_graph_style(option.palette)`-Factory pro Paint; kein stale Cache. Falls nötig `CommitTreeWidget.changeEvent()` analog `GraphView`. Eigene Inline-Lane-Palette; keine Mutation globaler EdgeColor-Liste. Zeilenhöhe 24–28 px, leicht luftigere Spuren, HEAD-Akzentring, bestehende Chips/Animation.

```bash
git add cola/widgets/dag.py test/widgets_dag_history_test.py
git commit -m "style: refine palette-aware inline commit graph"
```

### Task 10: Qt5-/Qt6-Paint-Smoke-Tests

**Files:**
- Modify: `test/widgets_dag_history_test.py`

Mit transparentem `QImage` linear, Fork, Merge, HEAD, Light und Dark rendern. Nur semantische Regionen und sichtbare Pixel prüfen, keine Golden Images.

```bash
git add test/widgets_dag_history_test.py cola/widgets/dag.py
git commit -m "test: cover inline history rendering offscreen"
```

### Task 11: Vollständige Verifikation

**Fokussierte Suite:**

```bash
garden test --   test/dag_test.py   test/graph_test.py   test/widgets_dag_history_test.py   test/widgets_main_history_test.py
```

**Vollständige Projekt-Gates:**

```bash
garden check
git diff --check
git status --short
```

`garden check` führt laut `garden.yaml` Tests, Format-Check, `pyupgrade` und `mypy` aus. `check/pyupgrade` kann Dateien ändern; danach den Diff vollständig prüfen, nur erwartete Format-/Upgrade-Änderungen behalten und die fokussierte Suite erneut ausführen. Nicht stattdessen das mutierende `garden fmt` als reinen Check ausgeben.

Zusätzlich prüfen:

- Main-History und DAG gleichzeitig;
- zwei interleaved Reader und zweiter Read nach Reset teilen keine Commits;
- Doppel-Refresh, Parameterwechsel, Error/Empty, pending-after-error und stale Signals;
- Close vor initialem Timer sowie Close mit active+pending Request;
- synthetische Parent-Kante über Index 2047/2048 und vollständige GraphView-Übergabe;
- `build_graph()` läuft im Worker, nicht im GUI-Thread;
- Main-History höchstens 1.000 und ohne Pseudo-Commits;
- `model.updated` aktualisiert automatisch mit Coalescing;
- alter GitDAG-State und alter MainView-v2-State bleiben lesbar.

Manuell als normaler Benutzer:

```bash
cd ~/Projects/git-fanta
./bin/git-cola
```

History direkt sichtbar/gefüllt, `--all`, HEAD/Refs lesbar, keine Pseudo-Zeilen, Context/Selection, andere Docks, genau ein View-Eintrag, Persistenz, Light/Dark, automatisches Update und paralleles `View > DAG...` prüfen. Bei absichtlich ungültigem Ref muss die letzte Historie sichtbar bleiben und der nichtmodale Fehlerstatus erscheinen.

---

## 7. Wahrscheinlich geänderte Dateien

| Datei | Zweck |
|---|---|
| `cola/models/dag.py` | Factory-Isolation |
| `cola/widgets/dag.py` | Loader, vollständiger Graph, Widget, Style |
| `cola/widgets/main.py` | Dock, initialer Load, State, Close |
| `test/dag_test.py` | Reader-/Factory-Isolation |
| `test/widgets_dag_history_test.py` | Lifecycle, Chunk, Widget, Style, Paint |
| `test/widgets_main_history_test.py` | Dock, Load, Menü, Migration, Close |

`cola/models/graph.py` bleibt unverändert, sofern kein echter RED-Test eine Algorithmuslücke belegt.

## 8. SOLID-/DRY-Leitplanken

- **SRP:** History-Widget besitzt History-UI/Load; Fenster besitzen Dock-State.
- **OCP:** vorhandene Komponenten komponieren, nicht ersetzen.
- **LSP:** Child verlässt sich nicht auf Top-Level-Close; `stop_and_wait()` explizit.
- **ISP:** MainView sieht Widget/State/Signale, nicht Reader/Thread.
- **DIP:** konkrete Worker-Details bleiben im Widget.
- **DRY:** Cache, Selection und Worker-State haben je einen Owner.
- **YAGNI:** keine neue externe Service-Schicht und kein inkrementeller Graph-Builder.

## 9. Abbruchkriterien

- Unbekannte externe `Commit`-Konstruktoren: Task 2 stoppen und Call-Sites charakterisieren.
- Vollständiger Worker-Graph verbraucht bei sehr großen standalone Counts zu viel Speicher: messen und separaten Plan erstellen, nicht spontan inkrementellen State bauen.
- MainWindow nur mit privaten Mock-Details testbar: Widget-Grenze vereinfachen.
- Qt5/Qt6-Unterschiede: semantische Tests behalten, keine plattformspezifischen Golden Files.
- Altes Version-2-Layout scheitert: Restore-Vertrag korrigieren, keinen Versions-Bump verwenden.

## 10. Review-Gate

Vor Implementierung muss `critical-plan-review` bestätigen:

- kein BLOCKER;
- Factory-Isolation vor UI-Komposition;
- Run-ID, immutable Request und finaler `stop_and_wait()`;
- Chunk-Test vor Extraktion;
- MainView-Version bleibt `2`;
- Child- und Window-State getrennt;
- initialer Load und `model.updated`-Refresh im Test beobachtbar;
- Error/Empty/Pending-Semantik ist explizit;
- alter GitDAG-State und MainView-v2-State werden migriert;
- Dock und v2-Migration bilden eine gemeinsame TDD-Scheibe;
- `stop_and_wait()` ist als sichere Barriere statt Prozess-Kill beschrieben;
- exakte `garden test -- ...`- und `garden check`-Gates sind angegeben;
- `display_status=False`, `--all`, `1000` festgelegt.
