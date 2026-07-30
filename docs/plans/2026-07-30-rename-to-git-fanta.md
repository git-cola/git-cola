---
status: completed
completed_at: 2026-07-31
plan_commit: f57ca256
implementation_branch: renaming/opus5/minimax-M3
implementation_head: 3083c9dd
ci_run: nicht ausgefuehrt (lokal gruen)
manual_verification: |
  - ./bin/git-fanta version --brief  -> 4.19.0
  - App wurde gestartet, Titel und About zeigen "Git Fanta", Fenster-Icon vorhanden
  - cola.tabwidth aus einer alten .gitconfig wird als fanta.tabwidth gelesen (test_legacy_config_prefix_is_still_read)
  - ~/.config/git-cola wurde nach ~/.config/git-fanta migriert (test_migration_copies_the_legacy_directory)
---

# Umbenennung: git-cola → git-fanta

**Erstellt:** 2026-07-30
**Branch:** `renaming/opus5/plan` (Basis: `cd365ba7`)
**Umfang:** Stufe 2 — alles Nutzersichtbare wird umbenannt, das Python-Paket `cola/` bleibt.

---

## 0. Wie dieser Plan zu lesen ist

Dieser Plan ist so geschrieben, dass er **ohne Vorwissen und ohne eigene Entscheidungen**
ausgeführt werden kann. Es gilt:

- **Führe die Tasks strikt in der Reihenfolge 0 → 13 aus.** Kein Task darf übersprungen werden.
- **Jeder Task ist ein Commit.** Task-Grenze = Commit-Grenze. Die Commit-Message steht jeweils
  am Ende des Tasks wörtlich da.
- **Jeder Task hat RED → GREEN → VERIFIKATION.** Der RED-Schritt schreibt zuerst den Test, der
  fehlschlagen *muss*. Steht dort eine erwartete Fehlermeldung, dann muss die tatsächliche
  Ausgabe dazu passen. Passt sie nicht, ist etwas anders als angenommen → **stoppen und melden**,
  nicht weitermachen.
- **Zeilennummern sind Orientierung, nicht Wahrheit.** Vor jedem Edit steht ein `grep`-Befehl,
  der den Anker findet. Benutze immer den `grep`, nicht die Zeilennummer.
- **Nach jedem Task ist die Test-Suite grün.** Ist sie das nicht, ist der Task nicht fertig.
- Wenn ein Befehl fehlschlägt und der Plan dafür keinen Ausweg nennt: **stoppen und melden.**
- **Der Dateiname dieses Plans enthält bewusst kein `git-cola`.** Er wird aus
  `.claude/skills/project-brief/` heraus referenziert, und der Wächter-Test aus Task 2 scannt
  dieses Verzeichnis mit — ein Pfadstring mit dem alten Namen würde ihn rot machen. Beim
  Umbenennen oder Kopieren dieses Dokuments diese Eigenschaft erhalten.

Die Standard-Testbefehle in diesem Plan:

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test
```

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/rename_guard_test.py
```

---

## 1. Ziel

Das Projekt heißt nach außen `git-fanta`. Konkret:

| Bereich | vorher | nachher |
|---|---|---|
| Ausführbare Datei | `git-cola` | `git-fanta` |
| Git-Subkommando | `git cola` | `git fanta` |
| Anzeigename | `Git Cola` | `Git Fanta` |
| Distributionsname | `git-cola` (PyPI) | `git-fanta` |
| git-config-Keys | `cola.fontdiff` … | `fanta.fontdiff` … |
| Umgebungsvariablen | `GIT_COLA_MSG` … | `GIT_FANTA_MSG` … |
| Konfig-Verzeichnis | `~/.config/git-cola/` | `~/.config/git-fanta/` |
| Commit-Msg-Hook | `cola-prepare-commit-msg` | `fanta-prepare-commit-msg` |
| Desktop-/Icon-Dateien | `git-cola.desktop`, `git-cola.svg` | `git-fanta.*` |

**„Nichts geht kaputt" heißt hier wörtlich:** jede der drei letzten Zeilen bekommt einen
Rückwärts-Fallback, damit bestehende `~/.gitconfig`-Einträge, Hooks und gespeicherte
Fensterlayouts weiterhin funktionieren.

## 2. Nicht-Ziele — was **nicht** umbenannt wird

Diese Punkte sind bewusste Entscheidungen. Wer sie ändert, bricht etwas.

| Bleibt `cola` | Begründung |
|---|---|
| Python-Paket `cola/`, alle `import cola…` | Stufe-2-Entscheidung. 125 Import-Zeilen in 41 Dateien plus 20592 `#:`-Quellrefs in den `.po`-Dateien wären betroffen — hohes Risiko, null Nutzen für den Anwender. |
| `cola/resources.py:21` + `:28` (`site-packages/cola`, `pkgs/cola`) | Prüfen den **Paket**-Verzeichnisnamen. Der bleibt `cola`. Änderung bricht die Prefix-Erkennung im installierten Zustand. |
| `icons.cola()` in `cola/icons.py:220` | Interner Symbolname. Siehe **Falle F3** — Umbenennen bricht die Toolbar *lautlos*. |
| `ColaApplication`, `ColaQApplication` (`cola/app.py:250`, `:351`) | Interne Klassennamen, nicht nutzersichtbar. |
| `CHANGES.rst` | 1067 Zeilen Upstream-Release-Historie. Umschreiben fälscht die Historie und erzeugt tote Links. |
| `docs/plans/*.md` | Abgeschlossene Design-Records. Gleiche Regel wie `CHANGES.rst`: Historie wird nicht umgeschrieben. |
| Upstream-URLs (39 Zeilen, siehe §3) | Zeigen auf das echte Projekt `github.com/git-cola/git-cola`. Umgeschrieben wären sie 404. |
| Upstream-Remotes in `garden.yaml` | 75 Forks echter Contributor. |
| `url:` des Hauptbaums in `garden.yaml` | Bleibt `${gl-https}/git-cola/git-cola.git`. Folge: `garden grow git-fanta` klont **Upstream**, nicht den Fork. Wer den Fork will, nutzt `origin` (`hermes-agent-ak/git-fanta`). Bewusste Konsequenz der Entscheidung „Upstream-Referenzen bleiben". |
| `.github/workflows/ci.yml:129` `brew install git-cola` | Installiert die **echte Homebrew-Formel** als Abhängigkeit des macOS-Jobs. `brew install git-fanta` existiert nicht → Job bricht. |

## 3. Ausschlussliste (verbatim, wird in Task 2 und Task 3 gebraucht)

**A — komplett ausgenommene Dateien und Pfade:**

```
CHANGES.rst
garden.yaml
cola/i18n/*      (eigener Task 10)
docs/plans/*     (Design-Records)
qtpy/*           (vendored)
```

**B — Zeilen-Marker.** Jede Zeile, die einen dieser Strings enthält, wird **nicht** angefasst:

```
github.com/git-cola
gitlab.com/git-cola
git-cola.github.io
git-cola.gitlab.io
git-cola.readthedocs.io
pypi.org/project/git-cola
src.fedoraproject.org/rpms/git-cola
results.pre-commit.ci
flathub/com.github.git_cola
brew install git-cola
```

Diese Marker treffen exakt **39 Zeilen** in 15 Dateien. Sie sind in Task 1 durch einen
Charakterisierungstest abgesichert.

## 4. Fallen, die bereits verifiziert wurden

| # | Falle | Beleg |
|---|---|---|
| **F1** | Ein `sed` über *alle* Dateien zerstört 820 Zeilen Upstream-Referenzen. | Gemessen: `git grep -In "git-cola" \| grep -cE "<Marker>"` → 820 (mit `CHANGES.rst`/`garden.yaml`), 39 ohne. |
| **F2** | Ein **case-insensitives** `sed` (`s/cola/fanta/gi`) zerstört echte Wörter: `Colapsar`, `Colar`, `colaborador` (pt/es-Übersetzungen) und den Contributor-Namen `Nicolas`. **Niemals `-i`-Flag am `sed`-Regex benutzen.** | `git grep -Iioh -E "[a-z]*cola[a-z]+"` |
| **F3** | `cola/widgets/toolbar.py:253` macht `getattr(icons, command_icon, None)`. `cola/widgets/toolbarcmds.py:283` + `:285` setzen `'icon': 'cola'`. Wird `icons.cola()` umbenannt, liefert `getattr` **`None`** — kein Fehler, kein Icon. Lautloser Bruch. Deshalb bleibt `icons.cola()`. | `cola/widgets/toolbar.py:252-256` |
| **F4** | `cola/version.py:72` ruft `metadata.version('git-cola')`. Der String **muss** dem `name` in `pyproject.toml:6` entsprechen, sonst wirft `importlib.metadata` `PackageNotFoundError` und die Versionsanzeige fällt auf den Builtin-Wert zurück. | `cola/version.py:72`, `pyproject.toml:6` |
| **F5** | `sed` benennt **keine Dateien** um. Nach Task 2 zeigt z. B. `cola/resources.py:113` auf `doc('git-fanta.rst')`, die Datei heißt aber noch `docs/git-cola.rst`. Deshalb sind `sed` und `git mv` **ein einziger Task**. | Dry-Run beobachtet |
| **F6** | `sed`-Adressen mit `/regex/` brechen, wenn der Regex `/` enthält (`sed: extra characters after command`). Es **muss** der alternative Delimiter `\%…%` benutzt werden. | Dry-Run: erste Variante schlug fehl, `\%…%` funktionierte |
| **F7** | `cola/main.py:31`, `:97` und `:800` benutzen alle den String `'cola'` als Default-Subkommando. Die drei **müssen** gemeinsam geändert werden, sonst wirft argparse `invalid choice: 'cola'`. | `cola/main.py:26-31`, `:97`, `:800` |
| **F8** | `cola/guicmds.py:454`, `:478`, `:494` rufen `resources.xdg_config_home('git-cola', 'layouts')` **direkt** auf und umgehen `resources.config_home()`. Wer nur `config_home()` migriert, verliert die gespeicherten Layouts. | `cola/guicmds.py:454` |

## 5. Vorhandenes, das wiederverwendet wird (nicht neu bauen)

| Vorhanden | Wo | Wofür in diesem Plan |
|---|---|---|
| Legacy-Pfad-Fallback für `~/.cola` | `cola/settings.py:276-284` | **Vorbild** für den `~/.config/git-cola`-Fallback in Task 9. Gleiches Muster kopieren, nicht neu erfinden. |
| `RENAMED`-Migrationsdict | `cola/widgets/toolbar.py:79-81` | **Vorbild** für Namensmigration. Zeigt, dass das Projekt Umbenennungen über eine Mapping-Tabelle löst. |
| `_renamed_keys`-Mechanik | `cola/gitcfg.py:236`, `:285` | Der **Einhängepunkt** für den `cola.*`-Fallback in Task 7. Kein neuer Lookup-Pfad nötig. |
| Zentrale Key-Tabelle | `cola/models/prefs.py:13-73` | Alle `cola.*`-Keys stehen dort als Konstanten. Task 7 ändert **nur diese Tabelle** plus 3 hartkodierte Stellen. |
| `resources.config_home()` | `cola/resources.py:220-222` | Einziger Chokepoint für das Konfig-Verzeichnis (bis auf F8). |
| `app_context`-Fixture | `test/helper.py:85` | Echtes temporäres Git-Repo. **Nicht** selbst Repos bauen oder `context.git` mocken. |

---

# TASKS

## Task 0 — Entwicklungsumgebung herstellen

> **Blockierend. Kein Commit.** Ohne lauffähiges `pytest` ist TDD unmöglich.

**Aktueller Stand (gemessen am 2026-07-30):** `garden`, `pytest`, `pip` und `env3/` fehlen auf
diesem Rechner. `python3` ist 3.14.4, PyQt5 ist systemweit vorhanden, `polib` fehlt.

### Schritte

1. Prüfe, ob die Umgebung schon existiert:

```bash
ls -d /home/hermes-agent/Projects/git-fanta/env3 2>/dev/null && echo VORHANDEN || echo FEHLT
```

2. Falls `FEHLT`, baue sie:

