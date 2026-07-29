---
status: completed
completed_at: 2026-07-29
plan_commit: 84c4029441bb7ff9c38a59dfef684097625392b2
implementation_branch: ag-tree-ui-01
implementation_head: c98b4aefa7e70e39e0eff12f419c5eeb67d5031d
ci_run: https://github.com/hermes-agent-ak/git-fanta/actions/runs/30469948165
manual_verification: passed
---

# Git-Fanta: Sichtbarer Commit-Graph – Implementierungsplan (ABGESCHLOSSEN)

> **Historischer Ausführungsvertrag (erfüllt):** Die Umsetzung erfolgte taskweise mit strikten RED-GREEN-REFACTOR-Zyklen und grünem Gate nach jedem Task.

**Goal:** Den vorhandenen Commit-Graphen direkt im Hauptfenster anzeigen und zurückhaltend GitKraken-inspiriert aufwerten, ohne die bestehende Qt-Architektur oder das separate DAG-Fenster zu beschädigen.

**Architecture:** Vor der UI-Integration werden der prozessglobale `CommitFactory`-State, der Worker-Lifecycle und die fehlerhafte Graphberechnung über Reader-Chunks testgetrieben korrigiert. Danach wird die bestehende Inline-History als `CommitHistoryWidget` extrahiert und von `GitDAG` sowie `MainView` gemeinsam verwendet. `build_graph()` bleibt die einzige Graph-Engine.

**Tech Stack:** Python 3.9+, `qtpy` mit PyQt5/PyQt6, vorhandene `QDockWidget`-Architektur, `pytest`, Qt-Offscreen-Tests, `garden`, `mypy`.

---

## 0. Abschluss- und As-built-Nachweis

> [!IMPORTANT]
> Dieser Plan ist vollständig umgesetzt. Er bleibt an seinem stabilen Pfad als
> Design-, Entscheidungs- und Verifikationsdokument erhalten. Der
> Implementierungsbranch `ag-tree-ui-01` endete funktional in `c98b4aef`; der
> erfolgreiche CI-Lauf ist oben im maschinenlesbaren Statusblock verlinkt.

### Geliefertes Ergebnis

- Das Hauptfenster besitzt ein direkt sichtbares, standardmäßig aktiviertes
  History-Dock mit Inline-Commitgraph, `ref='--all'`, maximal 1.000 Commits und
  ohne WORKTREE-/STAGE-Pseudo-Commits.
- `MainView` und das separate `GitDAG` verwenden dasselbe
  `CommitHistoryWidget`, denselben `RepoReader`-Pfad und ausschließlich
  `cola.models.graph.build_graph()` als Graph-Engine.
- Initialer Load und Repository-Updates laufen serialisiert im Worker; Qt-Items,
  Selection und große `GraphView`-Scenes bleiben im GUI-Thread.
- Fehler behalten die letzte erfolgreiche Historie und zeigen Returncode plus
  exakten Fehlertext nichtmodal an; ein erfolgreicher leerer Verlauf leert den
  sichtbaren Zustand atomar.
- Der Inline-Graph ist palettebasiert, cachefrei, Light-/Dark-tauglich und unter
  PyQt5/PyQt6 semantisch offscreen getestet. HEAD, Merge, normale Nodes,
  Ref-Chips und Lanes sind unterscheidbar; große Fonts skalieren die Zeilenhöhe.
- Das separate DAG-Fenster, seine große GraphView, Diff-/Files-Docks und seine
  Pseudo-Commit-Option bleiben erhalten.

### Wichtigste technische Findings und Entscheidungen

1. **Reader-Isolation:** Ein prozessglobaler Commit-Cache kollidierte zwischen
   parallelen Reads. Jeder `RepoReader` besitzt deshalb eine eigene
   `CommitFactory`; Reset, stderr und Erfolgszustand sind symmetrisch.
2. **Vollständiger Graph statt Chunk-Graphen:** Kanten über die frühere
   2.048-Commit-Grenze gingen bei chunkweiser Berechnung verloren. Der Worker
   sammelt die vollständige Commitliste und ruft `build_graph()` genau einmal
   auf; sichtbar angewendet wird nur das finale Resultat.
3. **Latest-desired-state:** Immutable `HistoryRequest`/`HistoryResult`, Run-ID,
   ein aktiver Worker und genau ein coalesced Pending-Wunsch verhindern stale
   Applies, Doppel-Refreshes und progressive Teilzustände.
