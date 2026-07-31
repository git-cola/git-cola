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
    """Wie in test/widgets_main_history_test.py: mit strip()."""
    return subprocess.run(
        ('git', *args), check=True, text=True, capture_output=True
    ).stdout.strip()


def _repo_with_topic(context):
    """Zwei Commits, zwei Branches, HEAD auf main."""
    _git('commit', '-m', 'base')
    base_oid = _git('rev-parse', 'HEAD')
    _git('checkout', '-b', 'topic')
    _git('commit', '--allow-empty', '-m', 'topic')
    topic_oid = _git('rev-parse', 'HEAD')
    _git('checkout', 'main')
    context.model.update_status()
    return base_oid, topic_oid


def _fake_commit(oid, branches=(), tags=()):
    """Ein Commit-Stellvertreter mit genau den Feldern, die die Regel liest."""
    commit = dag.Commit(None, dag.CommitFactory(), oid=oid)
    commit.summary = 'summary'
    commit.author = 'A U Thor'
    commit.authdate = '2026-07-31'
    commit.branches = list(branches)
    commit.tags = list(tags)
    return commit


@pytest.fixture
def checkout_context(app_context):
    """app_context plus das eine Attribut, das cmds.Command.do() numerisch vergleicht."""
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