```bash
cd /home/hermes-agent/Projects/git-fanta && garden dev/virtualenv && garden dev
```

3. Falls `garden` nicht gefunden wird, ist das der Fallback:

```bash
cd /home/hermes-agent/Projects/git-fanta && python3 -m venv --system-site-packages env3 && ./env3/bin/python -m ensurepip --upgrade && ./env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

### Verifikation (muss grün sein, bevor Task 1 beginnt)

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -5
```

**Erwartet:** eine Zeile der Form `NNN passed` ohne `failed` und ohne `error`.

Notiere die Zahl `NNN` — das ist die **Baseline**. Ab jetzt darf diese Zahl in keinem Task
sinken.

> **Wenn dieser Schritt nicht grün wird: STOPP.** Melde, dass die Umgebung nicht herstellbar ist,
> und führe keinen weiteren Task aus. Ein Rename ohne Testabdeckung ist genau das, was dieser
> Plan verhindern soll.

---

## Task 1 — Charakterisierungstest: Upstream-Referenzen sind geschützt

**Ziel:** Bevor irgendetwas umbenannt wird, wird festgeschrieben, was **nicht** umbenannt werden
darf. Dieser Test ist das Sicherheitsnetz für Task 2.

> **Dies ist ein Charakterisierungstest.** Er ist sofort grün — das ist korrekt und *kein*
> kaputter RED-Schritt. Seine Aufgabe ist, in Task 2 rot zu werden, falls `sed` zu viel trifft.

### Schritt 1.1 — Testdatei anlegen

Lege `test/rename_guard_test.py` mit **exakt** diesem Inhalt an:

```python
"""Wächter-Tests für die Umbenennung git-cola -> git-fanta.

Zwei Invarianten werden hier festgeschrieben:

1. Verweise auf das Upstream-Projekt (github.com/git-cola/git-cola und Freunde)
   bleiben unverändert, weil sie auf ein echtes, weiterhin existierendes Projekt
   zeigen.
2. Der Produktname "git-cola" kommt sonst nirgends mehr in den versionierten
   Quellen vor.

Test 2 wird erst in Task 2 des Umbenennungsplans hinzugefuegt.
"""

import pathlib
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Zeilen mit einem dieser Marker sind Upstream-Verweise und werden nie umbenannt.
UPSTREAM_MARKERS = (
    'github.com/git-cola',
    'gitlab.com/git-cola',
    'git-cola.github.io',
    'git-cola.gitlab.io',
    'git-cola.readthedocs.io',
    'pypi.org/project/git-cola',
    'src.fedoraproject.org/rpms/git-cola',
    'results.pre-commit.ci',
    'flathub/com.github.git_cola',
    'brew install git-cola',
    # Bewusste historische Nennung des Vorgaengerprojekts in Fliesstext. Wer den
    # alten Namen in einer Doku-Zeile erwaehnen muss, benutzt genau eine dieser
    # Formulierungen - dann ist die Absicht am Satz selbst ablesbar.
    'fork of git-cola',
    'renamed from git-cola',
)

# Diese Dateien und Praefixe werden komplett ausgespart.
EXEMPT_FILES = frozenset({'CHANGES.rst', 'garden.yaml'})
EXEMPT_PREFIXES = ('cola/i18n/', 'docs/plans/', 'qtpy/')

# Der alte Produktname in allen Schreibweisen, die im Repo vorkommen.
LEGACY_PRODUCT_NAMES = ('git-cola', 'git_cola', 'Git Cola', 'git cola')

# Konkrete Upstream-Verweise, die nach der Umbenennung noch da sein muessen.
# Format: (Pfad relativ zum Repo-Wurzelverzeichnis, erwarteter Teilstring)
PROTECTED_REFERENCES = (
    ('README.md', 'https://github.com/git-cola/git-cola.git'),
    ('cola/gravatar.py', 'https://git-cola.github.io/images/git-64x64.jpg'),
    ('cola/widgets/about.py', 'https://github.com/git-cola/git-cola/issues'),
    ('cola/widgets/log.py', 'https://git-cola.readthedocs.io/en/latest/'),
    ('cola/settings.py', 'https://github.com/git-cola/git-cola/issues/1241'),
    ('cola/themes.py', 'https://github.com/git-cola/git-cola/issues/905'),
    ('docs/conf.py', 'https://gitlab.com/git-cola/git-cola'),
    ('.github/workflows/ci.yml', 'brew install git-cola'),
    ('test/gravatar_test.py', 'git-cola.github.io'),
)


def tracked_text_files():
    """Liefert (Pfad, Inhalt) fuer jede versionierte Textdatei ausserhalb der Ausnahmen."""
    listing = subprocess.run(
        ['git', 'ls-files', '-z'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for name in listing.split('\0'):
        if not name or name in EXEMPT_FILES or name.startswith(EXEMPT_PREFIXES):
            continue
        path = REPO_ROOT / name
        if path.is_symlink() or not path.is_file():
            continue
        try:
            yield name, path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue


def test_upstream_references_are_preserved():
    """Charakterisierung: Verweise auf das Upstream-Projekt bleiben erhalten."""
    missing = []
    for name, needle in PROTECTED_REFERENCES:
        path = REPO_ROOT / name
        if not path.is_file():
            missing.append(f'{name}: Datei fehlt')
            continue
        if needle not in path.read_text(encoding='utf-8'):
            missing.append(f'{name}: "{needle}" fehlt')

    assert not missing, 'Upstream-Verweise wurden zerstoert:\n' + '\n'.join(missing)


def test_changes_rst_history_is_untouched():
    """Charakterisierung: die Upstream-Release-Historie wird nicht umgeschrieben."""
    text = (REPO_ROOT / 'CHANGES.rst').read_text(encoding='utf-8')
    assert 'git-cola' in text
    assert 'git-fanta' not in text
```

### Schritt 1.2 — Formatierung anwenden

```bash
cd /home/hermes-agent/Projects/git-fanta && ./env3/bin/cercis test/rename_guard_test.py && ./env3/bin/isort --force-single-line-imports --py=39 --no-lines-before=STDLIB test/rename_guard_test.py
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/rename_guard_test.py
```

**Erwartet:** `2 passed`.

Dann die volle Suite:

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 2 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add test/rename_guard_test.py && git commit -m "test: charakterisiere geschuetzte Upstream-Referenzen vor der Umbenennung"
```

---

## Task 2 — Produktname umbenennen: gescopter `sed` + `git mv`

**Ziel:** `git-cola` → `git-fanta` in Dateiinhalten **und** Dateinamen, in einem Schritt.

> **Warum ein Task und nicht zwei:** Nach dem `sed` allein zeigt z. B. `cola/resources.py:113`
> auf `doc('git-fanta.rst')`, während die Datei noch `docs/git-cola.rst` heißt (Falle **F5**).
> Zwischen `sed` und `git mv` ist das Repo inkonsistent. Deshalb gehören sie in einen Commit.

### Schritt 2.1 (RED) — Wächter-Test erweitern

Hänge **ans Ende** von `test/rename_guard_test.py` an:

```python
def test_product_name_is_git_fanta():
    """Der alte Produktname kommt ausserhalb der Upstream-Verweise nicht mehr vor."""
    offenders = []
    for name, text in tracked_text_files():
        for number, line in enumerate(text.splitlines(), start=1):
            if any(marker in line for marker in UPSTREAM_MARKERS):
                continue
            if any(legacy in line for legacy in LEGACY_PRODUCT_NAMES):
                offenders.append(f'{name}:{number}: {line.strip()[:100]}')

    assert not offenders, (
        f'{len(offenders)} Zeilen tragen noch den alten Produktnamen:\n'
        + '\n'.join(offenders[:40])
    )


