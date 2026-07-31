# Maus-Aktionen und HEAD-Markierung in der History-Ansicht

**Erstellt:** 2026-07-31
**Branch:** wird vor der Umsetzung manuell gesetzt — dieser Plan legt **keinen** Branch an.
**Betrifft:** die History-Ansicht im Hauptfenster (`CommitHistoryWidget`, `CommitTreeWidget`,
`GraphDelegate`) und damit automatisch auch das eigenständige DAG-Fenster, das dieselben
Komponenten benutzt.

---

## 0. Wie dieser Plan zu lesen ist

Der Plan ist so geschrieben, dass er **ohne Vorwissen und ohne eigene Entscheidungen**
ausgeführt werden kann.

- **Tasks strikt in der Reihenfolge 0 → 8.** Nichts überspringen.
- **Ein Task = ein Commit.** Die Commit-Message steht am Ende jedes Tasks wörtlich da.
  Ausnahme: Task 4 und 5 hängen an derselben Methode und werden **getrennt** committet —
  jeder Task ist für sich grün.
- **Jeder Task hat RED → GREEN → VERIFIKATION.** Steht beim RED-Schritt eine erwartete
  Fehlermeldung, muss die tatsächliche Ausgabe dazu passen. Passt sie nicht: **stoppen und
  melden**, nicht weitermachen.
- **Zeilennummern sind Orientierung, nicht Wahrheit.** Vor jedem Edit steht ein `grep`, der den
  Anker findet. Benutze den `grep`, nicht die Zeilennummer. Die Nummern in §3 und §4 sind Belege
  für den Ist-Zustand zum Zeitpunkt der Planerstellung, keine Sprungziele.
- **Nach jedem Task ist die volle Test-Suite grün.**
- Schlägt ein Befehl fehl und der Plan nennt keinen Ausweg: **stoppen und melden.**

Standard-Testbefehle:

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test
```

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py test/widgets_dag_history_test.py test/widgets_main_history_test.py
```

---

## 1. Was gebaut wird

Drei Dinge, die alle die History-Ansicht betreffen:

**A — Doppelklick auf einen Commit wechselt den Branch.**
Ist der Commit die Spitze genau eines lokalen Branches, wird dieser Branch ausgecheckt.
Ist er es nicht, würde der Checkout HEAD ablösen — davor wird gefragt.

**B — Es ist erkennbar, wo man steht.**
Der HEAD-Knoten im Inline-Graph wird deutlich sichtbar (heute ist sein Ring in **jeder**
gemessenen Palette praktisch unsichtbar, siehe Falle **F5**), und der Chip des aktuellen
Branches wird markiert. Bei abgelöstem HEAD gibt es überhaupt erst einen Chip (heute: keinen,
siehe Falle **F1**).

**C — Linkes Padding** für die Dock-Überschrift „History" und die Zeile mit `--all`.

Festgelegte Entscheidungen:

| Frage | Entscheidung |
|---|---|
| Commit ist Spitze **eines** lokalen Branches | `cmds.CheckoutBranch` — direkt, ohne Rückfrage. Das ist dasselbe, was das Kontextmenü „Checkout Branch" tut. |
| Commit ist Spitze **mehrerer** lokaler Branches | Der vorhandene Dialog `guicmds.checkout_branch(context, default=branches[0])` entscheidet. Kein neuer Dialog. |
| Commit ist Spitze **des aktuellen** Branches | Nichts tun. Genau wie `BranchesTreeWidget.checkout_action` (`cola/widgets/branch.py:545-549`). |
| Commit ist **keine** Branch-Spitze | `Interaction.confirm(...)` mit `default=False`, danach `cmds.Checkout` (abgelöster HEAD). |
| HEAD ist bereits abgelöst **auf diesem Commit** | Nichts tun, keine Rückfrage. |
| HEAD ist abgelöst, Commit ist Spitze von `main` | `main` wird ausgecheckt — der Doppelklick hängt HEAD wieder an. |
| `WORKTREE`/`STAGE`-Pseudo-Commits | Ignoriert. |
| Wo wirkt der Doppelklick? | In `CommitTreeWidget` — also in der History des Hauptfensters **und** in der Commit-Liste des DAG-Fensters. Die `GraphView` des DAG-Fensters bleibt unangetastet, siehe §2. |
| Wie wird der aktuelle Branch markiert? | Stern-Glyphe `chr(0x2605)` vor dem Namen plus 2 px Rahmen um den Chip. Die Stern-Markierung ist das Projektmuster: `cola/widgets/branch.py:395` setzt `icons.star()` auf den aktuellen Branch. |
| Wie wird abgelöster HEAD markiert? | Ein zusätzlicher Chip `HEAD` ganz vorn in der Zeile. `_draw_labels` hat für `tag == 'HEAD'` bereits eine Farbe (`chip_remote`), und die `GraphView` zeichnet diesen Chip schon lange (`cola/widgets/dag.py:3000-3002`). **Die genaue Regel lautet nicht „wenn abgelöst", sondern „wenn auf dieser Zeile kein Chip als aktueller Branch markiert wurde".** Beides fällt in der Anwendung zusammen, weil `apply_result()` den aktuellen Branch vor jedem Aufbau setzt; bei einem `CommitTreeWidget`, dem noch nie ein Branch mitgeteilt wurde, erscheint der HEAD-Chip ebenfalls. |
| Wie wird der HEAD-Knoten prominenter? | **Nicht größer** — der äußere Radius bleibt bei 8 px, weil der Paint-Test sonst bricht (Falle **F4**). Stattdessen: Ring von 2 auf 3 px verbreitert und `head_accent` kontrastoptimiert (Falle **F5**). |

## 2. Nicht-Ziele

- **Kein Checkout per Einfachklick.** Die Auswahl bleibt eine Auswahl.
- **Kein Doppelklick in der `GraphView`** des DAG-Fensters. Die gemeinsame Logik landet in
  `ViewerMixin`, das sich `CommitTreeWidget` und `GraphView` teilen — die `GraphView` bekommt
  sie also geschenkt, wird aber bewusst nicht verdrahtet. Grund: sie hat eigenes Maus-Handling
  mit Panning und Item-Drag (`cola/widgets/dag.py:3758-3787`), das eine eigene Untersuchung
  braucht. Wer es nachrüsten will, braucht eine `mouseDoubleClickEvent`-Überschreibung, die
  `itemAt()` auflöst und `checkout_commit()` ruft.
- **Kein lokaler Branch aus einem Remote-Branch.** Zeigt ein Commit nur `remotes/origin/foo`
  und keinen lokalen Branch, gilt er als „keine Branch-Spitze" und führt in die
  Detached-Rückfrage. Ein „als neuen Branch auschecken" gibt es im Kontextmenü der Branches-
  Ansicht (`checkout_new_branch_action`), nicht hier.
- **Kein neuer Bestätigungsdialog.** `Interaction.confirm` ist der vorhandene Weg; im GUI-Betrieb
  installiert `cola/app.py:269` über `standard.install()` die Qt-Variante.
- **Kein `widget_version`-Bump.** Es ändert sich keine Dock-Topologie.
- **Keine neue Chip-Hintergrundfarbe.** `_distinct_chip_backgrounds()` liefert exakt drei
  (Falle **F8**); der aktuelle Branch wird über Rahmen und Glyphe markiert, nicht über eine
  vierte Farbe.
- **Keine Änderung an `build_graph()`.** Welche Zeile `GraphRowColor.HEAD` bekommt, entscheidet
  weiterhin `cola/models/graph.py:138`.

## 3. Fallen — alle empirisch verifiziert