4. **Echte Close-Barriere:** `stop_and_wait()` wartet ohne Timeout auf den
   synchronen Git-Read. Es verspricht keinen Hard-Kill, verhindert aber Worker
   nach dem Schließen und verwirft Pending-Arbeit sicher.
5. **Klare Ownership-Grenze:** `CommitHistoryWidget` besitzt Controls, Tree,
   Cache, Worker, Selection und Child-State. `MainView`/`GitDAG` besitzen
   Fenster-, Dock- und GraphView-State. `MainView.widget_version` bleibt `2`.
6. **State-Provenance:** Explizite CLI-Optionen gewinnen anhand ihrer Präsenz,
   auch bei defaultgleichen Werten. Alter flacher GitDAG-State und MainView-v2-
   Layouts werden atomar migriert; malformed State mutiert nichts.
7. **Palette und Accessibility:** Selection folgt Qt-Palettenrollen; Chiptext
   wird pro Hintergrund kontrastiert. Adversariale weiße, schwarze,
   achromatische, transparente und ungültige Rollen besitzen opake Fallbacks.
   Lane-Farben sind unabhängig von `EdgeColor.colors`.
8. **Manueller Integrationsfund:** Der erste Desktop-Test zeigte einen
   deaktivierten Main-Inline-Default, eine fehlende View-Action und
   `menu_actions=None` beim Rechtsklick. `c98b4aef` aktivierte den Graph,
   ergänzte `View > Display Inline Graph`, komponierte Main-Tree-Actions und
   migriert alten bugbedingten `history.display_inline_graph=False`-State ohne
   Versionsmarker einmalig. Receiverlose DAG-only-
   Actions bleiben im Main-Kontext verborgen.
9. **Tooling-Baseline:** Das Repository besitzt 102 bestehende pytest-ruff-
   Baselinefehler und einen Konflikt zwischen Gardens
   `--force-single-line-imports` und Ruff-I001. CI führt deshalb die vollständige
   funktionale Suite mit `-p no:ruff` aus und prüft die geänderten History-Tests
   anschließend separat strikt mit Ruff.

### Task- und Commit-Nachweis

| Task | Ergebnis | Commit |
|---|---|---|
| 1 | DAG-/History-Verträge charakterisiert | `62207e1c` |
| 2 | CommitFactory und Reader-State isoliert | `82c02cf5` |
| 3 | Immutable Result-/Worker-Verträge | `8bf44a99` |
| 4 | Vollständiger Graph über Reader-Batches | `8938b86f` |
| 5 | `CommitHistoryWidget` extrahiert | `a670d8be` |
| 6 | CLI-/State-Priorität und Migration | `5dc167fe` |
| 7 | Main-History-Dock und v2-Layout | `9d6c4035` |
| 8 | Initial-Load und Update-Coalescing | `266f9cd4` |
| 9 | Palettebewusstes Inline-Styling | `4b43e4d0` |
| 10 | PyQt5-/PyQt6-Paint-Matrix | `2c6f9b00` |
| 11 | Abschlussgates und Typverträge | `b75328c6` |
| Desktop-Closure | Main-Default, View-Action, Context-Menü, State-Migration | `c98b4aef` |

`53fe60df` war ausschließlich ein leerer CI-Trigger und enthält keine
Produktänderung.

### Finale Verifikation