def test_no_legacy_product_name_in_tracked_filenames():
    """Kein versionierter Dateiname enthaelt noch "git-cola" oder "_activate_cola"."""
    listing = subprocess.run(
        ['git', 'ls-files', '-z'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    offenders = [
        name
        for name in listing.split('\0')
        if name
        and not name.startswith(('cola/i18n/', 'docs/plans/'))
        and ('git-cola' in name or '_activate_cola' in name)
    ]

    assert not offenders, 'Diese Dateien muessen umbenannt werden:\n' + '\n'.join(offenders)
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/rename_guard_test.py 2>&1 | tail -20
```

**Erwartete Fehlermeldung — beide neuen Tests schlagen fehl:**

```
AssertionError: 517 Zeilen tragen noch den alten Produktnamen:
```
und
```
AssertionError: Diese Dateien muessen umbenannt werden:
```
mit **18 Dateinamen** in der Liste.

> Weicht die Zahl 517 um mehr als ±5 ab, hat sich der Repo-Zustand seit Planerstellung geändert.
> **Stoppen und melden.** Die 18 Dateinamen müssen exakt der Liste in Schritt 2.3 entsprechen.
>
> Die beiden Tests aus Task 1 müssen in diesem Lauf **weiterhin passen** (`2 passed, 2 failed`).

### Schritt 2.2 (GREEN, Teil 1) — der gescopte `sed`

Führe **exakt diesen Block** aus. Nichts daran verändern — insbesondere nicht den `\%…%`-
Delimiter (Falle **F6**) und **niemals** ein `i`-Flag an die `s`-Kommandos hängen (Falle **F2**).

```bash
cd /home/hermes-agent/Projects/git-fanta && UP='github\.com/git-cola\|gitlab\.com/git-cola\|git-cola\.github\.io\|git-cola\.gitlab\.io\|git-cola\.readthedocs\.io\|pypi\.org/project/git-cola\|src\.fedoraproject\.org/rpms/git-cola\|results\.pre-commit\.ci\|flathub/com\.github\.git_cola\|brew install git-cola' && git ls-files -z -- . ':(exclude)CHANGES.rst' ':(exclude)garden.yaml' ':(exclude)cola/i18n/*' ':(exclude)docs/plans/*' ':(exclude)qtpy/*' | xargs -0 grep -Il '' | xargs sed -i -e "\\%$UP%!s/git-cola/git-fanta/g" -e "\\%$UP%!s/git_cola/git_fanta/g" -e "\\%$UP%!s/Git Cola/Git Fanta/g" -e "\\%$UP%!s/git cola/git fanta/g"
```

**Sofort prüfen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && echo "geaenderte Dateien: $(git diff --name-only | wc -l)" && ./env3/bin/python -c "
import ast, pathlib
bad = []
for p in list(pathlib.Path('cola').rglob('*.py')) + list(pathlib.Path('test').rglob('*.py')):
    try:
        ast.parse(p.read_text(encoding='utf-8'))
    except SyntaxError as e:
        bad.append(f'{p}: {e}')
print('SYNTAXFEHLER:', bad or 'keine')
"
```

**Erwartet:** `geaenderte Dateien: 81` (±2) und `SYNTAXFEHLER: keine`.

> **Diese eine Fehlermeldung ist erwartet und harmlos:**
> ```
> grep: share/doc/git-cola: Is a directory
> ```
> `share/doc/git-cola` ist ein Symlink auf `../../docs`. `grep -Il` meldet ihn als Verzeichnis
> und listet ihn nicht, `sed` fasst ihn also nie an. Der Symlink wird in Schritt 2.3 umbenannt.
> **Das ist kein Grund zu stoppen.**

> Bei Syntaxfehlern: `git checkout -- .` und **stoppen und melden.**

### Schritt 2.3 (GREEN, Teil 2) — Dateien umbenennen

Genau diese 18 Umbenennungen, in dieser Reihenfolge:

```bash
cd /home/hermes-agent/Projects/git-fanta && git mv bin/_activate_cola.py bin/_activate_fanta.py && git mv bin/git-cola bin/git-fanta && git mv bin/git-cola-sequence-editor bin/git-fanta-sequence-editor && git mv cola/icons/git-cola.svg cola/icons/git-fanta.svg && git mv cola/icons/git-cola.ico cola/icons/git-fanta.ico && git mv cola/icons/git-cola-ok.svg cola/icons/git-fanta-ok.svg && git mv cola/icons/git-cola-error.svg cola/icons/git-fanta-error.svg && git mv cola/icons/dark/git-cola.svg cola/icons/dark/git-fanta.svg && git mv cola/icons/dark/git-cola.ico cola/icons/dark/git-fanta.ico && git mv contrib/_git-cola contrib/_git-fanta && git mv contrib/git-cola-completion.bash contrib/git-fanta-completion.bash && git mv contrib/darwin/git-cola contrib/darwin/git-fanta && git mv contrib/darwin/git-cola.icns contrib/darwin/git-fanta.icns && git mv docs/git-cola.rst docs/git-fanta.rst && git mv share/applications/git-cola.desktop share/applications/git-fanta.desktop && git mv share/applications/git-cola-folder-handler.desktop share/applications/git-fanta-folder-handler.desktop && git mv share/metainfo/git-cola.appdata.xml share/metainfo/git-fanta.appdata.xml && git mv share/doc/git-cola share/doc/git-fanta
```

### Schritt 2.4 (GREEN, Teil 3) — die drei Stellen, die `sed` nicht sieht

`sed` hat den Import `import _activate_cola` nicht getroffen, weil dort kein `git-cola` steht.

**Anker finden:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -rn "_activate_cola" bin/
```

**Erwartet:** drei Treffer — `bin/git-fanta`, `bin/git-fanta-sequence-editor`, `bin/git-dag`,
jeweils die Zeile `import _activate_cola`.

**Ersetzen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i 's/^import _activate_cola$/import _activate_fanta/' bin/git-fanta bin/git-fanta-sequence-editor bin/git-dag
```

Und in `bin/_activate_fanta.py` die Docstring-Zeile:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "cola development environment\|git_cola.egg" bin/_activate_fanta.py
```

**Erwartet:** `"""Activate the cola development environment"""` und `git_fanta.egg-info`
(letzteres hat `sed` bereits korrekt umgeschrieben, weil `pyproject.toml:6` jetzt `git-fanta`
heißt und setuptools daraus `git_fanta.egg-info` erzeugt).

Ersetze nur den Docstring:

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i 's/Activate the cola development environment/Activate the fanta development environment/' bin/_activate_fanta.py
```

### Schritt 2.5 — Formatierung

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt
```

Falls `garden` fehlt:

```bash
cd /home/hermes-agent/Projects/git-fanta && ./env3/bin/cercis bin bin/git-* cola test extras/sphinxtogithub && ./env3/bin/isort --force-single-line-imports --py=39 --no-lines-before=STDLIB bin bin/git-* cola test extras/sphinxtogithub
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/rename_guard_test.py
```

**Erwartet:** `4 passed`.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 4 passed, **0 failed**.

> Erwartete Nicht-Brüche, zur Beruhigung: `test/cmds_test.py:32-33` und `test/display_test.py:6`
> `:14` enthalten `git-cola` in **Eingabe und Erwartungswert zugleich**. `sed` ändert beide, der
> Test bleibt in sich konsistent und grün.

**Manueller Smoke-Test (Pflicht — kein Test deckt den Start ab):**

```bash
cd /home/hermes-agent/Projects/git-fanta && ./env3/bin/python ./bin/git-fanta version --brief
```

**Erwartet:** eine Versionsnummer, kein Traceback.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "chore: benenne Produktnamen git-cola in git-fanta um

Gescopter sed ueber alle versionierten Textdateien plus 18 Dateiumbenennungen.
Upstream-Referenzen (github.com/git-cola, brew install git-cola, CHANGES.rst,
garden.yaml, docs/plans) bleiben unveraendert und sind durch
test/rename_guard_test.py abgesichert."
```

---

## Task 3 — `garden.yaml` manuell aufteilen

**Ziel:** Die Build-Kommandos des Forks heißen `git-fanta`, die 75 Upstream-Remotes bleiben.

`garden.yaml` war in Task 2 ausgenommen, weil dort beides in einer Datei steht.

### Schritt 3.1 (RED) — Test ergänzen

Hänge an `test/rename_guard_test.py` an:

```python
def test_garden_build_commands_use_git_fanta():
    """Die Build-Kommandos des Forks sind umbenannt, die Upstream-Remotes nicht."""
    text = (REPO_ROOT / 'garden.yaml').read_text(encoding='utf-8')

    # Fork-eigene Build-Artefakte tragen den neuen Namen.
    assert './bin/git-fanta' in text
    assert 'cola/icons/git-fanta.svg' in text
    assert './bin/git-cola' not in text

    # Upstream-Remotes bleiben erhalten.
    assert 'davvid/git-cola.git' in text
    assert 'git-cola/git-cola.git' in text
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/rename_guard_test.py::test_garden_build_commands_use_git_fanta 2>&1 | tail -8
```

**Erwartete Fehlermeldung:** `AssertionError: assert './bin/git-fanta' in text`

### Schritt 3.2 (GREEN) — nur Kommando-Zeilen umschreiben

Die Umbenennung in `garden.yaml` betrifft ausschließlich Zeilen ohne `${gh-`, `${gl-` und ohne
`fedoraproject`:

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i -e '\%\${gh-\|\${gl-\|fedoraproject\|git-cola\.gitlab\.io\|git-cola\.github\.io%!s/git-cola/git-fanta/g' -e '\%\${gh-\|\${gl-\|fedoraproject\|git-cola\.gitlab\.io\|git-cola\.github\.io%!s/git_cola/git_fanta/g' -e '\%\${gh-\|\${gl-\|fedoraproject%!s/Git Cola/Git Fanta/g' garden.yaml
```

**Prüfen, was sich geändert hat:**

```bash
cd /home/hermes-agent/Projects/git-fanta && git diff --stat garden.yaml && git diff garden.yaml | grep "^[+-]" | grep -i "cola\|fanta" | head -40
```

**Erwartet:** Änderungen nur in `commands:`, `variables:` und Kommentaren — z. B.
`run: ${activate} ./bin/git-fanta "$@"`, `cola-app: ${TREE_PATH}/git-fanta.app`,
`install -m 664 cola/icons/git-fanta.svg`. **Keine** Änderung in den `remotes:`- und `url:`-
Blöcken.

**Der Baum-Schlüssel `git-cola:` (erste Zeile unter `trees:`)** wird durch den `sed` zu
`git-fanta:` — das ist gewollt und korrekt, es ist der lokale Garden-Baumname.

> **Achtung, manuell prüfen:** die Zeile `worktree: git-cola` im `todo:`-Baum wird ebenfalls zu
> `worktree: git-fanta` und muss das auch, weil sie auf den lokalen Baumnamen verweist.
> Kontrolliere mit:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "worktree:\|^  git-fanta:\|^  git-cola:" garden.yaml
> ```
> **Erwartet:** `git-fanta:` als Baumname und `worktree: git-fanta`.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && ./env3/bin/python -c "import yaml,sys; yaml.safe_load(open('garden.yaml')); print('garden.yaml parst')" 2>/dev/null || ./env3/bin/python -c "
import sys
try:
    import yaml
except ImportError:
    print('PyYAML fehlt - ueberspringe Parse-Check')
    sys.exit(0)
yaml.safe_load(open('garden.yaml'))
print('garden.yaml parst')
"
```

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 5 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "chore: benenne die Fork-Build-Kommandos in garden.yaml um

Die 75 Upstream-Contributor-Remotes und die fedora/pages/flatpak-URLs bleiben
unveraendert, weil sie auf existierende Fremdprojekte zeigen."
```

---

## Task 4 — Distributionsnamen-Kopplung absichern

**Ziel:** `cola/version.py` fragt `importlib.metadata` nach dem Distributionsnamen. Nach Task 2
steht dort `'git-fanta'`, und `pyproject.toml:6` sagt ebenfalls `git-fanta`. Diese Kopplung ist
unsichtbar und bricht lautlos (Falle **F4**) — deshalb bekommt sie einen Test.

### Schritt 4.1 (RED) — Test schreiben

Hänge an `test/rename_guard_test.py` an:

```python
def test_distribution_name_matches_pyproject():
    """version.py fragt importlib.metadata mit genau dem Namen aus pyproject.toml.

    Laufen die beiden auseinander, wirft importlib.metadata PackageNotFoundError
    und die Versionsanzeige faellt still auf den Builtin-Wert zurueck.
    """
    import re

    pyproject = (REPO_ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    match = re.search(r'^name\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match, 'pyproject.toml hat keinen name-Eintrag'
    distribution = match.group(1)

    version_py = (REPO_ROOT / 'cola' / 'version.py').read_text(encoding='utf-8')
    assert f"metadata.version('{distribution}')" in version_py, (
        f'cola/version.py fragt nicht nach "{distribution}"'
    )
    assert distribution == 'git-fanta'
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/rename_guard_test.py::test_distribution_name_matches_pyproject 2>&1 | tail -6
```

> **Sonderfall:** Dieser Test ist ein **Charakterisierungstest** und geht sofort auf `1 passed`,
> weil Task 2 beide Stellen bereits konsistent umgeschrieben hat. Das ist korrekt. Der Test
> existiert, damit ein späteres Auseinanderlaufen sofort auffällt.
>
> Geht er **rot**, dann hat Task 2 eine der beiden Stellen verfehlt. Prüfe:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "^name" pyproject.toml && grep -n "metadata.version" cola/version.py
> ```
> Beide müssen `git-fanta` sagen. Korrigiere von Hand, dann weiter.

### Schritt 4.2 — Entry-Points prüfen

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -n '/\[project.scripts\]/,/^\[/p' pyproject.toml
```

**Erwartet nach Task 2:**

```
[project.scripts]
cola = "cola.main:main"
git-fanta = "cola.main:main"
git-dag = "cola.dag:main"
git-fanta-sequence-editor = "cola.sequenceeditor:main"
```

Die erste Zeile `cola = …` ist das Kurzkommando. Benenne es um:

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i 's/^cola = "cola.main:main"$/fanta = "cola.main:main"/' pyproject.toml && sed -n '/\[project.scripts\]/,/^\[/p' pyproject.toml
```

**Erwartet:** `fanta = "cola.main:main"` als erste Zeile.

> `[tool.setuptools] packages = ["cola", …]` und `[tool.setuptools.package-data] cola = [...]`
> bleiben **unverändert** — sie benennen das Python-Paket, das laut Scope `cola` bleibt.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 6 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "test: sichere die Kopplung zwischen pyproject-Name und version.py ab

Benennt ausserdem den Kurz-Entrypoint cola in fanta um."
```

---

## Task 5 — CLI-Subkommando `cola` → `fanta` (mit Alias)

**Ziel:** `git fanta` statt `git fanta cola`. Das alte `cola` bleibt als Alias funktionsfähig.

Betroffen sind drei Stellen, die zusammen konsistent sein müssen (Falle **F7**).

### Schritt 5.1 (RED) — Test schreiben

Hänge an `test/main_test.py` an:

```python
def test_default_subcommand_is_fanta():
    """Ohne Subkommando landet der Aufruf im "fanta"-Parser."""
    args = main.parse_args(['fanta'])

    assert args.func is main.cmd_cola


def test_legacy_cola_subcommand_still_works():
    """Das alte "cola"-Subkommando bleibt als Alias erhalten."""
    args = main.parse_args(['cola'])

    assert args.func is main.cmd_cola
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/main_test.py 2>&1 | tail -12
```

**Erwartete Fehlermeldung:** `test_default_subcommand_is_fanta` schlägt fehl mit

```
SystemExit: 2
```

(argparse schreibt `invalid choice: 'fanta'` nach stderr). `test_legacy_cola_subcommand_still_works`
ist bereits grün — das ist korrekt, es ist der Charakterisierungsteil.

### Schritt 5.2 (GREEN) — `add_command` um Aliase erweitern

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "def add_command" -A 8 cola/main.py
```

Ersetze die **gesamte Funktion** `add_command` durch:

```python
def add_command(
    parent: argparse._SubParsersAction,
    name: str,
    description: str,
    func: Callable,
    aliases: tuple[str, ...] = (),
) -> argparse.ArgumentParser:
    """Add a "git fanta" command with common arguments"""
    parser = parent.add_parser(str(name), help=description, aliases=aliases)
    parser.set_defaults(func=func)
    app.add_common_arguments(parser)
    return parser
```

> `aliases` steht **als letzter Parameter mit Default**. Alle 25 bestehenden Aufrufer übergeben
> vier positionale Argumente und bleiben unverändert lauffähig.

### Schritt 5.3 (GREEN) — die drei `'cola'`-Strings

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "'cola'" cola/main.py
```

**Erwartet:** vier Treffer in den Zeilen ~26, ~27, ~31, ~97, ~800 (zwei davon Kommentar).

**a)** Registrierung — ersetze

```python
    parser = add_command(subparser, 'cola', 'launch git-fanta', cmd_cola)
```

durch

```python
    parser = add_command(
        subparser, 'fanta', 'launch git-fanta', cmd_cola, aliases=('cola',)
    )
```

**b)** Default-Injection — ersetze