| # | Falle | Beleg |
|---|---|---|
| **F1** | `_prepare_labels()` wirft `'HEAD'` weg (`cola/widgets/dag.py:759-760`: `if ref == 'HEAD': continue`). Bei abgelöstem HEAD hat die Zeile **gar keinen** Chip. | Gemessen: `_prepare_labels(['HEAD'])` → `[]`; `_prepare_labels(['HEAD', 'heads/main'])` → `[('heads/main', 'main', None)]` |
| **F2** | `commit.tags` **kann angehängten von abgelöstem HEAD nicht unterscheiden.** Beide Zustände liefern auf einer Branch-Spitze `['HEAD', 'heads/main']`. Ohne `model.currentbranch` ist die Unterscheidung unmöglich. | Gemessen über `dag.RepoReader` in einem echten Repo: angehängt auf `main` → `tags=['HEAD','heads/main'] branches=['main']`; abgelöst auf derselben Spitze → **identisch** |
| **F3** | `gitcmds.current_branch()` liefert bei abgelöstem HEAD den **String `'HEAD'`** (`cola/gitcmds.py:241-242` fällt auf die rohe `rev-parse`-Ausgabe zurück). Git verbietet einen Branch namens `HEAD`, deshalb kann `'heads/' + currentbranch` in diesem Fall nie auf einen echten Ref passen — es braucht **keinen** Sonderfall. | `git rev-parse --symbolic-full-name HEAD` bei abgelöstem HEAD → `HEAD`; `git branch HEAD` → `fatal: 'HEAD' is not a valid branch name` |
| **F4** | **Der HEAD-Knoten darf nicht wachsen.** `test_semantic_paint_smoke_renders_graph_regions_without_touching_background` prüft `next_rect.center().y() - (incoming_y + 1) > node_guard` mit `node_guard = DOT_RADIUS + max(2, EDGE_WIDTH) = 8`. Der knappste Abstand beträgt **9**. Ein äußerer Radius > 8 macht diese Assertion falsch. | Gemessen mit `ROW_HEIGHT=26`: outgoing-Abstand 10, **incoming-Abstand 9**, Diagonal-Abstand 10.0. Radius 9 → `incoming ok=False` |
| **F5** | **`head_accent` ist heute praktisch unsichtbar.** `_mix_color(highlight, highlightedText, 0.52)` ergibt gegen Zeile und Knoten einen Kontrast zwischen **1.00 und 1.98**. Bei kollabierten Paletten exakt 1.00, also identisch mit dem Hintergrund. | Gemessen über 8 Paletten (light, dark, black, grey, white, transparent, invalid, achromatic): 1.81 / 1.98 / 1.00 / 1.00 / 1.00 / 1.00 / 1.00 / 1.04 |
| **F6** | `_draw_labels()`, `_labels_width()` und `_label_hit_test()` müssen **dieselbe** Label-Liste benutzen, sonst driften sichtbarer Chip und Trefferfläche auseinander. `test_24pt_visible_chip_and_hit_area_have_identical_boundaries` (`test/widgets_dag_history_test.py:1116`) hält das fest. | `cola/widgets/dag.py:1165` und `:1283` rufen heute beide `_prepare_labels(...)` |
| **F7** | `_TextRecordingPainter.drawRoundedRect` merkt sich `(pen.color(), brush.color())`. `test_draw_labels_makes_every_adversarial_chip_opaque_and_contrasting` fordert für **jedes** Paar Kontrast ≥ 4.5 und `len({brush}) == 3`. Die Markierung des aktuellen Branches darf deshalb **die Stiftfarbe nicht ändern** — nur die Stiftbreite. | `test/widgets_dag_history_test.py:1108-1110`, `:1199-1208` |
| **F8** | `_distinct_chip_backgrounds()` liefert **genau drei** Farben — die Verschiebungen `(0.0, 0.34, 0.67)` sind fest verdrahtet (`cola/widgets/dag.py:923-926`). Eine vierte Chip-Farbe gibt es nicht zu holen. | `cola/widgets/dag.py:910-926` |
| **F9** | **`Interaction.confirm` ist im Test die Konsolen-Variante.** Die Qt-Variante installiert nur `standard.install()` aus `cola/app.py:269`, das im Test nie läuft. Die Basis schreibt auf `stdout` und liest `sys.stdin.readline()` — unter pytest-Capture ist das ein Fehler, kein `False`. **Jeder Test, der eine Rückfrage auslösen kann, muss `Interaction.confirm` monkeypatchen.** Der Plan tut das durchgehend; damit ist die Frage gegenstandslos. | `cola/interaction.py:107-140`, `cola/widgets/standard.py:1336`. *Nicht* empirisch gemessen — in dieser Umgebung fehlt pytest (siehe Task 0). |
| **F10** | `app_context.settings` ist ein **roher `Mock`, und ein `Mock` ist truthy.** Jedes Widget, das `init_state(context.settings, …)` ruft, stirbt beim Konstruieren mit `TypeError` in `QByteArray.fromBase64()`. `MainView` und `GitDAG` gehören dazu. Erst `app_context.settings.get_gui_state.return_value = {}` setzen. | Konvention in `test/widgets_dag_history_test.py:293` ff. und in der `main_context`-Fixture `test/widgets_main_history_test.py:114` |
| **F11** | **`cmds.do()` verschluckt jede Exception** und macht daraus `Interaction.critical` (`cola/cmds.py:3591-3599`). Ein kaputter Checkout wirft im Test also nicht, sondern loggt. Tests müssen den **Git-Zustand** prüfen (`git rev-parse`, `model.currentbranch`), nicht „keine Exception". | `cola/cmds.py:3587-3599` |
| **F18** | **`context.timestamp` muss eine Zahl sein, sonst läuft kein einziges Kommando.** `cola/cmd.py:64` vergleicht `if self.context.timestamp > self.timestamp:` — in der rohen `app_context`-Fixture ist das ein `Mock`, also `TypeError`. Zusammen mit **F11** heißt das: der Checkout passiert einfach nicht, und der Test scheitert mit `assert 'main' == 'topic'` statt mit der echten Ursache. Deshalb hat Task 1 die Fixture `checkout_context`. | Gemessen: ohne `timestamp` scheitern 3 von 9 Szenarien mit `TypeError: '>' not supported between instances of 'Mock' and 'float'`; mit `context.timestamp = 0.0` bestehen alle 9. `main_context` setzt es aus demselben Grund (`test/widgets_main_history_test.py:120`) |
| **F12** | `CommitHistoryWidget` und `CommitTreeWidget` gehören **beiden** Fenstern. `GitDAG` baut sie in `cola/widgets/dag.py:2126`, `MainView` in `cola/widgets/main.py:119-132`. Jede Änderung wirkt in beiden Fenstern. | `git grep -n "CommitHistoryWidget(" -- cola` |
| **F13** | `core.run_command()` **strippt nicht**, `test/helper.py:run_git` gibt also die Ausgabe mit `\n` zurück. Für `git rev-parse`-Vergleiche ist das eine stille Falle. Die History-Tests haben deshalb ein eigenes `_git()` mit `.strip()`. | `cola/core.py:290-307`, `test/widgets_main_history_test.py:137-140` |
| **F14** | **Zeilennummern verschieben sich innerhalb eines Tasks.** Task 4 fügt in `cola/widgets/dag.py` rund 40 Zeilen vor `_draw_labels` ein; jeder danach folgende Anker in derselben Datei liegt anders. **Alle Anker dieses Plans steuern über Inhalt.** | siehe §0 |
| **F15** | **`_prepare_labels()` hat eine eigene, vom Plan sonst nicht berührte Testdatei.** `test/dag_test.py` prüft die Funktion in **10** Tests mit exakten Listenvergleichen, davon zwei mit `'HEAD'` in den Refs (`:421`, `:471`) — beide erwarten, dass `'HEAD'` **weggeworfen** wird. Deshalb darf der HEAD-Chip **nicht** in `_prepare_labels` entstehen, sondern nur eine Ebene höher in `GraphDelegate._row_labels`. Task 5 fasst `_prepare_labels` nur an, um ein String-Literal durch `_HEAD_REF` zu ersetzen — gleicher Wert, gleiches Verhalten. | `test/dag_test.py:395-490`; `test_prepare_labels_no_remotes` erwartet für `['HEAD', 'heads/main', 'tags/v1.0']` genau `[('tags/v1.0', 'v1.0', None), ('heads/main', 'main', None)]` |
| **F16** | **Ein Klassenattribut ist eine Konstante, kein Zustand.** `_TextRecordingPainter` merkt sich neuerdings `rounded_widths` und `ellipses`; `_draw_labels` setzt die Stiftbreite pro Chip. Wer `chip_pen` außerhalb der Schleife anlegt, vererbt die Breite 2 an alle folgenden Chips. Der Plan legt den Stift **innerhalb** der Schleife an. | `test_current_branch_chip_is_starred_and_bordered` prüft `marked > plain` und würde das fangen |
| **F17** | **`icons.branch()` gibt im Test eine Warnung auf stderr aus**: `qt.svg: Cannot open file 'icons:git-branch.svg'`. Das ist der dokumentierte Zustand (`icons.install()` läuft nur aus `cola/app.py`) und **kein Fehler** — der Test bleibt grün. Nicht darauf reagieren. | Gemessen beim Ausführen der Rückfrage mit `icon=icons.branch()` |

## 4. Vorhandenes, das wiederverwendet wird (nicht neu bauen)

| Vorhanden | Wo | Rolle in diesem Plan |
|---|---|---|
| `cmds.CheckoutBranch` | `cola/cmds.py:607` | **Ist** der Branch-Checkout. Ruft `model.update_status()`, wodurch die History automatisch nachlädt. |
| `cmds.Checkout` | `cola/cmds.py:472` | **Ist** der Checkout auf eine OID (abgelöster HEAD). Genau das, was `ViewerMixin.checkout_detached` schon benutzt. |
| `guicmds.checkout_branch(context, default=…)` | `cola/guicmds.py:75` | Der vorhandene Auswahldialog für den mehrdeutigen Fall. `ViewerMixin.checkout_branch` (`cola/widgets/dag.py:198`) ruft ihn bereits genauso. |
| `Interaction.confirm(...)` | `cola/interaction.py:107` | **Ist** die Rückfrage. Signatur `(title, text, informative_text, ok_text, icon=None, default=True, …)`. Vorbild für Text und Tonfall: `CheckoutOurs.confirm` (`cola/cmds.py:547-559`). |
| `BranchesTreeWidget.checkout_action` | `cola/widgets/branch.py:545-549` | **Präzedenzfall** für „Doppelklick = Checkout" und für „auf dem aktuellen Branch passiert nichts". |
| `icons.star()` / `chr(0x2191)` | `cola/widgets/branch.py:395`, `:414` | **Präzedenzfall**: der aktuelle Branch wird mit einem Stern markiert, und Unicode-Glyphen werden als `chr(0x…)` geschrieben. |
| `Label.paint` der `GraphView` | `cola/widgets/dag.py:2999-3002` | **Präzedenzfall**: die große Graph-Ansicht zeichnet einen `HEAD`-Chip. Der Inline-Graph zieht nach. |
| `_best_contrast(candidates, backgrounds)` | `cola/widgets/dag.py:843` | **Ist** die Kontrast-Auswahl. `head_accent` bekommt dieselbe Behandlung, die Chip-Text und Lane-Farben längst haben. |
| `_prepare_labels(refs)` | `cola/widgets/dag.py:744` | Bleibt unverändert (Gruppierung, Kondensierung, Sortierung). Der Plan legt nur eine Delegate-Methode darüber. |
| `prefs.abbrev(context)` | `cola/models/prefs.py:195` | Kürzt die OID für die Rückfrage. `ViewerMixin.with_oid_short` macht es genauso. |
| `_wait_for_head`, `_wait_for_history`, `_main_with_refresh_spy`, `_git`, `_show` | `test/widgets_main_history_test.py:179, :143, :167, :137, :197` | **Fertige** Warte- und Aufbauhelfer für den Ende-zu-Ende-Test. Nicht neu schreiben. |
| `_tree`, `_commit`, `_palette`, `_contrast`, `_paint_graph_row`, `_render_semantic_graph`, `_TextRecordingPainter`, `_adversarial_chip_palettes` | `test/widgets_dag_history_test.py:110, :89, :502, :519, :667, :774, :1066, :1165` | **Fertiges** Paint-Test-Gerüst. Der Plan erweitert `_TextRecordingPainter` um zwei Listen, statt einen zweiten Recorder zu bauen. |
| `qapp` / `managed_qobject` | `test/widgets_dag_history_test.py:50-86` | Vorlage für die neue Testdatei (es gibt kein `conftest.py`). `qapp` wird wörtlich übernommen; `managed_qobject` **ohne** den `QThread`-Zweig, weil die neue Datei nur `CommitTreeWidget` baut und keinen `ReaderThread` startet. Der Plan zeigt die fertige Fassung. |
| `qtutils.create_dock` / `DockTitleBarWidget` | `cola/qtutils.py:1119`, `:1036` | Bekommen einen optionalen, **letzten** Parameter `title_indent=0`. Default 0 heißt: jedes andere Dock bleibt Pixel für Pixel gleich. |
| `defs.margin` | `cola/widgets/defs.py` (`scale(4)`) | **Ist** das „leichte" Padding. Keine neue Konstante. |

---

# TASKS

## Task 0 — Entwicklungsumgebung herstellen

> **Blockierend. Kein Commit.**

> **Achtung, gemessen am 2026-07-31 auf dieser Maschine:** `env3/` existiert **nicht**, `garden`
> ist **nicht** installiert, `pytest` ist **nicht** installiert, und `python3 -m pip` sowie
> `ensurepip` fehlen ebenfalls (`ModuleNotFoundError: No module named 'ensurepip'`). PyQt5 ist
> vorhanden, PyQt6 nicht. **Ohne funktionierenden Testrunner ist dieser Plan nicht ausführbar.**

