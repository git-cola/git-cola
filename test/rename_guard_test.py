"""Wächter-Tests für die Umbenennung git-fanta -> git-fanta.

Zwei Invarianten werden hier festgeschrieben:

1. Verweise auf das Upstream-Projekt (github.com/git-cola/git-cola und Freunde)
   bleiben unverändert, weil sie auf ein echtes, weiterhin existierendes Projekt
   zeigen.
2. Der Produktname "git-fanta" kommt sonst nirgends mehr in den versionierten
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
    'fork of git-fanta',
    'renamed from git-fanta',
)

# Diese Dateien und Praefixe werden komplett ausgespart.
EXEMPT_FILES = frozenset({'CHANGES.rst', 'garden.yaml', 'test/rename_guard_test.py'})
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


def test_product_name_is_git_fanta():
    """Der alte Produktname kommt ausserhalb der Upstream-Verweise nicht mehr vor."""
    offenders = []
    for name, text in tracked_text_files():
        for number, line in enumerate(text.splitlines(), start=1):
            if any(marker in line for marker in UPSTREAM_MARKERS):
                continue
            if any(legacy in line for legacy in LEGACY_PRODUCT_NAMES):
                offenders.append(f'{name}:{number}: {line.strip()[:100]}')

    assert (
        not offenders
    ), f'{len(offenders)} Zeilen tragen noch den alten Produktnamen:\n' + '\n'.join(
        offenders[:40]
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

    assert not offenders, 'Diese Dateien muessen umbenannt werden:\n' + '\n'.join(
        offenders
    )