```python
    # 'cola' into the command-line so that parse_args()
    # routes them to the 'cola' parser by default.
```

durch

```python
    # 'fanta' into the command-line so that parse_args()
    # routes them to the 'fanta' parser by default.
```

und

```python
        argv.insert(0, 'cola')
```

durch

```python
        argv.insert(0, 'fanta')
```

**c)** Shortcut-Launcher — ersetze

```python
        argv = ['cola', '--prompt']
```

durch

```python
        argv = ['fanta', '--prompt']
```

### Schritt 5.4 — Docstring von `add_cola_command`

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i 's/"""Add the main "git fanta" command. "git fanta cola" is valid"""/"""Add the main "git fanta" command. "git fanta fanta" is valid"""/' cola/main.py && grep -n 'is valid' cola/main.py
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/main_test.py
```

**Erwartet:** `7 passed`.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 8 passed, 0 failed.

**Manueller Smoke-Test:**

```bash
cd /home/hermes-agent/Projects/git-fanta && ./env3/bin/python ./bin/git-fanta --help-commands 2>&1 | head -20
```

**Erwartet:** In der Kommandoliste steht `fanta`, nicht `cola`.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: benenne das CLI-Subkommando cola in fanta um

'cola' bleibt als argparse-Alias erhalten, damit bestehende Skripte und
Shell-Historien weiterlaufen."
```

---

## Task 6 — Umgebungsvariablen `GIT_COLA_*` → `GIT_FANTA_*` mit Fallback

**Ziel:** Acht Variablen umbenennen, alte Namen bleiben wirksam.

Betroffen (gemessen): `GIT_COLA_MSG`, `GIT_COLA_TRACE`, `GIT_COLA_GIT`, `GIT_COLA_ICON_THEME`,
`GIT_COLA_SCALE`, `GIT_COLA_VERBOSE`, `GIT_COLA_SEQ_EDITOR_TITLE`, `GIT_COLA_SEQ_EDITOR_ACTION`.

> **Wichtige Unterscheidung.** `GIT_COLA_MSG` ist **kein** Environment-Variablen-Name, sondern ein
> **Dateiname** in `.git/` (`context.git.git_path('GIT_COLA_MSG')`). Er wird trotzdem umbenannt,
> braucht aber einen Datei-Fallback statt eines Env-Fallbacks.

### Schritt 6.1 (RED) — Tests schreiben

Neue Datei `test/env_rename_test.py`:

```python
"""Tests fuer die Umbenennung der GIT_COLA_*-Umgebungsvariablen."""

from cola import compat

from . import helper
from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


def test_getenv_prefers_new_name(monkeypatch):
    """Der neue Name gewinnt, wenn beide gesetzt sind."""
    monkeypatch.setenv('GIT_FANTA_TRACE', 'neu')
    monkeypatch.setenv('GIT_COLA_TRACE', 'alt')

    assert compat.getenv_with_legacy('GIT_FANTA_TRACE') == 'neu'


def test_getenv_falls_back_to_legacy_name(monkeypatch):
    """Ist nur der alte Name gesetzt, wird er benutzt."""
    monkeypatch.delenv('GIT_FANTA_TRACE', raising=False)
    monkeypatch.setenv('GIT_COLA_TRACE', 'alt')

    assert compat.getenv_with_legacy('GIT_FANTA_TRACE') == 'alt'


def test_getenv_returns_default_when_neither_is_set(monkeypatch):
    monkeypatch.delenv('GIT_FANTA_TRACE', raising=False)
    monkeypatch.delenv('GIT_COLA_TRACE', raising=False)

    assert compat.getenv_with_legacy('GIT_FANTA_TRACE', 'standard') == 'standard'


def test_commit_message_path_prefers_new_file(app_context):
    """Existiert .git/GIT_FANTA_MSG, wird diese Datei benutzt."""
    from cola import gitcmds

    new_path = app_context.git.git_path('GIT_FANTA_MSG')
    helper.write_file(new_path, 'neue Nachricht')

    assert gitcmds.commit_message_path(app_context) == new_path


def test_commit_message_path_falls_back_to_legacy_file(app_context):
    """Existiert nur .git/GIT_COLA_MSG, wird diese Datei benutzt."""
    from cola import gitcmds

    legacy_path = app_context.git.git_path('GIT_COLA_MSG')
    helper.write_file(legacy_path, 'alte Nachricht')

    assert gitcmds.commit_message_path(app_context) == legacy_path


def test_commit_message_path_returns_none_without_a_file(app_context):
    """Ohne Datei bleibt der Rueckgabewert None - der bestehende Vertrag."""
    from cola import gitcmds

    assert gitcmds.commit_message_path(app_context) is None


def test_save_commitmsg_writes_the_new_file(app_context):
    """Geschrieben wird immer nur noch .git/GIT_FANTA_MSG."""
    from cola import core

    path = app_context.model.save_commitmsg('hallo')

    assert path.endswith('GIT_FANTA_MSG')
    assert core.read(path) == 'hallo\n'
```

> **Vor dem RED-Lauf prüfen**, dass `helper.write_file` existiert und `gitcmds.commit_message_path`
> so heißt:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "def write_file" test/helper.py && grep -n "def commit_message_path" -A 6 cola/gitcmds.py
> ```
> Heißt eine der beiden anders, benutze den tatsächlichen Namen und **melde die Abweichung**.
>
> **Wichtig — der bestehende Vertrag:** `commit_message_path` gibt **`None`** zurück, wenn keine
> Datei existiert (`cola/gitcmds.py:989`). Dieser Rückgabewert darf sich nicht ändern; die beiden
> Aufrufer `cola/models/main.py:464` und `cola/widgets/commitmsg.py:292` verlassen sich darauf.

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/env_rename_test.py 2>&1 | tail -12
```

**Erwartete Fehlermeldung:** `AttributeError: module 'cola.compat' has no attribute 'getenv_with_legacy'`
für die ersten drei Tests; die letzten beiden schlagen mit einem Pfad-Vergleich fehl.

### Schritt 6.2 (GREEN) — Helfer in `cola/compat.py`

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && tail -20 cola/compat.py
```

Hänge **ans Ende** von `cola/compat.py` an:

```python
# git-fanta hiess frueher git-cola. Umgebungsvariablen heissen jetzt GIT_FANTA_*,
# die alten GIT_COLA_*-Namen bleiben als Fallback wirksam.
_LEGACY_ENV_PREFIX = 'GIT_COLA_'
_ENV_PREFIX = 'GIT_FANTA_'


def legacy_env_name(name):
    """Return the pre-rename name of a GIT_FANTA_* variable, or None"""
    if name.startswith(_ENV_PREFIX):
        return _LEGACY_ENV_PREFIX + name[len(_ENV_PREFIX) :]
    return None


def getenv_with_legacy(name, default=None):
    """Read an environment variable, falling back to its pre-rename name"""
    value = os.getenv(name)
    if value is not None:
        return value
    legacy = legacy_env_name(name)
    if legacy is not None:
        value = os.getenv(legacy)
        if value is not None:
            return value
    return default
```

> **Prüfe zuerst, ob `import os` in `cola/compat.py` schon vorhanden ist:**
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "^import os" cola/compat.py
> ```
> Fehlt er, füge ihn alphabetisch bei den anderen `import`-Zeilen ein (eine Zeile pro Import).

### Schritt 6.3 (GREEN) — Aufrufstellen umstellen

Nach Task 2 heißen die Variablen im Code noch `GIT_COLA_*` (der `sed` traf nur `git-cola`, nicht
`GIT_COLA_`). Jetzt umbenennen — wieder gescopt, weil `CHANGES.rst` ausgenommen bleibt:

```bash
cd /home/hermes-agent/Projects/git-fanta && git ls-files -z -- cola bin docs test ':(exclude)cola/i18n/*' ':(exclude)docs/plans/*' | grep -zv '^test/env_rename_test\.py$' | xargs -0 grep -Il '' | xargs sed -i 's/GIT_COLA_/GIT_FANTA_/g'
```

> **Warum `test/env_rename_test.py` ausgenommen ist.** Die Datei aus Schritt 6.1 enthält
> `monkeypatch.setenv('GIT_COLA_TRACE', 'alt')` **mit Absicht** — das ist der alte Name, gegen den
> der Fallback getestet wird. Läuft der `sed` darüber, setzen beide Test-Zweige dieselbe Variable
> und die Fallback-Tests beweisen nichts mehr.
>
> **Kontrolliere direkt danach**, dass die Datei unangetastet ist:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -c "GIT_COLA_TRACE" test/env_rename_test.py
> ```
> **Erwartet:** `3`. Steht dort `0`, hat der `sed` doch zugeschlagen — dann
> `git checkout -- test/env_rename_test.py` ist **nicht** möglich (die Datei ist noch nicht
> committed). Stelle die drei Zeilen aus Schritt 6.1 von Hand wieder her.

**Prüfen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && git grep -In "GIT_COLA_" -- . ':(exclude)CHANGES.rst' ':(exclude)cola/i18n/*' ':(exclude)docs/plans/*' ':(exclude)test/env_rename_test.py'
```

**Erwartet:** keine Ausgabe.

Jetzt die vier Lesestellen auf den Fallback-Helfer umstellen.

**a) `cola/git.py`** — Anker:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "GIT_FANTA_TRACE\|GIT_FANTA_GIT" cola/git.py
```

`cola/git.py` importiert im Stil `from .compat import X` (Zeilen 12-15). Halte dich daran.

Ersetze

```python
GIT_FANTA_TRACE = core.getenv('GIT_FANTA_TRACE', '')
GIT = core.getenv('GIT_FANTA_GIT', 'git')
```

durch

```python
GIT_FANTA_TRACE = getenv_with_legacy('GIT_FANTA_TRACE', '')
GIT = getenv_with_legacy('GIT_FANTA_GIT', 'git')
```

und ergänze in der `from .compat import …`-Gruppe **alphabetisch vor `int_types`**:

```python
from .compat import getenv_with_legacy
```

**b) `cola/app.py`** — Anker:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "GIT_FANTA_ICON_THEME" cola/app.py && grep -n "^from . import compat" cola/app.py
```

Ersetze `core.getenv('GIT_FANTA_ICON_THEME')` durch
`compat.getenv_with_legacy('GIT_FANTA_ICON_THEME')`. Fehlt `from . import compat`, füge es
alphabetisch in der `from . import …`-Gruppe ein.

**c) `cola/interaction.py`** — Anker:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "GIT_FANTA_VERBOSE" cola/interaction.py
```

Ersetze `os.getenv('GIT_FANTA_VERBOSE')` durch `compat.getenv_with_legacy('GIT_FANTA_VERBOSE')`.
Die Datei hat bereits `from . import core` (Zeile 9); füge `from . import compat` **davor** ein.

**d) `cola/widgets/defs.py`** — Anker:

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -n '1,8p' cola/widgets/defs.py
```

Ersetze `os.getenv('GIT_FANTA_SCALE', '1')` durch
`compat.getenv_with_legacy('GIT_FANTA_SCALE', '1')`.