1. Prüfen:

```bash
ls -d /home/hermes-agent/Projects/git-fanta/env3 2>/dev/null && echo VORHANDEN || echo FEHLT
```

2. Falls `FEHLT` und `garden` vorhanden ist:

```bash
cd /home/hermes-agent/Projects/git-fanta && garden dev/virtualenv && garden dev
```

3. Falls `garden` fehlt:

```bash
cd /home/hermes-agent/Projects/git-fanta && python3 -m venv --system-site-packages env3 && ./env3/bin/python -m ensurepip --upgrade && ./env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

4. Falls auch das scheitert (kein `ensurepip`, kein Netz): **STOPP und melden.** Der Plan darf
   nicht „blind" ausgeführt werden — jeder Task hängt an einer beobachteten RED- und
   GREEN-Ausgabe.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -5
```

**Erwartet:** `NNN passed`, kein `failed`, kein `error`. **Notiere `NNN` als Baseline.**

---

## Task 1 — Die Checkout-Regel

**Ziel:** Eine Methode `ViewerMixin.checkout_commit(commit)`, die aus einem Commit die richtige
Aktion ableitet. Noch **ohne** Verdrahtung an die Maus — der Task testet reine Politik.

### Schritt 1.1 (RED) — Testdatei anlegen

Neue Datei `test/widgets_history_checkout_test.py`:

```python
# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Der Doppelklick in der Commit-Liste und seine Checkout-Regeln."""

import subprocess
import sys

import pytest

from cola import guicmds
from cola.interaction import Interaction
from cola.models import dag
from cola.widgets.dag import CommitTreeWidget
from qtpy import QtCore
from qtpy import QtTest
from qtpy import QtWidgets

from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for offscreen widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-fanta-test']
        )
    yield instance


@pytest.fixture
def managed_qobject(qapp):
    """Delete parentless Qt test objects after the test."""
    objects = []

    def manage(obj):
        objects.append(obj)
        return obj

    yield manage

    QtTest.QTest.qWait(5)
    qapp.processEvents()
    for obj in reversed(objects):
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


def _git(*args):
    """Wie in test/widgets_main_history_test.py: mit strip().

    test/helper.py:run_git benutzt core.run_command(), und das strippt nicht -
    ein Vergleich mit einer OID schluege dann still fehl.
    """
    return subprocess.run(
        ('git', *args), check=True, text=True, capture_output=True
    ).stdout.strip()


def _repo_with_topic(context):
    """Zwei Commits, zwei Branches, HEAD auf main.

    Die app_context-Fixture legt A und B nur staged an - der erste Commit fehlt.
    """
    _git('commit', '-m', 'base')
    base_oid = _git('rev-parse', 'HEAD')
    _git('checkout', '-b', 'topic')
    _git('commit', '--allow-empty', '-m', 'topic')
    topic_oid = _git('rev-parse', 'HEAD')
    _git('checkout', 'main')
    context.model.update_status()
    return base_oid, topic_oid


def _fake_commit(oid, branches=(), tags=()):
    """Ein Commit-Stellvertreter mit genau den Feldern, die die Regel liest.

    Die Factory ist Pflicht: Commit.__init__ liest factory.root_generation
    bedingungslos (cola/models/dag.py:156).
    """
    commit = dag.Commit(None, dag.CommitFactory(), oid=oid)
    commit.summary = 'summary'
    commit.author = 'A U Thor'
    commit.authdate = '2026-07-31'
    commit.branches = list(branches)
    commit.tags = list(tags)
    return commit


@pytest.fixture
def checkout_context(app_context):
    """app_context plus das eine Attribut, das cmds.Command.do() numerisch vergleicht.

    cola/cmd.py:64 macht `if self.context.timestamp > self.timestamp:`. In der
    app_context-Fixture ist context ein roher Mock, context.timestamp also ein
    Mock -> TypeError. cmds.do() verschluckt ihn (Falle F11), der Test scheitert
    dann mit einer voellig anderen Meldung. Genau dafuer setzt auch die
    main_context-Fixture app_context.timestamp = 0.0
    (test/widgets_main_history_test.py:120).
    """
    app_context.timestamp = 0.0
    return app_context


def _tree(context, managed_qobject):
    return managed_qobject(CommitTreeWidget(context, None))


def _never_confirm(monkeypatch):
    """Interaction.confirm ist im Test die Konsolenvariante und liest stdin."""
    calls = []

    def record(*args, **kwargs):
        calls.append((args, kwargs))
        return False

    monkeypatch.setattr(Interaction, 'confirm', staticmethod(record))
    return calls


def _always_confirm(monkeypatch):
    calls = []

    def record(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(Interaction, 'confirm', staticmethod(record))
    return calls


def test_double_click_on_a_branch_tip_checks_out_that_branch(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Die Spitze genau eines lokalen Branches wird ohne Rueckfrage ausgecheckt."""
    _base, topic_oid = _repo_with_topic(checkout_context)
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(topic_oid, branches=['topic']))

    assert _git('rev-parse', '--abbrev-ref', 'HEAD') == 'topic'
    assert checkout_context.model.currentbranch == 'topic'
    assert confirmed == []


def test_double_click_on_the_current_branch_tip_runs_no_git_command(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Wer schon auf dem Branch steht, loest keinen Checkout aus."""
    base_oid, _topic = _repo_with_topic(checkout_context)
    checkouts = []
    monkeypatch.setattr(
        checkout_context.git, 'checkout', lambda *a, **kw: checkouts.append((a, kw))
    )
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(base_oid, branches=['main'], tags=['HEAD']))

    assert checkouts == []
    assert confirmed == []


def test_double_click_on_a_plain_commit_asks_before_detaching(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Ohne Branch-Spitze wird gefragt - und ein Nein laesst HEAD stehen."""
    base_oid, _topic = _repo_with_topic(checkout_context)
    head_before = _git('rev-parse', 'HEAD')
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(base_oid))

    assert len(confirmed) == 1
    args, kwargs = confirmed[0]
    assert base_oid[:7] in args[1]
    assert 'detach' in (args[1] + args[2]).lower()
    assert kwargs['default'] is False
    assert _git('rev-parse', 'HEAD') == head_before


def test_confirmed_detached_checkout_moves_head(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Ein Ja loest HEAD ab und setzt ihn auf den Commit."""
    base_oid, _topic = _repo_with_topic(checkout_context)
    _always_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(base_oid))

    assert _git('rev-parse', 'HEAD') == base_oid
    assert _git('rev-parse', '--symbolic-full-name', 'HEAD') == 'HEAD'


def test_detached_head_on_a_branch_tip_reattaches_to_the_branch(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Aus dem abgeloesten Zustand haengt der Doppelklick HEAD wieder an."""
    _base, topic_oid = _repo_with_topic(checkout_context)
    _git('checkout', '--detach', 'topic')
    checkout_context.model.update_status()
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(
        _fake_commit(topic_oid, branches=['topic'], tags=['HEAD', 'heads/topic'])
    )

    assert _git('rev-parse', '--abbrev-ref', 'HEAD') == 'topic'
    assert confirmed == []


def test_detached_head_on_a_plain_commit_does_not_ask_again(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Wer schon abgeloest auf diesem Commit steht, wird nicht gefragt."""
    base_oid, _topic = _repo_with_topic(checkout_context)
    _git('checkout', '--detach', base_oid)
    checkout_context.model.update_status()
    checkouts = []
    monkeypatch.setattr(
        checkout_context.git, 'checkout', lambda *a, **kw: checkouts.append((a, kw))
    )
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(base_oid, tags=['HEAD']))

    assert confirmed == []
    assert checkouts == []


def test_several_branches_at_one_commit_open_the_checkout_dialog(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Mehrdeutig heisst: der vorhandene Auswahldialog entscheidet."""
    _base, topic_oid = _repo_with_topic(checkout_context)
    _git('branch', 'alpha', 'topic')
    checkout_context.model.update_status()
    chosen = []
    monkeypatch.setattr(
        guicmds,
        'checkout_branch',
        lambda context, default=None: chosen.append(default),
    )
    checkouts = []
    monkeypatch.setattr(
        checkout_context.git, 'checkout', lambda *a, **kw: checkouts.append((a, kw))
    )
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(topic_oid, branches=['alpha', 'topic']))

    assert chosen == ['alpha']
    assert checkouts == []
    assert confirmed == []


@pytest.mark.parametrize('oid', (dag.STAGE, dag.WORKTREE))
def test_pseudo_commits_are_never_checked_out(
    qapp, checkout_context, managed_qobject, monkeypatch, oid
):
    """WORKTREE und STAGE sind keine Commits."""
    _repo_with_topic(checkout_context)
    checkouts = []
    monkeypatch.setattr(
        checkout_context.git, 'checkout', lambda *a, **kw: checkouts.append((a, kw))
    )
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(oid))

    assert checkouts == []
    assert confirmed == []


def test_none_is_ignored(qapp, checkout_context, managed_qobject, monkeypatch):
    """Ein Doppelklick ins Leere darf nicht knallen."""
    _repo_with_topic(checkout_context)
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(None)

    assert confirmed == []
```

> **Warum ein eigener `_fake_commit()` und nicht der `_commit()`-Helfer aus
> `test/widgets_dag_history_test.py`?** Jener baut Elternbeziehungen und Generationen auf, die
> hier niemand liest. Die Regel liest genau `oid`, `branches` und `tags`. **Die `CommitFactory`
> darf trotzdem nicht `None` sein** — `Commit.__init__` greift bedingungslos auf
> `factory.root_generation` zu (`cola/models/dag.py:156`), `None` gäbe ein `AttributeError`.
> Der `context` darf `None` sein: er wird nur in `parse()` benutzt, und `parse()` läuft nur mit
> `log_entry` (`cola/models/dag.py:159-160`).
>
> **Diese Testdatei steht nicht im Ruff-Schritt der CI** (`.github/workflows/ci.yml:50-54` listet
> nur die beiden alten History-Testdateien). Das ist der Bestandszustand — auch
> `test/widgets_commit_file_diff_test.py` aus dem vorigen Arbeitspaket steht dort nicht.
>
> **Warum `monkeypatch.setattr(checkout_context.git, 'checkout', …)`?** Weil `cmds.do()` jede
> Exception verschluckt (Falle **F11**): „kein Checkout gelaufen" muss am Git-Aufruf gemessen
> werden, nicht am Ausbleiben eines Fehlers.

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py 2>&1 | tail -12
```

**Erwartete Fehlermeldung — alle 10 Tests scheitern mit:**

```
AttributeError: 'CommitTreeWidget' object has no attribute 'checkout_commit'
```

### Schritt 1.2 (GREEN) — Import ergänzen

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^from \.\.i18n import N_$" cola/widgets/dag.py
```