- GitHub Actions Run
  [`30469948165`](https://github.com/hermes-agent-ak/git-fanta/actions/runs/30469948165):
  **SUCCESS**.
- Linux-Funktionssuite in CI: **512 passed**.
- CI-Matrix: semantische History-Paint-Smokes unter **PyQt5** und **PyQt6**.
- macOS-App-Build, Windows-Installer, Dokumentations-Build und
  Installationsprüfung: **PASS**.
- Mypy: **96 Quelldateien ohne Befund**.
- Lokale finale Gates: PyQt6 fokussiert **254 passed**, PySide6 History/Main
  **202 passed**, PyQt5 Paint-Smokes **8 passed**, Garden fmt/pyupgrade und
  strikter Ruff-Check der geänderten History-Tests: **PASS**.
- Manueller Desktop-Test am 2026-07-29: Inline-Graph sichtbar,
  `View > Display Inline Graph` schaltbar und Context-Menü ohne Traceback:
  **PASS**.

### Bewusst verbleibende Grenzen

- Ein bereits laufender synchroner Git-Unterprozess wird nicht hart beendet;
  Close wartet stattdessen als vollständige Barriere.
- Die 102 repositoryweiten Ruff-Baselinebefunde sind nicht Teil dieses Features
  und bleiben separat zu bereinigen.
- Dieser Abschluss ist kein vollständiger GitKraken-Klon und führt weder ein
  neues UI-Toolkit noch eine zweite Graph-Engine ein.

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
- Git-Lesen und `cola.models.graph.build_graph()` für den Inline-Graph laufen außerhalb des GUI-Threads; Qt-Item- und bestehendes `GraphView`-Scene-Layout bleiben im GUI-Thread.
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

### Atomarer Lade- und Graphvertrag

- Der Worker sammelt die vollständige Commitliste; partielle Läufe verändern keine sichtbaren Items.
- Das bisherige `add`-Batch-Signal wird nicht für sichtbare Zwischenzustände weiterverwendet.
- Der Worker berechnet `GraphResult` genau einmal auf der vollständigen Liste.
- Nur ein erfolgreiches, aktuelles finales `HistoryResult` ersetzt Items, OID-Map, Graph-Rollen, Cache und Auswahl gemeinsam.
- Fehlerhafte, stale oder beim Schließen verworfene Läufe besitzen keinen sichtbaren Staging-State.
- Ein synthetischer Test deckt eine Parent-Kante über Index 2047/2048 ab und beweist, dass vor dem finalen Result kein partieller Tree sichtbar wird.

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

**GREEN-Gate vor Commit:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/dag_test.py test/graph_test.py test/widgets_dag_history_test.py -q
```

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
- `RepoReader.reset()` leert Factory, `_objects`, `_topo_list`, `_top_commit`, `returncode`, `error` und Cache-Marker symmetrisch.
- `RepoReader.get()` bewahrt den dritten Rückgabewert von `core.run_command()` als `self.error`; ein erfolgreicher Lauf und `reset()` löschen alte Fehlerdaten.
- Model-Tests decken erfolgreichen Lauf, Fehlerlauf mit stderr sowie Reset nach Fehler ab.
- Alle verbliebenen Klassenstate-Zugriffe werden entfernt.
- Keine globale Sperre und keine versteckte Fallback-Factory.

**GREEN-Gate vor Commit:**

```bash
python3 -B -m pytest test/dag_test.py test/graph_test.py -q
git add cola/models/dag.py test/dag_test.py
git commit -m "fix: isolate dag commit factories per reader"
```

### Task 3: Resultatvertrag und Worker-Lifecycle serialisieren

**Files:**
- Modify: `cola/models/dag.py:236-313`
- Modify: `cola/widgets/dag.py:1621-1641,1744-1795,1823-1836,1931-1982`
- Modify: `test/dag_test.py`
- Modify: `test/widgets_dag_history_test.py`

**RED – Ergebnissemantik:**

1. erfolgreicher leerer Lauf löscht alte Items, Graph, Cache und Auswahl;
2. fehlgeschlagener Lauf behält die letzte erfolgreiche Ansicht;
3. Fehler beendet Loading und liefert `returncode`/Fehlertext an einen nichtmodalen Status;
4. ein Erfolg entfernt den alten Fehlerstatus;
5. nach einem Fehler wird ein pending Request normal ausgeführt;
6. `HistoryResult.error` übernimmt exakt `RepoReader.error` und erfindet keinen parallelen generischen Fehlertext.

**RED – Lifecycle:**

1. Doppel-Refresh startet höchstens einen Worker;
2. ein zum aktiven oder pending Cache-Key identischer Request wird ignoriert;
3. nur ein tatsächlich anderer letzter pending Request gewinnt;
4. Worker erhält immutable Parameter;
5. stale `run_id` verändert die View nicht;
6. Close während Load und mit pending Request wartet sicher auf den Abschluss;
7. nach `stop_and_wait()` starten keine Runs und keine UI-Updates;
8. Close vor einem geplanten initialen `singleShot` startet keinen Worker.

**GREEN:** Ein Owner verwaltet `active_thread`, `active_run_id`, `pending_request`, `stopping` und Loading-/Error-State. Folgeläufe starten erst nach `finished`; Slots prüfen `run_id`. Identische active/pending Cache-Keys werden dedupliziert. `thread_begin` leert die letzte erfolgreiche Ansicht nicht. Erst ein erfolgreiches Resultat ersetzt sie atomar. Der Worker übernimmt `returncode` und `error` ausschließlich aus `RepoReader`.

`requestInterruption()` wird nur zwischen kooperativen Phasen geprüft. Der Test verwendet einen kontrolliert freigegebenen blockierenden Fake und behauptet nicht, dass das Flag einen laufenden `core.run_command()`-Prozess beendet.

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/dag_test.py test/widgets_dag_history_test.py -q
git add cola/models/dag.py cola/widgets/dag.py test/dag_test.py test/widgets_dag_history_test.py
git commit -m "fix: define and serialize history load results"
```

### Task 4: Graph über Chunk-Grenzen korrigieren

**Files:**
- Modify: `cola/widgets/dag.py:1294-1343,1810-1832,1945-1982`
- Modify: `test/widgets_dag_history_test.py`

**RED:** Eine synthetische History mit mehr als 2.048 Commits und einer Parent-Kante über Index 2047/2048. Prüfen: alle OIDs haben Graph-Zeilen, `GraphRow.edges_to_parent` enthält die Grenzkante, `build_graph()` läuft genau einmal im Worker, vor dem finalen Result ist kein partieller Tree sichtbar und Fehler/stale/close nach intern gelesenen Teilmengen verändern die letzte erfolgreiche Ansicht nicht.

**GREEN:** Der Worker sammelt alle Commits und berechnet den vollständigen Graph einmal. Das bisherige sichtbare `add`-Batch-Verhalten entfällt. Ein aktuelles erfolgreiches `HistoryResult` wird im GUI-Thread atomar in Items, OID-Map, Rollen und vollständige große `GraphView` umgesetzt; Fehler und stale Results werden ohne sichtbare Mutation verworfen.

**GREEN-Gate vor Commit:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/graph_test.py test/widgets_dag_history_test.py -q
```

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

**GREEN-Gate vor Commit:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/dag_test.py test/widgets_dag_history_test.py -q
```

```bash
git add cola/widgets/dag.py test/widgets_dag_history_test.py
git commit -m "refactor: extract reusable commit history widget"
```

### Task 6: `GitDAG` rekomponieren und alten State migrieren

**Files:**
- Modify: `cola/dag.py:22-47`
- Modify: `cola/main.py:38-73,153-173,606-617`
- Modify: `cola/models/dag.py:67-76`
- Modify: `cola/widgets/dag.py:45-63,1391-1935`
- Modify: `test/dag_test.py`
- Create: `test/main_test.py`
- Modify: `test/widgets_dag_history_test.py`

**RED:**

- Selection erreicht Diff/File/Graph.
- Pseudo-Commit-Option bleibt erhalten.
- Close ruft `stop_and_wait()`.
- Eine zweite History-Instanz beschädigt keine Beziehungen.
- `apply_state()` akzeptiert ein Fixture des bisherigen flachen GitDAG-Schemas (`count`, `display_inline_graph`, `display_status`, `log`).
- Neues `state['history']` wird symmetrisch gelesen und geschrieben.
- Altes Schema wird beim nächsten Export ausschließlich als neues kanonisches Schema ausgegeben.
- Explizite CLI-Overrides für `ref` und `count` gewinnen über altes und neues gespeichertes State-Schema.
- Reale Parser-zu-State-Tests decken gespeichertes `count=500` plus explizites `--count 1000` sowie gespeicherten Fremd-Ref plus expliziten aktuellen Branch ab.
- Standalone `cola.dag.parse_args([])` und Subcommand `cola.main.parse_args(['dag'])` liefern jeweils `count is None`, wenn die Option fehlt.
- `cola.dag.parse_args(['--count', '1000'])` und `cola.main.parse_args(['dag', '--count', '1000'])` erhalten die explizite `1000` und markieren sie im nachfolgenden `DAG.set_arguments()` als Override.
- Beide Einstiegspfade prüfen außerdem explizite Ref-Präsenz bis zum State-Prioritätsvertrag.
- MainView ohne CLI-Overrides darf den gespeicherten Child-Ref restaurieren.

**GREEN:**

1. Sowohl `cola.dag.parse_args()` (`git-dag`) als auch `cola.main.add_dag_command()` (`git cola dag`) verwenden für `--count` `default=None`, damit Optionspräsenz in beiden Namespaces erkennbar bleibt.
2. `git_dag()` initialisiert `DAG` weiterhin zentral mit dem Produktdefault `1000`.
3. `DAG.set_arguments()` setzt `overrides['count']`, sobald `args.count is not None`, und `overrides['ref']`, sobald explizite `args.args` vorhanden sind — jeweils unabhängig davon, ob `set_count()`/`set_ref()` den Wert ändert.
4. `GitDAG.apply_state()` löst alten/neuen State anhand dieses korrigierten `DAG.overridden('ref'/'count')`-Vertrags auf und übergibt dem Widget priorisierte Werte; keine zweite Override-Logik im Widget.
5. Log-Dock enthält das Widget; `apply_state()` liest altes flaches und neues Schema, `export_state()` schreibt nur das neue Schema. Übergangs-Aliase nur für nachgewiesene externe Aufrufer.

**GREEN-Gate vor Commit:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/dag_test.py test/main_test.py test/widgets_dag_history_test.py -q
```

```bash
git add cola/dag.py cola/main.py cola/models/dag.py cola/widgets/dag.py test/dag_test.py test/main_test.py test/widgets_dag_history_test.py
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

**GREEN-Gate vor Commit:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_main_history_test.py -q
```

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
2. ein identischer Request zum active oder pending Cache-Key startet keinen zweiten Lauf;
3. mehrere schnelle tatsächlich unterschiedliche Updates werden zum letzten pending Request zusammengeführt;
4. Commit, Checkout, Fetch/Rescan werden nach dem nächsten erfolgreichen Lauf sichtbar;
5. fehlgeschlagener Auto-Refresh behält die letzte Historie und zeigt den nichtmodalen Fehlerstatus;
6. erfolgreicher leerer Auto-Refresh leert die Ansicht.

**GREEN:** Initialen Load erst nach State-Restore/Event-Loop auslösen. `MainView.refresh()` beziehungsweise seine vorhandene `model.updated`-Verbindung ruft ausschließlich `historywidget.load_if_stale()` auf; MainView kennt keine Worker-Details. Deduplizierung und Coalescing bleiben alleiniger Owner im History-Widget. Verborgene Docks werden ebenfalls aktuell gehalten, damit Einblenden keinen veralteten Graph zeigt.

**GREEN-Gate vor Commit:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py test/widgets_main_history_test.py -q
```

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

**GREEN-Gate vor Commit:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py -q
```

```bash
git add cola/widgets/dag.py test/widgets_dag_history_test.py
git commit -m "style: refine palette-aware inline commit graph"
```

### Task 10: Dieselben Offscreen-Smokes unter PyQt5 und PyQt6

**Files:**
- Modify: `test/widgets_dag_history_test.py`
- Modify: `.github/workflows/ci.yml`

**RED:** Mit transparentem `QImage` linear, Fork, Merge, HEAD, Light und Dark rendern. Semantische Regionen und sichtbare Pixel prüfen, keine Golden Images. Derselbe Testknoten muss unter `QT_API=pyqt5` und `QT_API=pyqt6` laufen; ein nur unter dem aktuell installierten Binding ausgeführter Test erfüllt diesen Task nicht.

**GREEN:** Einen kleinen Linux-CI-Matrix-Job für `pyqt5` und `pyqt6` ergänzen. Pro Matrixeintrag `.[testing,<binding>]` in einer isolierten Umgebung installieren und ausschließlich die semantischen History-Paint-Tests mit `QT_QPA_PLATFORM=offscreen` und passendem `QT_API` ausführen. Bestehenden vollständigen PyQt6-Job nicht duplizieren.

**Lokale GREEN-Gates, sofern beide Extras installiert sind:**

```bash
QT_QPA_PLATFORM=offscreen QT_API=pyqt5 python3 -B -m pytest test/widgets_dag_history_test.py -k 'paint or palette' -q
QT_QPA_PLATFORM=offscreen QT_API=pyqt6 python3 -B -m pytest test/widgets_dag_history_test.py -k 'paint or palette' -q
```

Fehlt lokal ein Binding, muss der vorhandene Binding-Lauf grün sein und die CI-Matrix beide Läufe vor Merge bestätigen.

```bash
git add .github/workflows/ci.yml test/widgets_dag_history_test.py cola/widgets/dag.py
git commit -m "test: cover inline history under Qt5 and Qt6"
```

### Task 11: Vollständige Verifikation

**Direkte fokussierte Suite:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/dag_test.py test/main_test.py test/graph_test.py test/widgets_dag_history_test.py test/widgets_main_history_test.py -q
```

**Vollständige Projekt-Gates:**

```bash
garden test -vv
garden check
git diff --check
git status --short
QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/dag_test.py test/main_test.py test/graph_test.py test/widgets_dag_history_test.py test/widgets_main_history_test.py -q
```

`garden test` ist das vollständige Test-Gate; `garden test -- <paths>` ist nicht fokussiert, weil die Garden-Task immer `cola test` anhängt. `garden check` führt zusätzlich Format-Check, `pyupgrade` und `mypy` aus. `check/pyupgrade` kann Dateien ändern; danach den Diff vollständig prüfen, nur erwartete Änderungen behalten und die direkte fokussierte Suite erneut ausführen.

Zusätzlich prüfen:

- Main-History und DAG gleichzeitig;
- zwei interleaved Reader und zweiter Read nach Reset teilen keine Commits;
- stderr bleibt bei Fehler erhalten und wird bei Erfolg/Reset gelöscht;
- Doppel-Refresh, identischer active/pending Request, Parameterwechsel, Error/Empty, pending-after-error und stale Results;
- kein sichtbarer partieller Tree vor finalem Result;
- Close vor initialem Timer sowie Close mit active+pending Request;
- synthetische Parent-Kante über Index 2047/2048 und vollständige GraphView-Übergabe;
- Git-Lesen und `build_graph()` für den Inline-Graph laufen im Worker, nicht im GUI-Thread; bestehendes `GraphView`-Scene-Layout und Qt-Items bleiben GUI-seitig;
- Main-History höchstens 1.000 und ohne Pseudo-Commits;
- `model.updated` aktualisiert automatisch mit Deduplizierung/Coalescing;
- CLI-Ref/Count gewinnen über gespeicherten State in beiden Startpfaden (`git-dag` und `git cola dag`), auch wenn explizite Werte (`--count 1000`, aktueller Branch) den initialen Defaults entsprechen;
- alter GitDAG-State und alter MainView-v2-State bleiben lesbar;
- CI-Matrix führt dieselben Paint-Smokes unter PyQt5 und PyQt6 aus.

Manuell aus dem Root des normalen Desktop-Clones ausführen:

```bash
./bin/git-cola
```

History direkt sichtbar/gefüllt, `--all`, HEAD/Refs lesbar, keine Pseudo-Zeilen, Context/Selection, andere Docks, genau ein View-Eintrag, Persistenz, Light/Dark, automatisches Update und paralleles `View > DAG...` prüfen. Bei absichtlich ungültigem Ref muss die letzte Historie sichtbar bleiben und der nichtmodale Fehlerstatus erscheinen.

---

## 7. Wahrscheinlich geänderte Dateien

| Datei | Zweck |
|---|---|
| `cola/dag.py` | `git-dag`-CLI-Präsenz für defaultgleiche Overrides |
| `cola/main.py` | `git cola dag`-CLI-Präsenz für defaultgleiche Overrides |
| `cola/models/dag.py` | Factory-Isolation, Reader-Reset, stderr- und Override-Vertrag |
| `cola/widgets/dag.py` | Loader, vollständiger Graph, Widget, Style |
| `cola/widgets/main.py` | Dock, initialer Load, State, Close |
| `test/dag_test.py` | Reader-/Factory-Isolation und standalone DAG-Parser |
| `test/main_test.py` | `git cola dag`-Subcommand-Parser und Override-Präsenz |
| `test/widgets_dag_history_test.py` | Lifecycle, Chunk, Widget, Style, Paint |
| `test/widgets_main_history_test.py` | Dock, Load, Menü, Migration, Close |
| `.github/workflows/ci.yml` | fokussierte PyQt5-/PyQt6-Paint-Matrix |

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

## 10. Historisches Review-Gate (erfüllt)

Vor der Implementierung musste `critical-plan-review` die folgenden Punkte
bestätigen; dieses Gate wurde vor dem ersten Implementierungscommit erfüllt:

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
- jedes Task-Commit besitzt ein direktes GREEN-Gate;
- fokussierter direkter pytest-Lauf, vollständiges `garden test` und `garden check` sind getrennt;
- dieselben Paint-Smokes laufen unter PyQt5 und PyQt6;
- stderr-Erhalt/Reset und atomarer finaler Apply sind explizit;
- CLI-Override-Priorität basiert in `git-dag` und `git cola dag` auf Optionspräsenz und deckt defaultgleiche explizite Werte ab;
- nur Git-Lesen und Inline-`build_graph()` werden als Worker-Arbeit bezeichnet; Qt-/GraphView-Anwendung bleibt GUI-seitig;
- `display_status=False`, `--all`, `1000` festgelegt.