> **Achtung:** `cola/widgets/defs.py` hat bislang **keinen einzigen relativen Import** — nur
> `import math` und `import os`. Du fügst mit `from .. import compat` den ersten hinzu. Das ist
> unkritisch (`cola/compat.py` importiert selbst nur `os` und `sys`, es entsteht kein Zyklus),
> aber die Import-Zeile muss nach `import os` und durch eine Leerzeile getrennt stehen —
> `garden fmt` bzw. `isort` erledigt das in der Verifikation dieses Tasks.

**e) `cola/sequenceeditor.py`** — Anker:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "GIT_FANTA_SEQ_EDITOR" cola/sequenceeditor.py
```

Ersetze beide `core.getenv('GIT_FANTA_SEQ_EDITOR_…', …)` durch
`compat.getenv_with_legacy('GIT_FANTA_SEQ_EDITOR_…', …)`.

> **`cola/cmds.py:2445` ff. bleibt unverändert.** Dort werden die Variablen *gesetzt*, nicht
> gelesen — der Sequence-Editor wird von git-fanta selbst gestartet, also reicht der neue Name.

### Schritt 6.4 (GREEN) — Datei-Fallback für `GIT_FANTA_MSG`

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "GIT_FANTA_MSG" cola/gitcmds.py cola/models/main.py
```

In `cola/gitcmds.py` — ersetze die **gesamte Funktion** `commit_message_path`. Anker:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "def commit_message_path" -A 6 cola/gitcmds.py
```

Neuer Inhalt:

```python
def commit_message_path(context: ApplicationContext) -> str | None:
    """Return the path to .git/GIT_FANTA_MSG, or None when it does not exist

    git-fanta was renamed from git-cola. A pre-rename .git/GIT_COLA_MSG is still
    honored so that a commit message written before the rename is not lost.
    """
    for basename in ('GIT_FANTA_MSG', 'GIT_COLA_MSG'):
        path = context.git.git_path(basename)
        if core.exists(path):
            return path
    return None
```

> Das ist exakt die Form, die `merge_message_path` direkt darunter (`cola/gitcmds.py:992`) für
> `MERGE_MSG`/`SQUASH_MSG` benutzt — gleiche Schleife, gleiche Annotation `str | None`, gleiches
> `return None`. **Der `None`-Rückgabewert ist Pflicht**; die vorhandene Annotation `-> str` war
> falsch und wird hier mitkorrigiert.

**In `cola/models/main.py` ist nichts zu tun** — bewusst geprüft:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "GIT_FANTA_MSG\|commit_message_path" cola/models/main.py
```

**Erwartet:** zwei Treffer.
- `save_commitmsg` (~Zeile 238) **schreibt** und benutzt `self.git.git_path('GIT_FANTA_MSG')`.
  Das ist korrekt so: geschrieben wird immer der neue Name, der Fallback gilt nur fürs Lesen.
  Hier darf **nicht** `commit_message_path()` eingesetzt werden — die Funktion gibt `None`
  zurück, wenn noch keine Datei existiert, und `core.write(None, …)` würde fehlschlagen.
- Zeile ~464 ruft bereits `gitcmds.commit_message_path(self.context)` auf. Der Lese-Pfad ist
  also schon zentralisiert.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/env_rename_test.py test/main_model_test.py
```

**Erwartet:** alle passed.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 15 passed, 0 failed.

> 7 neue Tests in `test/env_rename_test.py`: drei für `getenv_with_legacy`, drei für
> `commit_message_path` (neu / Fallback / `None`) und einer für den Schreibpfad
> `save_commitmsg`.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: benenne GIT_COLA_* in GIT_FANTA_* um, mit Rueckwaerts-Fallback

compat.getenv_with_legacy() liest zuerst den neuen, dann den alten Namen.
.git/GIT_COLA_MSG wird weiterhin gelesen, wenn .git/GIT_FANTA_MSG fehlt."
```

---

## Task 7 — git-config-Keys `cola.*` → `fanta.*` mit Fallback

**Ziel:** Alle ~70 Konfigurationsschlüssel heißen `fanta.*`. Bestehende `cola.*`-Einträge in
`~/.gitconfig` und `.git/config` wirken weiter.

### Schritt 7.1 (RED) — Tests schreiben

Hänge an `test/gitcfg_test.py` an:

```python
def test_new_config_prefix_is_read(app_context):
    """Ein fanta.*-Key wird gelesen."""
    helper.run_git('config', 'fanta.tabwidth', '4')
    app_context.cfg.reset()

    assert app_context.cfg.get('fanta.tabwidth') == 4


def test_legacy_config_prefix_is_still_read(app_context):
    """Ein alter cola.*-Key wirkt weiterhin, wenn kein fanta.*-Key gesetzt ist."""
    helper.run_git('config', 'cola.tabwidth', '8')
    app_context.cfg.reset()

    assert app_context.cfg.get('fanta.tabwidth') == 8


def test_new_config_prefix_wins_over_legacy(app_context):
    """Ist beides gesetzt, gewinnt der neue Key."""
    helper.run_git('config', 'cola.tabwidth', '8')
    helper.run_git('config', 'fanta.tabwidth', '2')
    app_context.cfg.reset()

    assert app_context.cfg.get('fanta.tabwidth') == 2


def test_legacy_config_prefix_is_read_by_get_all(app_context):
    """get_all() beruecksichtigt den alten Prefix ebenfalls."""
    helper.run_git('config', '--add', 'cola.icontheme', 'dark')
    app_context.cfg.reset()

    assert 'dark' in app_context.cfg.get_all('fanta.icontheme')


def test_unknown_key_still_returns_default(app_context):
    """Der Fallback darf nicht dazu fuehren, dass fremde Keys plotzlich treffen."""
    app_context.cfg.reset()

    assert app_context.cfg.get('fanta.doesnotexist', default='x') == 'x'
    assert app_context.cfg.get('other.doesnotexist', default='y') == 'y'
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/gitcfg_test.py 2>&1 | tail -15
```

**Erwartete Fehlermeldung:** `test_legacy_config_prefix_is_still_read` und
`test_legacy_config_prefix_is_read_by_get_all` schlagen fehl mit
`assert None == 8` bzw. `assert 'dark' in []`. Die drei übrigen sind grün.

### Schritt 7.2 (GREEN) — Fallback in `cola/gitcfg.py`

**a) Modulkonstanten + Helfer.** Anker:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^def _append_tab" -B 2 -A 4 cola/gitcfg.py
```

Füge **direkt vor** `class GitConfig(QtCore.QObject):` ein:

```python
# git-fanta was renamed from git-cola. Config keys use the "fanta." prefix. The
# legacy "cola." prefix is still honored so that a pre-rename ~/.gitconfig or
# .git/config keeps working without any migration step.
CONFIG_PREFIX = 'fanta.'
LEGACY_CONFIG_PREFIX = 'cola.'


def legacy_config_key(key: str) -> str | None:
    """Return the pre-rename config key for a "fanta." key, or None"""
    if key.lower().startswith(CONFIG_PREFIX):
        return LEGACY_CONFIG_PREFIX + key[len(CONFIG_PREFIX) :]
    return None
```

**b) `_get_value` ersetzen.** Anker:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "def _get_value" -A 14 cola/gitcfg.py
```

Ersetze die **gesamte Methode** durch:

```python
    def _get_value(self, src: dict[str, ConfigValue], key: str) -> Any:
        """Return a value from the map"""
        for candidate in self._key_candidates(key):
            try:
                return src[candidate]
            except KeyError:
                continue
        # Allow the final KeyError to bubble up
        return src[key.lower()]

    def _key_candidates(self, key: str) -> Iterator[str]:
        """Yield the config keys to probe for `key`, current naming first

        The key is tried as-is, then via the case-preserved name recorded while
        parsing, then lowercased. Only after all three miss do the same three
        variants of the legacy "cola." key get a turn, so a "fanta." key always
        wins over a "cola." key of the same name.
        """
        yield key
        yield self._renamed_keys.get(key.lower(), key)
        yield key.lower()
        legacy = legacy_config_key(key)
        if legacy is not None:
            yield legacy
            yield self._renamed_keys.get(legacy.lower(), legacy)
            yield legacy.lower()
```

> **Reihenfolge ist hier die ganze Semantik.** Das ursprüngliche `_get_value` probierte
> `src[key]`, `src[renamed]`, `src[key.lower()]`. Fehlt in `_key_candidates` das `yield
> key.lower()` **vor** dem Legacy-Block, dann gewinnt ein alter `cola.`-Key gegen einen neuen
> `fanta.`-Key, der nur kleingeschrieben in `src` liegt. Genau das prüft
> `test_new_config_prefix_wins_over_legacy`.

**Kein neuer Import nötig.** `cola/gitcfg.py:8` hat bereits `from collections.abc import Iterator`.
Kontrolliere das einmal und füge **nichts** hinzu:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "import Iterator" cola/gitcfg.py
```

**Erwartet:** `8:from collections.abc import Iterator`

**c) `get_all` erweitern.** Anker:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "Check for a renamed version of this key" -B 6 -A 10 cola/gitcfg.py
```

Ersetze den Block

```python
        # Check for a renamed version of this key (x.kittycat -> x.kittyCat)
        renamed_key = self._renamed_keys.get(key.lower(), key)
        if renamed_key in self._multi_values:
            return self._multi_values[renamed_key]

        key_lower = key.lower()
        if key_lower in self._multi_values:
            return self._multi_values[key_lower]
        # Nothing found -> empty list.
        return []
```

durch

```python
        # Check for a renamed version of this key (x.kittycat -> x.kittyCat) and
        # for the legacy "cola." prefix.
        for candidate in self._key_candidates(key):
            if candidate in self._multi_values:
                return self._multi_values[candidate]

        key_lower = key.lower()
        if key_lower in self._multi_values:
            return self._multi_values[key_lower]
        # Nothing found -> empty list.
        return []
```

### Schritt 7.3 (GREEN) — Key-Tabelle umstellen

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i "s/^\([A-Z_]*\) = 'cola\./\1 = 'fanta./" cola/models/prefs.py && grep -c "= 'fanta\." cola/models/prefs.py && grep -c "= 'cola\." cola/models/prefs.py
```

**Erwartet:** exakt `44` und `0`.

> Der Ausdruck `^\([A-Z_]*\) = 'cola\.` trifft nur Zeilen, die mit einem
> Großbuchstaben-Konstantennamen beginnen. Die Nicht-Fanta-Keys `ABBREV = 'core.abbrev'`,
> `EDITOR = 'gui.editor'`, `USER_EMAIL = 'user.email'` bleiben nachweislich unberührt — das
> wurde an einer Kopie der Datei geprüft.

### Schritt 7.3b (GREEN) — die 34 hartkodierten Keys außerhalb `prefs.py`

> **Das ist der wichtigste Schritt in Task 7.** `prefs.py` ist **nicht** die einzige Quelle der
> Config-Keys. Es gibt **34 weitere hartkodierte `'cola.<key>'`-Literale in 16 Dateien** — u. a.
> `cola/app.py:185` `'cola.icontheme'`, `cola/app.py:669` `'cola.defaultrepo'`,
> `cola/cmds.py:2981` `'cola.safemode'`, `cola/widgets/standard.py:106`
> `'cola.savewindowsettings'`, `cola/qtutils.py:1259` `'cola.dragencoding'`,
> `cola/fsmonitor.py:574` `'cola.inotify'`.
>
> **Warum das gefährlich ist:** Der Fallback aus Schritt 7.2 lässt diese Keys weiterlaufen. Die
> Test-Suite bleibt grün, obwohl 35 Keys weiterhin den alten Prefix lesen. Ohne diesen Schritt
> ist Task 7 unerfüllt und **nichts merkt es**.

Zuerst den Ist-Stand zählen:

```bash
cd /home/hermes-agent/Projects/git-fanta && git grep -Ion "'cola\.[a-z][a-zA-Z0-9_.%]*'" -- cola bin ':(exclude)cola/models/prefs.py' ':(exclude)cola/i18n/*' | wc -l
```

**Erwartet:** `34`.

> Der Ausschluss von `prefs.py` ist wichtig: dessen 44 Keys hat Schritt 7.3 gerade umgestellt.
> Ohne den Ausschluss zählst du je nach Reihenfolge 78 oder 34 und weißt nicht, welche Zahl
> stimmt.