Füge **direkt darunter** ein (isort sortiert `..i18n` vor `..interaction` vor `..models`):

```python
from ..interaction import Interaction
```

### Schritt 1.3 (GREEN) — Rückfrage und Regel

**Anker 1 — Hilfsfunktion:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^class ViewerMixin" cola/widgets/dag.py
```

Füge **direkt vor** `class ViewerMixin:` ein:

```python
def _confirm_detached_checkout(context, commit):
    """Warn before a checkout that would leave HEAD detached"""
    oid = commit.oid[: prefs.abbrev(context)]
    return Interaction.confirm(
        N_('Checkout Detached HEAD?'),
        N_('Commit %s is not the tip of a branch.') % oid,
        N_(
            'Checking out this commit detaches HEAD. New commits will not belong '
            'to any branch and can be lost when you switch away.\n'
            'Use "Create Branch" if you want to keep working here.'
        ),
        N_('Checkout Detached HEAD'),
        default=False,
        icon=icons.branch(),
    )


```

**Anker 2 — die Regel:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    def checkout_detached" -A 4 cola/widgets/dag.py
```

Füge **direkt nach** der Methode `checkout_detached` ein (also vor `def save_blob_dialog`):

```python
    def checkout_commit(self, commit):
        """Go to the branch at `commit`, or to the commit itself after a warning

        A commit that is the tip of exactly one local branch is what the user
        means by "take me to that branch", so it is checked out by name. Several
        branches at the same commit are ambiguous and go through the existing
        Checkout Branch dialog. Anything else would detach HEAD, which is a state
        the user has to opt into.
        """
        if commit is None or commit.oid in (dag.STAGE, dag.WORKTREE):
            return
        context = self.context
        branches = list(commit.branches)
        if context.model.currentbranch in branches:
            return
        if len(branches) == 1:
            cmds.do(cmds.CheckoutBranch, context, branches[0])
            return
        if branches:
            guicmds.checkout_branch(context, default=branches[0])
            return
        if 'HEAD' in commit.tags:
            # HEAD is already detached right here.
            return
        if not _confirm_detached_checkout(context, commit):
            return
        cmds.do(cmds.Checkout, context, [commit.oid])
```

**Importe prüfen** — alle bereits vorhanden:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^from \.\. import cmds$\|^from \.\. import guicmds$\|^from \.\. import icons$\|^from \.\.models import dag$\|^from \.\.models import prefs$\|^from \.\.i18n import N_$" cola/widgets/dag.py
```

**Erwartet:** sechs Treffer. Fehlt einer, **stoppen und melden**.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py
```

**Erwartet:** `10 passed`.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 10 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: Checkout-Regel fuer einen Commit der History

checkout_commit() waehlt zwischen Branch-Checkout, Auswahldialog und einem
bestaetigten Checkout mit abgeloestem HEAD. Die Regel sitzt im ViewerMixin,
wo checkout_branch und checkout_detached schon liegen."
```

---

## Task 2 — Der Doppelklick

### Schritt 2.1 (RED) — Tests ergänzen

Ergänze zuerst den Import — `CommitTreeWidgetItem` wird ab jetzt gebraucht. Füge **direkt unter**
`from cola.widgets.dag import CommitTreeWidget` ein:

```python
from cola.widgets.dag import CommitTreeWidgetItem
```

Hänge dann an `test/widgets_history_checkout_test.py` an:

```python
def _double_click_first_item(tree):
    item = tree.topLevelItem(0)
    tree.itemDoubleClicked.emit(item, 0)
    return item


def test_double_click_in_the_tree_checks_out_the_branch(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Der Doppelklick auf die Zeile loest den Checkout aus."""
    _base, topic_oid = _repo_with_topic(checkout_context)
    _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)
    tree.addTopLevelItem(
        CommitTreeWidgetItem(_fake_commit(topic_oid, branches=['topic']))
    )

    _double_click_first_item(tree)
    qapp.processEvents()

    assert _git('rev-parse', '--abbrev-ref', 'HEAD') == 'topic'


def test_double_click_on_a_row_without_a_commit_is_ignored(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Fremde Items ohne .commit duerfen nichts ausloesen."""
    _repo_with_topic(checkout_context)
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)
    tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(['no commit']))

    _double_click_first_item(tree)
    qapp.processEvents()

    assert confirmed == []
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py -k double_click_in_the_tree 2>&1 | tail -8
```

**Erwartete Fehlermeldung:**

```
AssertionError: assert 'main' == 'topic'
```

> Der zweite neue Test (`..._without_a_commit_is_ignored`) ist bereits grün — es gibt ja noch
> gar keine Verbindung. Er ist eine **Absicherung gegen den GREEN-Schritt**, nicht ein RED.

### Schritt 2.2 (GREEN) — Verbindung und Slot

**Anker 1 — Verbindung:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "self.itemSelectionChanged.connect" -A 3 cola/widgets/dag.py
```

Füge **direkt nach** dem `itemSelectionChanged.connect(...)`-Aufruf in `CommitTreeWidget.__init__`
ein (der Aufruf endet mit `)` auf einer eigenen Zeile):

```python

        self.itemDoubleClicked.connect(self._commit_double_clicked)
```

> `itemSelectionChanged` wird bewusst `QueuedConnection` verbunden, weil die Auswahl über zwei
> Widgets synchronisiert wird. Der Doppelklick betrifft nur dieses Widget und läuft direkt.

**Anker 2 — Slot.**

> **Achtung, `cmds.do(cmds.FormatPatch, …)` steht zweimal in der Datei** — einmal in
> `CommitTreeWidget.create_patch`, einmal in `GraphView.create_patch`. Der folgende `grep` trifft
> nur die erste Stelle, weil `GraphView` `sort_by_generation(self.commits)` benutzt:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "all_oids = \[commit.oid for commit in self.commits\]" -A 1 cola/widgets/dag.py
```

**Erwartet:** genau **zwei** ausgegebene Zeilen (`all_oids = …` und die `cmds.do(...)`-Zeile
darunter), aus `CommitTreeWidget`. Sind es mehr, **stoppen und melden**.

Füge **direkt unter** der ausgegebenen `cmds.do(...)`-Zeile ein (also am Ende von `create_patch`,
vor dem Kommentar `# Qt overrides`):

```python

    def _commit_double_clicked(self, item, _column):
        """A double-click means "take me to that branch"."""
        self.checkout_commit(getattr(item, 'commit', None))
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py
```

**Erwartet:** `12 passed`.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 12 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: Doppelklick auf einen Commit wechselt den Branch

Die Verbindung sitzt im CommitTreeWidget und wirkt damit in der History des
Hauptfensters und in der Commit-Liste des DAG-Fensters. Die GraphView bleibt
absichtlich unverdrahtet, sie hat eigenes Maus-Handling."
```

---

## Task 3 — Der HEAD-Knoten wird sichtbar

**Warum getrennt von der Chip-Markierung:** Hier ändert sich nur Farbe und Stiftbreite eines
Knotens. Bricht dabei ein Paint-Test, liegt es an genau dieser Änderung.

### Schritt 3.1 (RED) — Tests ergänzen

Hänge an `test/widgets_dag_history_test.py` an:

```python
@pytest.mark.parametrize(
    'palette',
    [
        _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff'),
        _palette('#202328', '#e8eaed', '#17191d', '#292d33', '#6ea8fe', '#101216'),
        *_adversarial_chip_palettes(),
    ],
)
def test_head_accent_stays_visible_against_row_and_node(palette):
    """Der Ring um den HEAD-Knoten muss sich abheben - vom Hintergrund und vom Knoten.

    Die alte Ableitung _mix_color(highlight, highlightedText, 0.52) lag ueber acht
    Paletten zwischen 1.00 und 1.98, bei kollabierten Paletten also exakt auf der
    Hintergrundfarbe.
    """
    style = inline_graph_style(palette)
    backgrounds = (
        palette.base().color(),
        palette.alternateBase().color(),
        palette.highlight().color(),
        style.head_fill,
    )

    worst = min(_contrast(style.head_accent, _opaque_color(bg)) for bg in backgrounds)

    assert worst >= 2.0


def test_head_node_is_drawn_in_the_accent_color_with_a_wider_ring(
    qapp, app_context, managed_qobject
):
    """Der HEAD-Knoten unterscheidet sich vom normalen Knoten in Farbe und Breite."""
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([commit], _graph_result([commit]))
    style = inline_graph_style(palette)

    normal = _record_graph_row(tree, graph_model.GraphRowColor.NORMAL, palette)
    head = _record_graph_row(tree, graph_model.GraphRowColor.HEAD, palette)

    assert [color for color, _width, _brush, _radius in normal] == [style.outline]
    assert [color for color, _width, _brush, _radius in head] == [
        style.head_accent,
        style.head_accent,
    ]
    ring_width = head[0][1]
    node_width = normal[0][1]
    assert ring_width > node_width
    assert ring_width == GraphDelegate.HEAD_RING_WIDTH
    # Falle F4: der aeussere Rand darf 8 nicht ueberschreiten.
    assert GraphDelegate.HEAD_RING_RADIUS + GraphDelegate.HEAD_RING_WIDTH / 2 <= 8
```

Und den Recorder-Helfer — hänge ihn **direkt nach** `_paint_graph_row` an:

```python
def _record_graph_row(tree, row_color, palette):
    """Zeichnet eine Zeile in den Recorder und gibt die Ellipsen zurueck."""
    item = tree.topLevelItem(0)
    item.data(0, GRAPH_ROW_ROLE).color = row_color
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = QtCore.QRect(0, 0, 240, 26)
    option.palette = QtGui.QPalette(palette)
    option.font = tree.font()
    option.fontMetrics = QtGui.QFontMetrics(option.font)
    painter = _TextRecordingPainter()
    tree.graph_delegate.paint(painter, option, tree.indexFromItem(item, 0))
    return painter.ellipses
```

Und erweitere `_TextRecordingPainter` — **zwei** Ergänzungen, beide additiv:

**Anker A:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "        self.rounded_rects = \[\]" test/widgets_dag_history_test.py
```

Füge **direkt darunter** ein:

```python
        self.rounded_widths = []
        self.ellipses = []
```

**Anker B:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    def drawEllipse(self, \*_args):" -A 1 test/widgets_dag_history_test.py
```

Ersetze

```python
    def drawEllipse(self, *_args):
        pass