Dann alle auf einmal umstellen:

```bash
cd /home/hermes-agent/Projects/git-fanta && git ls-files -z -- cola bin ':(exclude)cola/i18n/*' | xargs -0 grep -Il '' | xargs sed -i "s/'cola\.\([a-z]\)/'fanta.\1/g"
```

**Danach prüfen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && git grep -Ion "'cola\.[a-z][a-zA-Z0-9_.%]*'" -- cola bin ':(exclude)cola/i18n/*' | wc -l && grep -n "LEGACY_CONFIG_PREFIX" cola/gitcfg.py
```

**Erwartet:** `0` und `LEGACY_CONFIG_PREFIX = 'cola.'` **unverändert**.

> Das Muster verlangt einen **Kleinbuchstaben nach dem Punkt**. `'cola.'` (Punkt direkt gefolgt
> vom schließenden Anführungszeichen) wird deshalb nicht getroffen — an einer Repo-Kopie
> verifiziert: 34 → 0 Literale, `LEGACY_CONFIG_PREFIX` unangetastet, keine Syntaxfehler.
>
> Die 16 betroffenen Dateien: `cola/app.py`, `cola/cmds.py`, `cola/difftool.py`,
> `cola/fsmonitor.py`, `cola/gitcfg.py`, `cola/gitcmds.py`, `cola/guicmds.py`,
> `cola/models/browse.py`, `cola/qtutils.py`, `cola/widgets/bookmarks.py`,
> `cola/widgets/browse.py`, `cola/widgets/commitmsg.py`, `cola/widgets/main.py`,
> `cola/widgets/merge.py`, `cola/widgets/standard.py`, `cola/widgets/startup.py`.
>
> Dieser `sed` erledigt auch `cola/gitcfg.py` (`fileattributes`, `terminal`, `color.%s`) und
> `cola/gitcmds.py` (`preparecommitmessagehook`) mit. Task 8 findet den Key dann bereits als
> `'fanta.preparecommitmessagehook'` vor — das ist so gewollt.

### Schritt 7.3c (GREEN) — bestehende Tests auf den neuen Prefix umstellen

Zwei vorhandene Testdateien schreiben `cola.*`-Keys. Durch den Fallback bleiben sie grün —
und genau deshalb würde **kein einziger Test** verifizieren, dass `fanta.defaultrepo` und
`fanta.color.*` tatsächlich funktionieren.

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "cola\.defaultrepo\|cola\.color" test/startup_test.py test/gitcfg_test.py
```

**Erwartet:** vier Zeilen in `test/startup_test.py` (17, 39, 59, 79) und eine in
`test/gitcfg_test.py` (13).

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i "s/'cola\.defaultrepo'/'fanta.defaultrepo'/g" test/startup_test.py && sed -i "s/'cola\.color\.%s'/'fanta.color.%s'/" test/gitcfg_test.py && grep -n "fanta\.defaultrepo\|fanta\.color" test/startup_test.py test/gitcfg_test.py
```

**Erwartet:** fünf Zeilen, alle mit `fanta.`.

Damit der Legacy-Pfad weiterhin abgedeckt bleibt, hänge an `test/startup_test.py` an:

```python
def test_legacy_default_repo_key_is_still_honored(app_context):
    """Ein vor der Umbenennung gesetztes cola.defaultrepo wirkt weiter."""
    app_context.cfg.set_repo('cola.defaultrepo', '/tmp/legacy-repo')
    app_context.cfg.reset()

    assert app_context.cfg.get('fanta.defaultrepo') == '/tmp/legacy-repo'
```

> **Warum dieser Test nötig ist:** Ohne ihn beweist nach Schritt 7.3c nichts mehr, dass der
> Fallback greift — die alten Tests, die das versehentlich taten, sind ja gerade umgestellt
> worden.

### Schritt 7.3d (RED→GREEN) — die Invariante testbar machen

Damit ein künftiger vergessener `'cola.<key>'`-Literal nicht wieder still durchrutscht, hänge
an `test/rename_guard_test.py` an:

```python
def test_no_legacy_config_key_literals():
    """Kein Quelltext-Literal benutzt mehr den alten cola.-Config-Prefix.

    Der Fallback in cola/gitcfg.py laesst vergessene Keys funktionieren, ohne dass
    ein Test rot wird. Dieser Test ist die einzige Instanz, die sie bemerkt.
    """
    import re

    pattern = re.compile(r"'cola\.[a-z]")
    offenders = []
    for name, text in tracked_text_files():
        if not name.startswith(('cola/', 'bin/')):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f'{name}:{number}: {line.strip()[:100]}')

    assert not offenders, (
        'Diese Literale benutzen noch den alten Config-Prefix:\n' + '\n'.join(offenders)
    )
```

> `LEGACY_CONFIG_PREFIX = 'cola.'` in `cola/gitcfg.py` wird vom Muster nicht getroffen, weil
> nach dem Punkt kein Kleinbuchstabe folgt. Der Test ist nach Schritt 7.3b sofort grün — er ist
> ein **Regressionsschutz**, kein RED-Schritt.

### Schritt 7.4 — Dokumentation der Keys

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -c "cola\." docs/git-fanta.rst
```

Ist die Zahl > 0, benenne die dokumentierten Keys um (nur `cola.<kleinbuchstaben>`, damit
Fließtext unberührt bleibt):

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i 's/\bcola\.\([a-z]\)/fanta.\1/g' docs/git-fanta.rst && grep -c "fanta\." docs/git-fanta.rst
```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/gitcfg_test.py test/settings_test.py 2>&1 | tail -5
```

> Es gibt **kein** `test/prefs_test.py` — die Prefs-Keys sind indirekt über `gitcfg_test.py` und
> die Widget-Tests abgedeckt. Nicht danach suchen.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 22 passed, 0 failed.

> 7 neue Tests in diesem Task: 5 in `test/gitcfg_test.py` (Schritt 7.1),
> `test_legacy_default_repo_key_is_still_honored` in `test/startup_test.py` (7.3c) und
> `test_no_legacy_config_key_literals` in `test/rename_guard_test.py` (7.3d).

**Manueller Smoke-Test — der Fallback in echt:**

```bash
cd /tmp && rm -rf fanta-cfg-probe && mkdir fanta-cfg-probe && cd fanta-cfg-probe && git init -q . && git config cola.tabwidth 8 && cd /home/hermes-agent/Projects/git-fanta && ./env3/bin/python -c "
import os
os.chdir('/tmp/fanta-cfg-probe')
from cola import app, gitcfg, git
ctx = type('C', (), {'git': git.Git()})()
cfg = gitcfg.GitConfig(ctx)
print('fanta.tabwidth ->', cfg.get('fanta.tabwidth'))
"
```

**Erwartet:** `fanta.tabwidth -> 8` (gelesen aus dem alten `cola.tabwidth`).

> Wirft dieser Probe-Aufruf einen Fehler, weil `GitConfig` mehr vom Kontext braucht: den Probe
> überspringen und stattdessen `test_legacy_config_prefix_is_still_read` als Nachweis nehmen.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: benenne die git-config-Keys von cola.* auf fanta.* um

GitConfig._key_candidates() probiert erst den fanta.-Key und faellt dann auf den
alten cola.-Key zurueck, damit bestehende ~/.gitconfig-Eintraege weiterwirken."
```

---

## Task 8 — Commit-Message-Hook umbenennen mit Fallback

**Ziel:** Der Hook heißt `fanta-prepare-commit-msg`. Ein vorhandener
`cola-prepare-commit-msg` wird weiterhin ausgeführt.

### Schritt 8.1 (RED) — Test schreiben

Neue Datei `test/prepare_commit_msg_hook_test.py`:

```python
"""Tests fuer die Umbenennung des prepare-commit-msg-Hooks."""

import os

from cola import gitcmds

from . import helper
from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


def _write_hook(context, name):
    """Lege einen ausfuehrbaren Hook mit dem angegebenen Namen an."""
    path = context.cfg.hooks_path(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    helper.write_file(path, '#!/bin/sh\nexit 0\n')
    os.chmod(path, 0o755)
    return path


def test_prefers_the_new_hook_name(app_context):
    """Existiert der fanta-Hook, wird er benutzt."""
    expect = _write_hook(app_context, 'fanta-prepare-commit-msg')
    app_context.cfg.reset()

    assert gitcmds.prepare_commit_message_hook(app_context) == expect


def test_falls_back_to_the_legacy_hook_name(app_context):
    """Existiert nur der alte cola-Hook, wird dieser benutzt."""
    expect = _write_hook(app_context, 'cola-prepare-commit-msg')
    app_context.cfg.reset()

    assert gitcmds.prepare_commit_message_hook(app_context) == expect


def test_returns_the_new_name_when_no_hook_exists(app_context):
    """Ohne Hook wird der neue Standardpfad zurueckgegeben."""
    app_context.cfg.reset()

    result = gitcmds.prepare_commit_message_hook(app_context)

    assert result.endswith('fanta-prepare-commit-msg')
```

> **Vorher prüfen**, dass `cfg.hooks_path` existiert:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "def hooks_path" -A 6 cola/gitcfg.py
> ```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/prepare_commit_msg_hook_test.py 2>&1 | tail -12
```

**Erwartete Fehlermeldung:** `test_prefers_the_new_hook_name` und
`test_returns_the_new_name_when_no_hook_exists` schlagen fehl, weil der Pfad noch auf
`cola-prepare-commit-msg` endet. `test_falls_back_to_the_legacy_hook_name` ist grün.

### Schritt 8.2 (GREEN)

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "def prepare_commit_message_hook" -A 6 cola/gitcmds.py
```

Ersetze die **gesamte Funktion** durch:

```python
def prepare_commit_message_hook(context: ApplicationContext) -> str:
    """Return the fanta.preparecommitmessagehook to prepare the commit message

    git-fanta was renamed from git-cola. A pre-rename cola-prepare-commit-msg hook
    is still honored when no fanta-prepare-commit-msg hook is installed.
    """
    config = context.cfg
    default_hook = config.hooks_path('fanta-prepare-commit-msg')
    if not core.exists(default_hook):
        legacy_hook = config.hooks_path('cola-prepare-commit-msg')
        if core.exists(legacy_hook):
            default_hook = legacy_hook
    return config.get('fanta.preparecommitmessagehook', default=default_hook)
```

> Prüfe, dass `core` in `cola/gitcmds.py` importiert ist:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "^from . import core\|^from cola import core" cola/gitcmds.py
> ```

### Schritt 8.3 — Log-Ausgaben und Doku

```bash
cd /home/hermes-agent/Projects/git-fanta && git grep -In "cola-prepare-commit-msg" -- cola docs ':(exclude)cola/i18n/*'
```

**Erwartet:** `cola/cmds.py` (zwei Stellen, Docstring + `Interaction.log`), `cola/gitcmds.py`
(die Fallback-Zeile, bleibt), `docs/git-fanta.rst` (zwei Stellen).

Ersetze überall außer der Fallback-Zeile in `gitcmds.py`:

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i 's/cola-prepare-commit-msg/fanta-prepare-commit-msg/g' cola/cmds.py docs/git-fanta.rst && git grep -In "cola-prepare-commit-msg" -- cola docs ':(exclude)cola/i18n/*'
```

**Erwartet:** nur noch die eine Fallback-Zeile in `cola/gitcmds.py`.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 25 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: benenne den prepare-commit-msg-Hook auf fanta-prepare-commit-msg um

Ein vorhandener cola-prepare-commit-msg wird weiterhin ausgefuehrt, wenn kein
fanta-Hook installiert ist."
```

---

## Task 9 — Konfig-Verzeichnis `~/.config/git-fanta` mit Migration

**Ziel:** Neues Verzeichnis `~/.config/git-fanta/`. Bestehende Einstellungen, Sessions, Themes und
Layouts gehen nicht verloren.

Nach Task 2 sagt `cola/resources.py:222` bereits `xdg_config_home('git-fanta', *args)`. Damit
liest git-fanta ein **leeres** Verzeichnis — genau das soll dieser Task verhindern.

### Schritt 9.1 (RED) — Tests schreiben

Neue Datei `test/config_home_migration_test.py`:

```python
"""Tests fuer die Migration von ~/.config/git-cola nach ~/.config/git-fanta."""

import os

from cola import resources


def test_config_home_points_at_git_fanta(monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))

    assert resources.config_home('settings') == str(
        tmp_path / 'git-fanta' / 'settings'
    )


def test_migration_copies_the_legacy_directory(monkeypatch, tmp_path):
    """Existiert nur das alte Verzeichnis, wird es einmalig kopiert."""
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    legacy = tmp_path / 'git-cola'
    legacy.mkdir()
    (legacy / 'settings').write_text('{"recent": []}', encoding='utf-8')

    resources.migrate_config_home()

    assert (tmp_path / 'git-fanta' / 'settings').read_text(
        encoding='utf-8'
    ) == '{"recent": []}'
    # Das alte Verzeichnis bleibt als Sicherheitsnetz liegen.
    assert legacy.is_dir()


def test_migration_does_not_overwrite_an_existing_directory(monkeypatch, tmp_path):
    """Existiert das neue Verzeichnis schon, wird nichts angefasst."""
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    legacy = tmp_path / 'git-cola'
    legacy.mkdir()
    (legacy / 'settings').write_text('alt', encoding='utf-8')
    current = tmp_path / 'git-fanta'
    current.mkdir()
    (current / 'settings').write_text('neu', encoding='utf-8')

    resources.migrate_config_home()

    assert (current / 'settings').read_text(encoding='utf-8') == 'neu'


def test_migration_is_a_noop_without_a_legacy_directory(monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))

    resources.migrate_config_home()

    assert not (tmp_path / 'git-fanta').exists()
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/config_home_migration_test.py 2>&1 | tail -12
```

**Erwartete Fehlermeldung:** `AttributeError: module 'cola.resources' has no attribute 'migrate_config_home'`
für drei Tests. `test_config_home_points_at_git_fanta` ist grün (Charakterisierung von Task 2).

### Schritt 9.2 (GREEN) — Migration in `cola/resources.py`

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "def config_home" -A 4 cola/resources.py
```

Ersetze das Ende der Datei ab `def config_home` durch:

```python
def config_home(*args) -> str:
    """Return git-fanta's configuration directory, e.g. ~/.config/git-fanta"""
    return xdg_config_home(CONFIG_DIRNAME, *args)


def legacy_config_home(*args) -> str:
    """Return the pre-rename configuration directory, e.g. ~/.config/git-cola"""
    return xdg_config_home(LEGACY_CONFIG_DIRNAME, *args)


def migrate_config_home() -> None:
    """Copy a pre-rename ~/.config/git-cola over to ~/.config/git-fanta

    git-fanta was renamed from git-cola. Existing settings, sessions, themes and
    saved layouts are copied once, on the first run after the rename. The legacy
    directory is left in place so that an older git-cola install keeps working and
    so that nothing is lost if the copy is incomplete.
    """
    current = config_home()
    if os.path.exists(current):
        return
    legacy = legacy_config_home()
    if not os.path.isdir(legacy):
        return
    try:
        shutil.copytree(legacy, current)
    except (OSError, shutil.Error):
        # A failed migration must never prevent git-fanta from starting.
        pass
```

Und **oben in der Datei**, direkt nach `_default_icon_theme = 'light'`, ergänzen:

```python
# git-fanta was renamed from git-cola. The configuration directory follows the new
# name; migrate_config_home() carries the old directory over on first run.
CONFIG_DIRNAME = 'git-fanta'
LEGACY_CONFIG_DIRNAME = 'git-cola'
```

Import ergänzen — prüfe:

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "^import " cola/resources.py
```

Füge `import shutil` alphabetisch zwischen `import os` und `import sys` ein.

### Schritt 9.3 (GREEN) — Migration aufrufen

Sie muss laufen, **bevor** `find_git()` auf `config_home('git-bindir')` zugreift.

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "def initialize" -A 8 cola/app.py
```

Füge als **erste Anweisung** in `initialize()` ein, direkt nach dem Docstring
`"""System-level initialization"""`:

```python
    # git-fanta was renamed from git-cola: carry ~/.config/git-cola over once.
    resources.migrate_config_home()
```

> Prüfe, dass `resources` in `cola/app.py` importiert ist:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "import resources" cola/app.py
> ```

### Schritt 9.4 (GREEN) — Direktzugriffe in `guicmds.py` beseitigen (Falle F8)

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "xdg_config_home('git-fanta'" cola/guicmds.py
```

**Erwartet:** drei Treffer.

Ersetze jedes `resources.xdg_config_home('git-fanta', 'layouts')` durch
`resources.config_home('layouts')`:

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i "s/resources\.xdg_config_home('git-fanta', /resources.config_home(/g" cola/guicmds.py && grep -n "config_home\|xdg_config_home" cola/guicmds.py
```

**Erwartet:** nur noch `resources.config_home(...)`-Aufrufe.

> Der dritte Treffer (`cola/guicmds.py:478`) ist ein mehrzeiliger Aufruf. Prüfe ihn danach von
> Hand und stelle sicher, dass die Klammerung stimmt — `garden fmt` in der Verifikation fängt
> Formatfehler, aber keine falsche Semantik.

### Schritt 9.5 (GREEN) — Lese-Fallback für die settings-Datei

Zusätzlich zur Verzeichnis-Migration bekommt die `settings`-Datei denselben Lese-Fallback, den
das Projekt bereits für `~/.cola` hat (Vorbild: `cola/settings.py:276-284`).

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "We couldn't find" -B 6 -A 12 cola/settings.py
```

Ersetze

```python
        else:
            # We couldn't find ~/.config/git-fanta, try ~/.cola
            values = {}
            path = os.path.join(core.expanduser('~'), '.cola')
```

durch

```python
        else:
            # We couldn't find ~/.config/git-fanta. Try the pre-rename
            # ~/.config/git-cola first, then the much older ~/.cola.
            values = {}
            path = resources.legacy_config_home('settings')
            if not core.exists(path):
                path = os.path.join(core.expanduser('~'), '.cola')
```

> Prüfe, dass `resources` in `cola/settings.py` importiert ist:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && grep -n "import resources" cola/settings.py
> ```

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/config_home_migration_test.py test/settings_test.py test/resources_test.py
```

**Erwartet:** alle passed.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 29 passed, 0 failed.

**Manueller Smoke-Test — Migration in echt:**

```bash
rm -rf /tmp/fanta-xdg && mkdir -p /tmp/fanta-xdg/git-cola && echo '{"recent": []}' > /tmp/fanta-xdg/git-cola/settings && cd /home/hermes-agent/Projects/git-fanta && XDG_CONFIG_HOME=/tmp/fanta-xdg ./env3/bin/python -c "
from cola import resources
resources.migrate_config_home()
print(open('/tmp/fanta-xdg/git-fanta/settings').read())
"
```

**Erwartet:** `{"recent": []}`.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "feat: migriere ~/.config/git-cola nach ~/.config/git-fanta

Einmalige Kopie beim ersten Start, das alte Verzeichnis bleibt liegen. Die
settings-Datei bekommt zusaetzlich einen Lese-Fallback nach dem Muster, das
settings.py bereits fuer ~/.cola benutzt. guicmds.py greift nicht mehr direkt
auf xdg_config_home() zu, damit die gespeicherten Layouts mitwandern."
```

---

## Task 10 — Übersetzungen

**Ziel:** Die 8 nutzersichtbaren `msgid`-Strings mit „cola" tragen den neuen Namen, `git-cola.pot`
heißt `git-fanta.pot`.

> **Was hier *nicht* passiert:** Die 20592 `#: cola/…`-Quellreferenzen bleiben, weil das
> Python-Paket `cola` heißt. Die `msgstr`-Übersetzungen werden nicht angefasst — sie werden bei
> der nächsten Übersetzungsrunde nachgezogen; bis dahin greift der gettext-Fallback auf den
> englischen `msgid` zurück. Das ist kein Bruch.

### Schritt 10.1 (RED) — Test schreiben

Hänge an `test/rename_guard_test.py` an:

```python
def test_translation_template_uses_the_new_product_name():
    """Die nutzersichtbaren msgid-Strings tragen den neuen Produktnamen."""
    pot = REPO_ROOT / 'cola' / 'i18n' / 'git-fanta.pot'
    assert pot.is_file(), 'cola/i18n/git-fanta.pot fehlt'

    msgids = [
        line
        for line in pot.read_text(encoding='utf-8').splitlines()
        if line.startswith('msgid')
    ]
    offenders = [line for line in msgids if 'cola' in line.lower()]

    assert not offenders, 'msgid-Strings tragen noch den alten Namen:\n' + '\n'.join(
        offenders
    )
```

**RED ausführen:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/rename_guard_test.py::test_translation_template_uses_the_new_product_name 2>&1 | tail -6
```

**Erwartete Fehlermeldung:** `AssertionError: cola/i18n/git-fanta.pot fehlt`

### Schritt 10.2 (GREEN) — Quellstrings anpassen

Die 8 betroffenen `msgid`-Strings stammen aus `N_()`-Aufrufen im Quellcode. Nach Task 2 sind
sechs davon bereits umbenannt. Übrig sind die mit **kleingeschriebenem, freistehendem** „cola".

**Anker:**

```bash
cd /home/hermes-agent/Projects/git-fanta && git grep -In "N_('.*cola\|N_(\".*cola\|already exists, cola" -- cola ':(exclude)cola/i18n/*'
```

**Erwartet:** die Stelle `'"%s" already exists, cola will create a new directory'`.

```bash
cd /home/hermes-agent/Projects/git-fanta && sed -i 's/already exists, cola will create/already exists, fanta will create/' $(git grep -Il "already exists, cola will create" -- cola ':(exclude)cola/i18n/*') && git grep -In "already exists, " -- cola ':(exclude)cola/i18n/*'
```

> **Erwartet:** der Treffer liegt in `cola/widgets/clone.py`.
>
> Findet der `git grep` nichts, ist `$(...)` leer und `sed -i` bricht mit
> `sed: no input files` und Exit-Code 4 ab — es **hängt nicht**. Das bedeutet dann, dass der
> String schon ersetzt wurde: mit dem nachfolgenden `git grep` kontrollieren und weitergehen.

Prüfe, dass keine weiteren freistehenden „cola"-Strings in `N_()` stecken:

```bash
cd /home/hermes-agent/Projects/git-fanta && git grep -Ion "N_([^)]*[Cc]ola[^)]*)" -- cola ':(exclude)cola/i18n/*'
```

**Erwartet:** keine Ausgabe.

### Schritt 10.3 (GREEN) — Template umbenennen und neu erzeugen

```bash
cd /home/hermes-agent/Projects/git-fanta && git mv cola/i18n/git-cola.pot cola/i18n/git-fanta.pot
```

Neu erzeugen — bevorzugt über garden:

```bash
cd /home/hermes-agent/Projects/git-fanta && garden pot
```

Falls `garden` oder `xgettext` fehlen, ist das der Fallback (`xgettext` kommt aus `gettext`):

```bash
cd /home/hermes-agent/Projects/git-fanta && xgettext --language=Python --keyword=N_ --no-wrap --omit-header --output-dir cola/i18n --output git-fanta.pot cola/*.py cola/*/*.py
```

> Ist `xgettext` nicht installierbar, **überspringe die Neuerzeugung** und passe stattdessen nur
> die 8 `msgid`-Zeilen im vorhandenen `git-fanta.pot` mit `sed` an:
> ```bash
> cd /home/hermes-agent/Projects/git-fanta && sed -i -e '/^msgid/s/git-cola/git-fanta/g' -e '/^msgid/s/git cola/git fanta/g' -e '/^msgid/s/exists, cola will/exists, fanta will/' -e '/^msgid/s/"cola\.inotify"/"fanta.inotify"/' cola/i18n/git-fanta.pot
> ```
> **Melde in diesem Fall**, dass die Quellreferenzen im `.pot` veraltet sind.

### Schritt 10.4 — `.po`-Dateien mit dem neuen Template abgleichen

```bash
cd /home/hermes-agent/Projects/git-fanta && garden po
```

Falls `msgmerge` fehlt: **diesen Schritt überspringen und melden.** Die `.po`-Dateien bleiben
dann auf dem alten Stand; gettext fällt für die 8 geänderten Strings auf den englischen `msgid`
zurück. Das ist funktional korrekt, nur unübersetzt.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/i18n_test.py test/rename_guard_test.py
```