```

durch

```python
    def drawEllipse(self, *args):
        radius = args[1] if len(args) > 1 else 0
        self.ellipses.append(
            (self.pen.color(), self.pen.width(), self.brush.color(), radius)
        )
```

> `self.rounded_widths` wird erst in Task 4 gebraucht, gehört aber in dieselbe Zeile Initialisierung.
> **`rounded_styles` bleibt ein 2-Tupel** — Falle **F7**: bestehende Tests entpacken es mit
> `for pen, brush in painter.rounded_styles`.

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k "head_accent or head_node" 2>&1 | tail -20
```

**Erwartete Fehlermeldungen — zwei verschiedene:**

```
AssertionError: assert 1.81... >= 2.0
```

für `test_head_accent_stays_visible_against_row_and_node` (7 Paletten-Varianten), und

```
AttributeError: type object 'GraphDelegate' has no attribute 'HEAD_RING_WIDTH'
```

für `test_head_node_is_drawn_in_the_accent_color_with_a_wider_ring`.

### Schritt 3.2 (GREEN) — `head_accent` kontrastoptimieren

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    return InlineGraphStyle(" -B 4 cola/widgets/dag.py
```

Füge **direkt vor** `    return InlineGraphStyle(` ein:

```python
    head_fill = _mix_color(highlight, base, 0.16)
    # The ring around the HEAD node used to be a fixed mix of highlight and
    # highlightedText. Measured over eight palettes its contrast against the row
    # and against the node it surrounds was between 1.00 and 1.98 - at 1.00 it is
    # literally the background color. Pick the candidate that stays visible.
    head_accent = _best_contrast(
        (
            _mix_color(highlight, highlighted_text, 0.52),
            highlight,
            text,
            highlighted_text,
            neutral_low,
            neutral_high,
        ),
        (base, alternate, highlight, head_fill),
    )
```

Ersetze anschließend im `return InlineGraphStyle(...)`-Aufruf die beiden Zeilen

```python
        head_fill=_mix_color(highlight, base, 0.16),
        head_accent=_mix_color(highlight, highlighted_text, 0.52),
```

durch

```python
        head_fill=head_fill,
        head_accent=head_accent,
```

### Schritt 3.3 (GREEN) — Knoten zeichnen

**Anker 1 — Konstanten:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    ROW_HEIGHT = 26" cola/widgets/dag.py
```

Füge **direkt darunter** ein:

```python
    # Falle F4: der Paint-Test laesst nur 8 px aeusseren Rand zu
    # (6.5 + 3/2 = 8). Der HEAD-Knoten wird deshalb dicker, nicht groesser.
    HEAD_RING_RADIUS = DOT_RADIUS + 1.5
    HEAD_RING_WIDTH = 3
```

**Anker 2 — Paint:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "                if row.color == GraphRowColor.HEAD:" -A 16 cola/widgets/dag.py
```

Ersetze den Block

```python
                if row.color == GraphRowColor.HEAD:
                    accent_pen = QtGui.QPen(style.head_accent)
                    accent_pen.setWidth(2)
                    painter.setPen(accent_pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(
                        QtCore.QPointF(cx, mid_y),
                        self.DOT_RADIUS + 2,
                        self.DOT_RADIUS + 2,
                    )
                outline_pen = QtGui.QPen(style.outline)
```

durch

```python
                if row.color == GraphRowColor.HEAD:
                    accent_pen = QtGui.QPen(style.head_accent)
                    accent_pen.setWidth(self.HEAD_RING_WIDTH)
                    painter.setPen(accent_pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(
                        QtCore.QPointF(cx, mid_y),
                        self.HEAD_RING_RADIUS,
                        self.HEAD_RING_RADIUS,
                    )
                    outline_color = style.head_accent
                else:
                    outline_color = style.outline
                outline_pen = QtGui.QPen(outline_color)
```

> Der Rest des Blocks (`outline_pen.setWidth(2)`, `setBrush(color_map[row.color])`,
> `drawEllipse(..., DOT_RADIUS, DOT_RADIUS)`) bleibt unverändert.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py
```

**Erwartet:** alle passed.

**Die beiden Paint-Tests einzeln prüfen** — sie sind die, die brechen würden:

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k "semantic_paint_smoke or offscreen_nodes or palette_derived"
```

**Erwartet:** alle passed. Gemessen wurde vorab: `fill_region` zeigt weiterhin `head_fill`,
`annulus_region` weiterhin `head_accent`, äußere Ausdehnung 9.22 px (antialiased) — **identisch
zu vorher**, in light, dark und grey.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 20 passed, 0 failed (12 aus Task 1/2, 7 Paletten-Varianten + 1 Knotentest).

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: der HEAD-Knoten im Inline-Graph wird sichtbar

head_accent war ueber acht gemessene Paletten zwischen 1.00 und 1.98 Kontrast -
bei kollabierten Paletten also unsichtbar. Die Farbe wird jetzt wie Chip-Text
und Lane-Farben ueber _best_contrast gewaehlt, und der Ring ist 3 statt 2 px
breit. Der aeussere Radius bleibt bei 8 px, weil der Paint-Test nicht mehr
Spielraum hat."
```

---

## Task 4 — Der aktuelle Branch wird markiert

### Schritt 4.1 (RED) — Tests ergänzen

Hänge an `test/widgets_dag_history_test.py` an:

```python
def _draw_row_labels(tree, commit, palette, point_size=None):
    """Zeichnet die Chips einer Zeile in den Recorder."""
    font = QtGui.QFont(tree.font())
    if point_size is not None:
        font.setPointSize(point_size)
    metrics = QtGui.QFontMetrics(font)
    painter = _TextRecordingPainter()
    tree.graph_delegate._draw_labels(
        painter,
        13,
        commit.tags,
        GraphDelegate.LANE_WIDTH + 8,
        metrics,
        None,
        inline_graph_style(palette),
    )
    return painter


def test_current_branch_chip_is_starred_and_bordered(
    qapp, app_context, managed_qobject
):
    """Der Chip des aktuellen Branches traegt Stern und dickeren Rahmen."""
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['heads/main', 'heads/topic']
    tree = _tree(app_context, managed_qobject)
    tree.set_current_branch('main')

    painter = _draw_row_labels(tree, commit, palette)

    texts = [text for text, _color in painter.text_colors]
    assert texts == [f'{chr(0x2605)} main', 'topic']
    marked, plain = painter.rounded_widths
    assert marked == GraphDelegate.CURRENT_BRANCH_BORDER
    assert marked > plain


def test_chips_stay_plain_without_a_current_branch(
    qapp, app_context, managed_qobject
):
    """Ohne bekannten aktuellen Branch bleibt jeder Chip unmarkiert."""
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['heads/main']
    tree = _tree(app_context, managed_qobject)

    painter = _draw_row_labels(tree, commit, palette)

    assert [text for text, _color in painter.text_colors] == ['main']
    assert len(set(painter.rounded_widths)) == 1


def test_detached_head_marks_no_branch_as_current(
    qapp, app_context, managed_qobject
):
    """gitcmds.current_branch() liefert bei abgeloestem HEAD den String 'HEAD'.

    Git verbietet einen Branch namens HEAD, also passt 'heads/HEAD' auf keinen Ref
    und kein Chip wird markiert - genau richtig.
    """
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['heads/main']
    tree = _tree(app_context, managed_qobject)
    tree.set_current_branch('HEAD')

    painter = _draw_row_labels(tree, commit, palette)

    assert [text for text, _color in painter.text_colors] == ['main']


def test_marked_chip_and_hit_area_have_identical_boundaries(
    qapp, app_context, managed_qobject
):
    """Der Stern verbreitert den Chip - die Trefferflaeche muss mitwachsen."""
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['heads/main']
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([commit], _graph_result([commit]))
    tree.set_current_branch('main')
    item = tree.topLevelItem(0)
    index = tree.indexFromItem(item, 0)
    font = QtGui.QFont(tree.font())
    font.setPointSize(24)
    metrics = QtGui.QFontMetrics(font)
    option = QtWidgets.QStyleOptionViewItem()
    option.font = font
    option.fontMetrics = metrics
    hint = tree.graph_delegate.sizeHint(option, index)
    rect = QtCore.QRectF(0, 0, hint.width(), hint.height())
    painter = _TextRecordingPainter()
    tree.graph_delegate._draw_labels(
        painter,
        rect.center().y(),
        commit.tags,
        GraphDelegate.LANE_WIDTH + 8,
        metrics,
        item,
        inline_graph_style(tree.palette()),
    )
    chip = painter.rounded_rects[0]

    for x in (chip.left() + 1, chip.right() - 1):
        assert (
            tree.graph_delegate._label_hit_test(
                QtCore.QPointF(x, rect.center().y()), rect, metrics, index, item
            )[0]
            == 0
        )
    assert (
        tree.graph_delegate._label_hit_test(
            QtCore.QPointF(chip.right() + 2, rect.center().y()),
            rect,
            metrics,
            index,
            item,
        )[0]
        == -1
    )


def test_applied_history_publishes_the_current_branch(
    qapp, app_context, managed_qobject
):
    """apply_result() reicht model.currentbranch an den Delegate weiter."""
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    app_context.model.currentbranch = 'main'
    history = managed_qobject(
        CommitHistoryWidget(app_context, ref='--all', count=10, display_status=False)
    )
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['HEAD', 'heads/main']

    history.apply_result([commit], _graph_result([commit]))
    painter = _draw_row_labels(history.treewidget, commit, palette)

    assert [text for text, _color in painter.text_colors] == [f'{chr(0x2605)} main']
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k "current_branch or chips_stay_plain or marked_chip or detached_head_marks" 2>&1 | tail -20
```

**Erwartete Fehlermeldungen — alle fünf Tests scheitern, mit zwei verschiedenen Ursachen.**

Vier von ihnen rufen `set_current_branch(...)` und scheitern daran:

```
AttributeError: 'CommitTreeWidget' object has no attribute 'set_current_branch'
```

`test_chips_stay_plain_without_a_current_branch` ruft es nicht. Es scheitert daran, dass
`rounded_widths` zwar seit Task 3 existiert, aber noch von niemandem gefüllt wird
(`len(set([])) == 0`):

```
AssertionError: assert 0 == 1
```

Entscheidend ist: **keiner** dieser fünf Tests ist schon grün. Ist einer grün, **stoppen und
melden**.

### Schritt 4.2 (GREEN) — Delegate lernt den aktuellen Branch

**Anker 1 — Konstanten:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    ANIMATION_DURATION = 50" cola/widgets/dag.py
```

Füge **direkt darunter** ein:

```python
    # The Branches dock marks the current branch with a star icon
    # (cola/widgets/branch.py). The inline graph draws text, so it uses the glyph.
    CURRENT_BRANCH_MARKER = chr(0x2605) + ' '
    CURRENT_BRANCH_BORDER = 2
```

**Anker 2 — Feld:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "        self._expand_progress: float = 0.0" cola/widgets/dag.py
```

Füge **direkt darunter** ein:

```python
        self._current_branch = ''
```

**Anker 3 — Methoden:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    def set_hover(self, item: object | None, label_idx: int) -> None:" cola/widgets/dag.py
```

Füge **direkt vor** `def set_hover(...)` ein:

```python
    def set_current_branch(self, name: str) -> None:
        """Remember which local branch HEAD points at.

        gitcmds.current_branch() returns the literal string 'HEAD' when HEAD is
        detached. Git refuses a branch named HEAD, so 'heads/HEAD' never matches
        a real ref and nothing gets marked in that case, which is correct.
        """
        name = name or ''
        if name == self._current_branch:
            return
        self._current_branch = name
        parent = self.parent()
        if parent is not None:
            parent.viewport().update()

    def _is_current_branch_ref(self, ref: str) -> bool:
        """Is `ref` the local branch HEAD is on?"""
        return bool(self._current_branch) and (
            ref == _HEADS_PREFIX + self._current_branch
        )

    def _row_labels(self, tags: list[str]) -> list[tuple[str, str, str | None]]:
        """_prepare_labels() with the current branch marked."""
        labels = []
        for ref, display_text, condensed_text in _prepare_labels(tags):
            if self._is_current_branch_ref(ref):
                marker = self.CURRENT_BRANCH_MARKER
                display_text = marker + display_text
                if condensed_text is not None:
                    condensed_text = marker + condensed_text
            labels.append((ref, display_text, condensed_text))
        return labels

```

**Anker 4 — `_draw_labels` benutzt die neue Liste:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "for i, (tag, display_text, condensed_text) in enumerate(_prepare_labels(tags)):" cola/widgets/dag.py
```

Ersetze die Zeile durch

```python
        for i, (tag, display_text, condensed_text) in enumerate(self._row_labels(tags)):
```

**Anker 5 — Rahmen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "                painter.setPen(QtGui.QPen(chip_text))" cola/widgets/dag.py
```

Ersetze die Zeile durch

```python
                chip_pen = QtGui.QPen(chip_text)
                if self._is_current_branch_ref(tag):
                    chip_pen.setWidth(self.CURRENT_BRANCH_BORDER)
                painter.setPen(chip_pen)
```

> **Falle F7:** die *Farbe* des Stifts bleibt `chip_text`. Nur die Breite ändert sich, deshalb
> bleiben `rounded_styles` und die Kontrast-Assertions unberührt.

**Anker 6 — `_label_hit_test` benutzt dieselbe Liste:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "        for i, (_, display_text, condensed_text) in enumerate(" -A 2 cola/widgets/dag.py
```

Ersetze

```python
        for i, (_, display_text, condensed_text) in enumerate(
            _prepare_labels(commit.tags)
        ):
```

durch

```python
        for i, (_, display_text, condensed_text) in enumerate(
            self._row_labels(commit.tags)
        ):
```

**Anker 7 — Recorder ergänzen** (Testdatei):

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "        self.rounded_styles.append((self.pen.color(), self.brush.color()))" test/widgets_dag_history_test.py
```

Füge **direkt darunter** ein:

```python
        self.rounded_widths.append(self.pen.width())
```

### Schritt 4.3 (GREEN) — Weiterreichen vom Modell zum Delegate

**Anker 1 — `CommitTreeWidget`:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    def display_inline_graph(self, enabled):" cola/widgets/dag.py
```

Füge **direkt vor** `def display_inline_graph(self, enabled):` ein:

```python
    def set_current_branch(self, name):
        """Tell the graph delegate which local branch HEAD is on"""
        self.graph_delegate.set_current_branch(name)

```

**Anker 2 — `CommitHistoryWidget.apply_result`:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "            self.treewidget.add_commits(commit_list, graph_result)" cola/widgets/dag.py
```

Füge **direkt darüber** ein:

```python
            # Vor add_commits: resizeColumnToContents() fragt sizeHint(), und die
            # Breite des markierten Chips haengt am aktuellen Branch.
            self.treewidget.set_current_branch(self.model.currentbranch)
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py
```

**Erwartet:** alle passed.

**Die Chip-Tests einzeln prüfen** — sie sind die, die brechen würden:

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k "adversarial_chip or contrasting_text or identical_boundaries or label_hit_area"
```

**Erwartet:** alle passed. Diese Tests bauen frische Widgets ohne `set_current_branch(...)`,
`_current_branch` ist also `''` und kein Chip wird markiert.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 25 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: der aktuelle Branch ist im Inline-Graph markiert

Stern-Glyphe und dickerer Rahmen am Chip des Branches, auf dem HEAD steht.
Die Stern-Markierung ist das Muster der Branches-Ansicht. Die Chipfarbe bleibt
unangetastet, weil _distinct_chip_backgrounds() nur drei Farben liefert."
```

---

## Task 5 — Abgelöster HEAD bekommt einen eigenen Chip

**Warum getrennt:** Task 4 markiert einen vorhandenen Chip. Hier kommt ein Chip **dazu**, der die
Label-Liste, die Breitenberechnung und die Trefferfläche verschiebt.

### Schritt 5.1 (RED) — Tests ergänzen

Hänge an `test/widgets_dag_history_test.py` an:

```python
def test_detached_head_row_gets_its_own_chip(qapp, app_context, managed_qobject):
    """Ohne angehaengten Branch braucht die HEAD-Zeile einen eigenen Chip.

    Gemessen: _prepare_labels(['HEAD']) liefert [] - bei abgeloestem HEAD hatte
    die Zeile bisher gar keine Beschriftung.
    """
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['HEAD']
    tree = _tree(app_context, managed_qobject)
    tree.set_current_branch('HEAD')

    painter = _draw_row_labels(tree, commit, palette)

    assert [text for text, _color in painter.text_colors] == ['HEAD']
    assert painter.rounded_widths == [GraphDelegate.CURRENT_BRANCH_BORDER]


def test_detached_head_on_a_branch_tip_shows_head_before_the_branch(
    qapp, app_context, managed_qobject
):
    """Abgeloest auf einer Branch-Spitze: HEAD zuerst, der Branch unmarkiert.

    commit.tags sieht in diesem Fall genauso aus wie im angehaengten Zustand -
    nur model.currentbranch unterscheidet die beiden.
    """
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['HEAD', 'heads/main']
    tree = _tree(app_context, managed_qobject)
    tree.set_current_branch('HEAD')

    painter = _draw_row_labels(tree, commit, palette)

    assert [text for text, _color in painter.text_colors] == ['HEAD', 'main']
    assert painter.rounded_widths == [GraphDelegate.CURRENT_BRANCH_BORDER, 1]


def test_attached_head_has_no_separate_head_chip(qapp, app_context, managed_qobject):
    """Angehaengt zeigt die Zeile nur den markierten Branch, keinen HEAD-Chip."""
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['HEAD', 'heads/main']
    tree = _tree(app_context, managed_qobject)
    tree.set_current_branch('main')

    painter = _draw_row_labels(tree, commit, palette)

    assert [text for text, _color in painter.text_colors] == [f'{chr(0x2605)} main']


def test_head_chip_widens_the_size_hint(qapp, app_context, managed_qobject):
    """Der zusaetzliche Chip muss auch in der Spaltenbreite ankommen.

    Verglichen werden dieselben tags in beiden HEAD-Zustaenden: angehaengt zeigt
    die Zeile einen Chip ('* main'), abgeloest zwei ('HEAD' und 'main').
    """
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['HEAD', 'heads/main']
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([commit], _graph_result([commit]))
    index = tree.indexFromItem(tree.topLevelItem(0), 0)
    option = QtWidgets.QStyleOptionViewItem()
    option.font = tree.font()
    option.fontMetrics = QtGui.QFontMetrics(option.font)

    tree.set_current_branch('main')
    attached = tree.graph_delegate.sizeHint(option, index).width()
    tree.set_current_branch('HEAD')
    detached = tree.graph_delegate.sizeHint(option, index).width()

    assert detached > attached
```

> **Warum nicht `['HEAD']` allein mit `''` gegen `'HEAD'` vergleichen?** Weil das nichts ändert
> und der Test dann nie grün würde — **gemessen: 229 gegen 229.** Die Einfügeregel lautet „wenn
> auf dieser Zeile **kein** Chip als aktueller Branch markiert wurde", und bei `tags=['HEAD']`
> gibt es gar keinen Branch-Chip zum Markieren. Der HEAD-Chip erscheint dort also in **beiden**
> Zuständen. Erst `['HEAD', 'heads/main']` unterscheidet die Fälle (gemessen: 244 angehängt,
> 277 abgelöst).

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k "detached_head_row or head_before_the_branch or separate_head_chip or widens_the_size_hint" 2>&1 | tail -20
```

**Erwartete Fehlermeldungen — drei Tests, drei Ursachen:**

```
AssertionError: assert [] == ['HEAD']
AssertionError: assert ['main'] == ['HEAD', 'main']
AssertionError: assert <breite> > <breite>
```

Die dritte Meldung zeigt **zweimal dieselbe Zahl** (vor Task 5 kennt `_row_labels` den HEAD-Chip
nicht, beide Zustände sind also gleich breit — gemessen 244). Welche Zahl genau, hängt von der
Testfont-Metrik ab und ist egal.

`test_attached_head_has_no_separate_head_chip` ist bereits grün — er ist die **Absicherung**
gegen einen zu gierigen GREEN-Schritt, kein RED.

### Schritt 5.2 (GREEN) — HEAD-Chip einfügen

**Anker 1 — `_row_labels`:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    def _row_labels" -A 12 cola/widgets/dag.py
```

Ersetze die Methode

```python
    def _row_labels(self, tags: list[str]) -> list[tuple[str, str, str | None]]:
        """_prepare_labels() with the current branch marked."""
        labels = []
        for ref, display_text, condensed_text in _prepare_labels(tags):
            if self._is_current_branch_ref(ref):
                marker = self.CURRENT_BRANCH_MARKER
                display_text = marker + display_text
                if condensed_text is not None:
                    condensed_text = marker + condensed_text
            labels.append((ref, display_text, condensed_text))
        return labels
```

durch

```python
    def _row_labels(self, tags: list[str]) -> list[tuple[str, str, str | None]]:
        """_prepare_labels() with the current position marked.

        _prepare_labels() drops 'HEAD' because an attached HEAD is already
        implied by the marked branch chip. A detached HEAD has no branch to
        mark, so it gets its own chip - the same one the standalone GraphView
        has always drawn.
        """
        labels = []
        marked = False
        for ref, display_text, condensed_text in _prepare_labels(tags):
            if self._is_current_branch_ref(ref):
                marked = True
                marker = self.CURRENT_BRANCH_MARKER
                display_text = marker + display_text
                if condensed_text is not None:
                    condensed_text = marker + condensed_text
            labels.append((ref, display_text, condensed_text))
        if _HEAD_REF in tags and not marked:
            labels.insert(0, (_HEAD_REF, _HEAD_REF, None))
        return labels
```

**Anker 2 — Konstante:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^_HEADS_PREFIX = 'heads/'" cola/widgets/dag.py
```

Füge **direkt darunter** ein:

```python
_HEAD_REF = 'HEAD'
```

**Anker 3 — auch der HEAD-Chip bekommt den Rahmen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    def _is_current_branch_ref" -A 5 cola/widgets/dag.py
```

Füge **direkt nach** der Methode `_is_current_branch_ref` ein:

```python
    def _is_current_position_ref(self, ref: str) -> bool:
        """Is this chip the place HEAD currently points at?"""
        return ref == _HEAD_REF or self._is_current_branch_ref(ref)

```

**Anker 4 — Rahmen umstellen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "                if self._is_current_branch_ref(tag):" cola/widgets/dag.py
```

Ersetze die Zeile durch

```python
                if self._is_current_position_ref(tag):
```

> Nur diese eine Stelle. `_row_labels` benutzt weiterhin `_is_current_branch_ref`, denn den Stern
> bekommt der **Branch**, nicht der HEAD-Chip.

**Anker 5 — vorhandene `'HEAD'`-Literale aufräumen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "if ref == 'HEAD':\|if tag == 'HEAD' or tag.startswith" cola/widgets/dag.py
```

Ersetze in `_prepare_labels`

```python
        if ref == 'HEAD':
```

durch

```python
        if ref == _HEAD_REF:
```

und in `_draw_labels`

```python
                if tag == 'HEAD' or tag.startswith(_TAGS_PREFIX):
```

durch

```python
                if tag == _HEAD_REF or tag.startswith(_TAGS_PREFIX):
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py
```

**Erwartet:** alle passed.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 29 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: abgeloester HEAD bekommt im Inline-Graph einen eigenen Chip

_prepare_labels() wirft 'HEAD' weg, weil ein angehaengter HEAD schon durch den
markierten Branch-Chip zu sehen ist. Bei abgeloestem HEAD gab es dadurch gar
keine Beschriftung. Die grosse GraphView zeichnet diesen Chip seit jeher."
```

---

## Task 6 — Linkes Padding für Überschrift und Eingabezeile

### Schritt 6.1 (RED) — Tests ergänzen

Hänge an `test/widgets_main_history_test.py` an:

```python
def test_history_dock_title_is_indented(qapp, main_context, managed_qobject):
    """Die Ueberschrift 'History' klebt nicht mehr an der Kante."""
    view = managed_qobject(MainView(main_context))

    titlebar = view.historydock.titleBarWidget()

    assert titlebar.title_layout.contentsMargins().left() == defs.margin


def test_other_dock_titles_stay_flush(qapp, main_context, managed_qobject):
    """Der neue Parameter aendert per Default nichts an den uebrigen Docks."""
    view = managed_qobject(MainView(main_context))

    for dock in (view.statusdock, view.commitdock, view.diffdock):
        assert dock.titleBarWidget().title_layout.contentsMargins().left() == 0


def test_history_content_is_indented_and_stays_aligned(
    qapp, main_context, managed_qobject
):
    """Eingabezeile und Baum ruecken gemeinsam ein, damit sie buendig bleiben."""
    view = managed_qobject(MainView(main_context))
    history = view.historywidget

    margins = history.layout().contentsMargins()

    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (
        defs.margin,
        0,
        0,
        0,
    )
    _show(qapp, view)
    assert history.revtext.parentWidget().x() == history.files_splitter.x()
```

Ergänze den Import — `test/widgets_main_history_test.py` importiert `defs` **noch nicht**
(gemessen). Füge in der `from cola…`-Gruppe, alphabetisch **nach** `from cola.models import graph
as graph_model` und **vor** `from cola.widgets import standard`, eine Zeile ein:

```python
from cola.widgets import defs
```

Zur Kontrolle vorher:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^from cola" test/widgets_main_history_test.py
```

**Erwartet:** kein Treffer für `defs`. Weicht das ab, **stoppen und melden**.

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_main_history_test.py -k "indented or stay_flush" 2>&1 | tail -12
```

**Erwartete Fehlermeldungen — zwei Tests, zwei Meldungen:**

```
AssertionError: assert 0 == 4
```

für `test_history_dock_title_is_indented`, und

```
AssertionError: assert (0, 0, 0, 0) == (4, 0, 0, 0)
```

für `test_history_content_is_indented_and_stays_aligned`.
`test_other_dock_titles_stay_flush` ist bereits grün — die Absicherung dafür, dass der Default
0 bleibt.

### Schritt 6.2 (GREEN) — `title_indent` durchreichen

**Anker 1 — `DockTitleBarWidget`:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "        self, parent, title: str, stretch: bool = True, hide_title: bool = False" cola/qtutils.py
```

Ersetze die Zeile durch

```python
        self,
        parent,
        title: str,
        stretch: bool = True,
        hide_title: bool = False,
        title_indent: int = 0,
```

**Anker 2 — Einzug setzen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "        self.title_layout = hbox(defs.no_margin, defs.button_spacing, self.label)" cola/qtutils.py
```

Füge **direkt darunter** ein:

```python
        self.title_layout.setContentsMargins(title_indent, 0, 0, 0)
```

**Anker 3 — `create_dock`.**

> **Achtung: Anker 1 hat gerade eine zweite Zeile `hide_title: bool = False,` erzeugt** — die in
> `DockTitleBarWidget.__init__` steht 8 Zeichen eingerückt und enthält die 4-Zeichen-Variante als
> Teilstring. Ein `grep -F "    hide_title"` findet ab jetzt **zwei** Treffer (gemessen an einer
> Kopie: Zeile 1044 und Zeile 1131). Der folgende `grep` ist deshalb auf Zeilenanfang und
> Zeilenende verankert und trifft nur `create_dock`:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^    hide_title: bool = False,$" -A 1 cola/qtutils.py
```

**Erwartet:** genau **ein** Treffer. Sind es zwei, **stoppen und melden** — dann wurde Anker 1
falsch angewendet.

Ersetze in der Signatur von `create_dock`

```python
    hide_title: bool = False,
) -> QtWidgets.QDockWidget:
```

durch

```python
    hide_title: bool = False,
    title_indent: int = 0,
) -> QtWidgets.QDockWidget:
```

**Anker 4 — Weitergabe:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "    titlebar = DockTitleBarWidget(dock, title, stretch=stretch, hide_title=hide_title)" cola/qtutils.py
```

Ersetze die Zeile durch

```python
    titlebar = DockTitleBarWidget(
        dock, title, stretch=stretch, hide_title=hide_title, title_indent=title_indent
    )
```

> **Beide neuen Parameter stehen ganz hinten.** Alle 14 vorhandenen `create_dock`-Aufrufe geben
> ihre optionalen Argumente als Schlüsselwörter an; Default 0 heißt: jedes andere Dock bleibt
> unverändert.

### Schritt 6.3 (GREEN) — History-Dock und History-Inhalt einrücken

**Anker 1 — Import in `cola/widgets/main.py`** (`defs` wird dort bisher **nicht** benutzt, gemessen):

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^from \. import dag$" cola/widgets/main.py
```

Füge **direkt darunter** ein (alphabetisch zwischen `dag` und `diff`):

```python
from . import defs
```

**Anker 2 — Dock:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "        self.historydock = create_dock(" -A 4 cola/widgets/main.py
```

Ersetze

```python
        self.historydock = create_dock(
            'History',
            N_('History'),
            self,
```

durch

```python
        self.historydock = create_dock(
            'History',
            N_('History'),
            self,
            title_indent=defs.margin,
```

**Anker 3 — Inhalt des History-Widgets:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "        layout = qtutils.vbox(" -A 3 cola/widgets/dag.py
```

Füge **direkt nach** dem `layout = qtutils.vbox(...)`-Aufruf (er endet mit `)` auf einer eigenen
Zeile, direkt vor dem Kommentar `# Pin the controls row…`) ein:

```python
        # Eingabezeile, Baum und Dateiliste ruecken gemeinsam von der Dockkante ab,
        # damit sie buendig bleiben.
        layout.setContentsMargins(defs.margin, 0, 0, 0)
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_main_history_test.py test/widgets_dag_history_test.py
```

**Erwartet:** alle passed.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 32 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "style: linkes Padding fuer History-Ueberschrift und Eingabezeile

create_dock bekommt einen optionalen title_indent (Default 0, alle uebrigen
Docks bleiben unveraendert). Der Inhalt des CommitHistoryWidget rueckt als
Ganzes ein, damit Eingabezeile und Baum buendig bleiben."
```

---

## Task 7 — Ende-zu-Ende im Hauptfenster

**Ziel:** Ein Test, der die ganze Kette prüft — Doppelklick, echter Checkout, Modell-Update,
History-Nachladen, HEAD-Markierung an der neuen Stelle. Er ist der einzige Test, der belegt,
dass die Verdrahtung im Hauptfenster tatsächlich ankommt.

### Schritt 7.1 (RED) — Test ergänzen

Hänge an `test/widgets_main_history_test.py` an:

```python
def test_double_click_in_the_main_window_checks_out_and_reloads(
    qapp, main_context, managed_qobject, monkeypatch
):
    """Der Doppelklick wechselt den Branch und die History zieht nach.

    Interaction.confirm wird ersetzt, weil die Konsolenvariante sonst stdin liest;
    dieser Fall darf sie ohnehin nicht erreichen.
    """
    monkeypatch.setattr(Interaction, 'confirm', staticmethod(lambda *a, **kw: False))
    _git('commit', '-m', 'base')
    original_branch = _git('branch', '--show-current')
    _git('checkout', '-b', 'topic')
    _git('commit', '--allow-empty', '-m', 'topic')
    topic_oid = _git('rev-parse', 'HEAD')
    _git('checkout', original_branch)
    main_context.model.update_status()
    window, refresh_calls = _main_with_refresh_spy(
        main_context, managed_qobject, monkeypatch
    )
    _wait_for_history(qapp, window, topic_oid)
    tree = window.historywidget.treewidget
    refresh_baseline = len(refresh_calls)

    tree.itemDoubleClicked.emit(tree.oidmap[topic_oid], 0)
    _wait_for_head(qapp, window, topic_oid, refresh_calls, refresh_baseline)

    assert main_context.model.currentbranch == 'topic'
    assert _git('branch', '--show-current') == 'topic'


def test_double_click_marks_the_new_branch_in_the_graph(
    qapp, main_context, managed_qobject, monkeypatch
):
    """Nach dem Wechsel traegt der neue Branch die Markierung."""
    monkeypatch.setattr(Interaction, 'confirm', staticmethod(lambda *a, **kw: False))
    _git('commit', '-m', 'base')
    original_branch = _git('branch', '--show-current')
    _git('checkout', '-b', 'topic')
    _git('commit', '--allow-empty', '-m', 'topic')
    topic_oid = _git('rev-parse', 'HEAD')
    _git('checkout', original_branch)
    main_context.model.update_status()
    window, refresh_calls = _main_with_refresh_spy(
        main_context, managed_qobject, monkeypatch
    )
    _wait_for_history(qapp, window, topic_oid)
    tree = window.historywidget.treewidget
    refresh_baseline = len(refresh_calls)

    tree.itemDoubleClicked.emit(tree.oidmap[topic_oid], 0)
    _wait_for_head(qapp, window, topic_oid, refresh_calls, refresh_baseline)

    labels = tree.graph_delegate._row_labels(
        window.historywidget.commits[topic_oid].tags
    )
    assert [display for _ref, display, _condensed in labels] == [
        f'{chr(0x2605)} topic'
    ]
```

> **Warum `_wait_for_head` und nicht `qapp.processEvents()`?** Der Checkout läuft synchron, das
> Nachladen der History aber in einem `ReaderThread`. `_wait_for_head`
> (`test/widgets_main_history_test.py:179`) wartet genau darauf, dass die HEAD-Markierung am
> erwarteten Commit angekommen ist — mit 10 s Deckel und einer Assertion am Ende, terminiert also
> in jedem Fall.
>
> Der zweite Test fragt `_row_labels()` mit den **echten** Tags des neu ausgecheckten Commits.
> Das prüft die ganze Kette bis zur Beschriftung: Reload → `apply_result()` →
> `set_current_branch()` → Markierung. Eine Assertion auf `_current_branch` allein wäre nur ein
> Echo der Zuweisung.
>
> Erwartet wird genau **ein** Label: `topic` ist nach dem Checkout der aktuelle Branch, also
> markiert, und deshalb entsteht **kein** zusätzlicher `HEAD`-Chip. Läge dort
> `['HEAD', 'topic']`, wäre `set_current_branch()` nicht angekommen.

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/widgets_main_history_test.py -k double_click 2>&1 | tail -12
```

**Erwartet:** **beide Tests sind bereits grün.** Task 2 hat die Verbindung gelegt, Task 4 die
Weiterreichung. Diese beiden Tests sind **Charakterisierungstests der fertigen Kette** — sie
belegen, dass Task 2 und Task 4 im Hauptfenster tatsächlich zusammenspielen, statt nur in
isolierten Widgets zu funktionieren.

> Sind sie **nicht** grün: **stoppen und melden.** Dann fehlt etwas an der Verdrahtung, und die
> Fehlermeldung sagt, was.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 34 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "test: Doppelklick im Hauptfenster wechselt Branch und laedt die History nach

Die Kette aus Doppelklick, cmds.CheckoutBranch, model.updated, load_if_stale und
apply_result laesst sich nur im Hauptfenster pruefen. Beide Tests sind
Charakterisierungstests des fertigen Zustands."
```

---

## Task 8 — Dokumentation

### Schritt 8.1 — `references/fork-history.md`

Hänge in `.claude/skills/project-brief/references/fork-history.md` **nach** Abschnitt
`## 4. Double-click a commit file to see its diff` und **vor** `## Where the fork's tests live`
an (Anker: `grep -n "^## " .claude/skills/project-brief/references/fork-history.md`):

```markdown
## 5. Mouse actions and HEAD marking in the history

Plan: `docs/plans/2026-07-31-history-mouse-actions.md`.

**Double-clicking a commit switches branch.** `ViewerMixin.checkout_commit()` picks the action:
the tip of exactly one local branch is checked out by name, several branches go through the
existing `guicmds.checkout_branch()` dialog, the current branch's tip does nothing, and anything
else asks before detaching HEAD. `CommitTreeWidget` connects `itemDoubleClicked`, so it works in
the main window *and* in the DAG window's commit list.

**Decisions that later work must not undo:**

- **The `GraphView` is deliberately not wired.** It inherits `checkout_commit()` from
  `ViewerMixin` but has its own pan/drag mouse handling; a double-click there is a no-op by
  design.
- **`head_accent` is contrast-selected, not mixed.** The old
  `_mix_color(highlight, highlightedText, 0.52)` measured between 1.00 and 1.98 contrast over
  eight palettes — at 1.00 it *was* the background. `test_head_accent_stays_visible_against_row_
  and_node` holds the floor at 2.0.
- **The HEAD node got thicker, not bigger.** `HEAD_RING_RADIUS + HEAD_RING_WIDTH / 2 == 8` is a
  hard ceiling: the semantic paint test's tightest sample sits 9 px from the node center.
- **The current branch is marked with `chr(0x2605)` plus a 2 px chip border, never a new chip
  color.** `_distinct_chip_backgrounds()` returns exactly three colors, and
  `_TextRecordingPainter` records the chip *pen color* — changing it would break the adversarial
  contrast test.
- **A detached HEAD gets its own `HEAD` chip**, inserted by `GraphDelegate._row_labels()` only
  when no chip on that row was marked as the current branch. `commit.tags` alone cannot tell the
  two states apart — both read `['HEAD', 'heads/main']` on a branch tip.
- **`create_dock(..., title_indent=...)` defaults to 0**, so only the History dock is indented.
```

Ergänze außerdem in der Testliste am Dateiende:

```markdown
- `test/widgets_history_checkout_test.py` — die Checkout-Regel des Doppelklicks: Branch-Spitze,
  Mehrdeutigkeit, aktueller Branch, abgelöster HEAD, Pseudo-Commits.
```

### Schritt 8.2 — `references/gotchas.md`

Hänge im Abschnitt „## Qt widget behavior" an:

```markdown
**`_prepare_labels()` drops `'HEAD'`,** so a detached HEAD row has no chip at all — measured:
`_prepare_labels(['HEAD']) == []`. `GraphDelegate._row_labels()` puts it back when no branch chip
on the row was marked current.

**`commit.tags` cannot distinguish an attached from a detached HEAD.** Both read
`['HEAD', 'heads/main']` on a branch tip — measured through `dag.RepoReader`. Only
`model.currentbranch` knows, and it is the literal string `'HEAD'` when detached
(`cola/gitcmds.py:241`). Git refuses a branch named `HEAD`, so `'heads/' + currentbranch` needs no
special case.

**The inline HEAD node cannot grow past an outer radius of 8 px.** The semantic paint test's
tightest sample (`incoming_y`) sits 9 px from the node center and asserts `> node_guard`.
```

Und im Abschnitt „## Tests":

```markdown
**`Interaction.confirm` is the console implementation in tests.** `standard.install()` runs only
from `cola/app.py`, so a confirmation in a test writes to stdout and reads `sys.stdin` — under
pytest capture that is an error, not a `False`. Monkeypatch it in every test that can reach one.

**`cmds.do()` swallows exceptions** into `Interaction.critical` (`cola/cmds.py:3591`). A broken
command does not fail a test by itself; assert on the git state or the model instead.
```

### Schritt 8.3 — `SKILL.md` des project-brief

Ersetze im Absatz über den Stand der Arbeitspakete

```
Four work packages have shipped: the inline commit history in the main window, the commit file
panel beside it, the rename itself, and double-clicking a file to open its diff in a window.
```

durch

```
Five work packages have shipped: the inline commit history in the main window, the commit file
panel beside it, the rename itself, double-clicking a file to open its diff in a window, and the
history's mouse actions (double-click a commit to switch branch) plus the HEAD/current-branch
marking in the inline graph.
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** unverändert grün (Doku ändert keinen Code).

```bash
cd /home/hermes-agent/Projects/git-fanta && garden check/fmt && garden check/pyupgrade && garden check/mypy
```

**Erwartet:** alle drei ohne Befund. Schlägt `check/mypy` an `_row_labels` oder
`set_current_branch` an: die Annotationen stehen im Plan, `from __future__ import annotations`
steht in `cola/widgets/dag.py:1` — dann **stoppen und melden**.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "docs: dokumentiere Maus-Aktionen und HEAD-Markierung der History"
```

---

## Manuelle Abnahme

Nach Task 8 einmal die Anwendung starten und der Reihe nach prüfen:

```bash
cd /home/hermes-agent/Projects/git-fanta && garden run
```

1. **Doppelklick auf die Spitze eines anderen Branches** wechselt dorthin, ohne Rückfrage. Die
   Fenstertitelzeile und der markierte Chip ziehen nach.
2. **Doppelklick auf die Spitze des aktuellen Branches** tut nichts.
3. **Doppelklick auf einen Commit dazwischen** öffnet die Rückfrage. „Cancel" lässt alles stehen.
4. Dieselbe Rückfrage mit „Checkout Detached HEAD" bestätigen: HEAD löst sich ab, die Zeile
   bekommt einen `HEAD`-Chip, kein Branch trägt mehr den Stern.
5. **Doppelklick auf die Branch-Spitze im abgelösten Zustand** hängt HEAD wieder an: Stern zurück
   am Branch, `HEAD`-Chip weg.
6. Der **HEAD-Knoten** ist in hellem *und* dunklem Theme auf einen Blick zu finden
   (`View → Theme` umschalten).
7. **Überschrift „History" und die `--all`-Zeile** kleben nicht mehr an der Kante, und die Zeile
   steht bündig über dem Commit-Baum.
8. Dasselbe im **eigenständigen DAG-Fenster** (`View → Visualize Current Branch` oder
   `git fanta dag`): Doppelklick in der Commit-Liste wirkt, Doppelklick im großen Graph nicht.
9. **Bei schmutzigem Arbeitsverzeichnis** einen Branchwechsel per Doppelklick versuchen: Git
   lehnt ab und die vorhandene Fehlermeldung erscheint (`Interaction.command`), die Anwendung
   bleibt benutzbar.

Danach die Frontmatter dieses Plans ergänzen (`status`, `completed_at`, `plan_commit`,
`implementation_branch`, `implementation_head`, `ci_run`, `manual_verification`) — wie in den
vier abgeschlossenen Plänen in `docs/plans/`.