**Erwartet:** alle passed.

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 30 passed, 0 failed.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "chore: benenne das Uebersetzungstemplate und die msgid-Strings um

Die #:-Quellreferenzen zeigen weiterhin auf cola/, weil das Python-Paket
unveraendert cola heisst."
```

---

## Task 11 — Projekt-Dokumentation für Agenten aktualisieren

**Ziel:** `.claude/skills/project-brief/` beschreibt nach der Umbenennung noch den alten Zustand
und würde jede künftige Sitzung in die Irre führen.

### Schritt 11.1 — Betroffene Stellen finden

```bash
cd /home/hermes-agent/Projects/git-fanta && git grep -In -i "cola" -- .claude
```

### Schritt 11.2 — `SKILL.md` korrigieren

Der einleitende Absatz behauptet aktuell das Gegenteil des neuen Zustands. Ersetze in
`.claude/skills/project-brief/SKILL.md` den Absatz

```
A fork of **git-cola**, the Qt desktop GUI for Git. Upstream naming is untouched — the Python
package is `cola`, `pyproject.toml` still says `git-cola`, and only the remote
(`hermes-agent-ak/git-fanta`) and the working directory carry the fork name. Do not "fix" that.
```

durch

```
A fork of git-cola, the Qt desktop GUI for Git, renamed to **git-fanta**. Everything
user-facing carries the fork name: the `git-fanta` executable, the `git fanta` subcommand,
`fanta.*` git-config keys, `GIT_FANTA_*` environment variables and `~/.config/git-fanta`.
The Python package is still `cola` (`import cola`, `cola/`) and `[tool.setuptools] packages`
names it — that is deliberate, do not "fix" it. References to the upstream project
(github.com/git-cola/git-cola, `brew install git-cola`, `CHANGES.rst`, the remotes in
`garden.yaml`) are also deliberate and must stay. See
`docs/plans/2026-07-30-rename-to-git-fanta.md`.
```

> **Die Formulierungen sind hier nicht frei wählbar.** Der Wächter-Test aus Task 2 scannt
> `.claude/` mit. Jede Zeile, die den alten Produktnamen trägt, braucht einen Marker aus §3 B:
> - Zeile 1 sagt **`A fork of git-cola`** (ohne Sternchen um den Namen!) — das trifft den Marker
>   `'fork of git-cola'`. Schreibt man `**git-cola**`, passt der Marker nicht mehr und der Test
>   wird rot.
> - Die Zeile mit `github.com/git-cola/git-cola` trägt den URL-Marker.
> - Der Plandateiname enthält **kein** `git-cola` mehr (siehe §0) — deshalb ist die letzte Zeile
>   unkritisch.
>
> Empirisch geprüft: mit dieser Fassung meldet `test_product_name_is_git_fanta` keinen Treffer.

### Schritt 11.3 — Launcher- und Befehlsangaben korrigieren

```bash
cd /home/hermes-agent/Projects/git-fanta && grep -n "bin/\|git-cola\|git-dag" .claude/skills/project-brief/SKILL.md
```

Die Zeile über `bin/` muss lauten:

```
| `bin/` | Launchers: `git-fanta`, `git-dag`, `git-fanta-sequence-editor` |
```

### Schritt 11.4 — Neue Falle in `gotchas.md` aufnehmen

Hänge an `.claude/skills/project-brief/references/gotchas.md` an:

```markdown
## git-fanta ist renamed from git-cola — das hat vier stille Kanten

1. `cola/widgets/toolbar.py:253` löst Icon-Namen über `getattr(icons, name, None)` auf, und
   `cola/widgets/toolbarcmds.py:283`/`:285` setzen `'icon': 'cola'`. `icons.cola()` umzubenennen
   entfernt das Icon lautlos — kein Fehler, kein Log. Deshalb heißt die Funktion weiterhin
   `cola()`, obwohl die Datei `git-fanta.svg` heißt.
2. `cola/version.py` fragt `metadata.version('git-fanta')`. Der String muss dem `name` in
   `pyproject.toml` entsprechen, sonst fällt die Versionsanzeige still auf den Builtin-Wert
   zurück. `test/rename_guard_test.py::test_distribution_name_matches_pyproject` bewacht das.
3. `.github/workflows/ci.yml` installiert per `brew install git-cola` die echte Homebrew-Formel
   als Abhängigkeit des macOS-Jobs. Diese Zeile ist kein Rename-Rückstand.
4. Die git-config-Keys heißen `fanta.*`, `cola/gitcfg.py` liest den alten `cola.`-Prefix aber
   weiter als Fallback. Das heißt: ein vergessener `'cola.irgendwas'`-Literal im Code fällt
   **nicht** durch einen roten Test auf. `test_no_legacy_config_key_literals` in
   `test/rename_guard_test.py` ist die einzige Instanz, die das bemerkt.
```

> Die Überschrift benutzt bewusst die Wendung **`renamed from git-cola`** — das ist einer der
> beiden Prosa-Marker aus §3 B. Ohne ihn wird der Wächter-Test rot.

### Verifikation

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q test/rename_guard_test.py
```

**Erwartet:** alle passed — insbesondere `test_product_name_is_git_fanta`, weil `.claude/` nicht
ausgenommen ist und die Datei jetzt keine unerlaubten `git-cola`-Vorkommen mehr haben darf.

> Schlägt der Test hier fehl, listet er die verbliebenen Zeilen in `.claude/` auf. Diese Zeilen
> von Hand nachziehen — Ausnahme: Zeilen, die bewusst das Upstream-Projekt nennen, brauchen einen
> der Marker aus §3 B in derselben Zeile.

### Commit

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "docs: aktualisiere den project-brief auf den git-fanta-Namensstand"
```

---

## Task 12 — Alle CI-Gates lokal durchlaufen

**Ziel:** Nichts bleibt der CI überlassen.

### Schritte

```bash
cd /home/hermes-agent/Projects/git-fanta && garden check/fmt
```

**Erwartet:** keine Änderungsvorschläge.

```bash
cd /home/hermes-agent/Projects/git-fanta && garden check/pyupgrade
```

**Erwartet:** keine Ausgabe.

```bash
cd /home/hermes-agent/Projects/git-fanta && garden check/mypy
```

**Erwartet:** `Success` oder dieselbe Fehlerzahl wie vor Task 1. **Neue** mypy-Fehler müssen
behoben werden — am wahrscheinlichsten in `cola/gitcfg.py` (`Iterator`-Import) und
`cola/resources.py` (`shutil`).

```bash
cd /home/hermes-agent/Projects/git-fanta && ./env3/bin/python -m ruff check test/rename_guard_test.py test/env_rename_test.py test/config_home_migration_test.py test/prepare_commit_msg_hook_test.py
```

**Erwartet:** `All checks passed!`

**Qt-Bindings-Matrix wie in der CI:**

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_API=pyqt5 QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

```bash
cd /home/hermes-agent/Projects/git-fanta && QT_API=pyqt6 QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen ./env3/bin/python -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

> Ist PyQt6 nicht installiert, wird dieser Lauf mit einem Import-Fehler abbrechen. Das ist dann
> **kein** Rename-Problem — melden und weitermachen.

**Sphinx-Build (prüft, ob `docs/git-fanta.rst` korrekt verlinkt ist):**

```bash
cd /home/hermes-agent/Projects/git-fanta && garden doc/html 2>&1 | tail -10
```

**Erwartet:** `build succeeded`. Warnungen über fehlende Referenzen auf `git-cola` deuten auf
einen übersehenen Verweis — dann `docs/` durchsuchen und nachziehen.

**Vollständiger manueller Smoke-Test:**

```bash
cd /home/hermes-agent/Projects/git-fanta && ./env3/bin/python ./bin/git-fanta version && ./env3/bin/python ./bin/git-dag --count 5 --help && ./env3/bin/python ./bin/git-fanta-sequence-editor --help
```

**Erwartet:** drei Mal saubere Ausgabe, kein Traceback.

**Und die App wirklich starten** (falls ein Display verfügbar ist):

```bash
cd /home/hermes-agent/Projects/git-fanta && garden run
```

Prüfen: Fenstertitel enthält „Git Fanta", `Hilfe → Über` zeigt „Git Fanta", das Fenster-Icon ist
da (das prüft Falle **F3** — ist das Icon weg, wurde `icons.cola()` doch angefasst).

### Commit

Nur falls die Gates Änderungen erzwungen haben:

```bash
cd /home/hermes-agent/Projects/git-fanta && git add -A && git commit -m "style: wende garden fmt nach der Umbenennung an"
```

---

## Task 13 — Plan abschließen

Ergänze am **Anfang** dieser Datei den Frontmatter-Block und trage die tatsächlichen Werte ein:

```yaml
---
status: completed
completed_at: <YYYY-MM-DD>
plan_commit: <sha des plan:-Commits>
implementation_branch: renaming/opus5/plan
implementation_head: <sha des letzten Commits>
ci_run: <URL des CI-Laufs oder "nicht ausgefuehrt">
manual_verification: |
  - ./bin/git-fanta version --brief
  - App gestartet, Titel und About zeigen "Git Fanta", Fenster-Icon vorhanden
  - cola.tabwidth aus einer alten .gitconfig wird als fanta.tabwidth gelesen
  - ~/.config/git-cola wurde nach ~/.config/git-fanta migriert
---
```

```bash
cd /home/hermes-agent/Projects/git-fanta && git add docs/plans/2026-07-30-rename-to-git-fanta.md && git commit -m "plan: markiere die git-fanta-Umbenennung als abgeschlossen"
```

---

## Abschluss-Checkliste

| # | Prüfung | Befehl |
|---|---|---|
| 1 | Kein `git-cola` außerhalb der Ausnahmen | `pytest -q test/rename_guard_test.py` |
| 2 | Keine Datei heißt mehr `git-cola*` | im selben Test enthalten |
| 3 | Upstream-Referenzen intakt | im selben Test enthalten |
| 4 | Volle Suite grün | `pytest -q cola test` |
| 5 | `fmt`, `pyupgrade`, `mypy` grün | `garden check/fmt check/pyupgrade check/mypy` |
| 6 | pyqt5- und pyqt6-Lauf grün | `QT_API=… pytest -q cola test` |
| 7 | Sphinx baut | `garden doc/html` |
| 8 | App startet, Titel + Icon korrekt | `garden run` |
| 9 | Alter `cola.*`-Config-Key wirkt | `test_legacy_config_prefix_is_still_read` |
| 10 | Alte `GIT_COLA_*`-Variable wirkt | `test_getenv_falls_back_to_legacy_name` |
| 11 | Alter Hook wirkt | `test_falls_back_to_the_legacy_hook_name` |
| 12 | Altes Konfig-Verzeichnis wandert mit | `test_migration_copies_the_legacy_directory` |

## Was dieser Plan bewusst offenlässt

- **Das Python-Paket heißt weiter `cola`.** Ein späterer Stufe-3-Schritt wäre ein eigener Plan:
  125 Import-Zeilen in 41 Dateien, `[tool.setuptools] packages`, die mypy- und garden-Pfade und
  eine komplette Neuerzeugung der `.po`-Quellreferenzen.
- **Die `msgstr`-Übersetzungen** nennen in 8 Strings weiter „cola". Das ist ein
  Übersetzungsthema, kein Funktionsfehler.
- **`icons.cola()`** behält den alten Namen (Falle **F3**). Wer das ändern will, muss
  `cola/widgets/toolbarcmds.py:283` und `:285` im **selben** Commit mitziehen.
- **Kein Kompatibilitäts-Symlink `git-cola` → `git-fanta`** wird installiert. Wer das braucht,
  legt ihn selbst an; im Repo würde er den Wächter-Test brechen.
