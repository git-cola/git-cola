"""Tests DAG functionality"""
from unittest.mock import patch

import pytest

from cola.models import dag
from cola.widgets.dag import _prepare_labels

from .helper import app_context
from .helper import commit_files

# Prevent unused imports lint errors.
assert app_context is not None


LOG_TEXT = """
23e7eab4ba2c94e3155f5d261c693ccac1342eb9^Af4fb8fd5baaa55d9b41faca79be289bb4407281e^A^ADavid Aguilar^AThu Dec 6 18:59:20 2007 -0800^Adavvid@gmail.com^AMerged diffdisplay into main
f4fb8fd5baaa55d9b41faca79be289bb4407281e^Ae3f5a2d0248de6197d6e0e63c901810b8a9af2f8^A^ADavid Aguilar^ATue Dec 4 03:14:56 2007 -0800^Adavvid@gmail.com^ASquashed commit of the following:
e3f5a2d0248de6197d6e0e63c901810b8a9af2f8^Afa5ad6c38be603e2ffd1f9b722a3a5c675f63de2^A^ADavid Aguilar^AMon Dec 3 02:36:06 2007 -0800^Adavvid@gmail.com^AMerged qlistwidgets into main.
103766573cd4e6799d3ee792bcd632b92cf7c6c0^Afa5ad6c38be603e2ffd1f9b722a3a5c675f63de2^A^ADavid Aguilar^ATue Dec 11 05:13:21 2007 -0800^Adavvid@gmail.com^AAdded TODO
fa5ad6c38be603e2ffd1f9b722a3a5c675f63de2^A1ba04ad185cf9f04c56c8482e9a73ef1bd35c695^A^ADavid Aguilar^AFri Nov 30 05:19:05 2007 -0800^Adavvid@gmail.com^AAvoid multiple signoffs
1ba04ad185cf9f04c56c8482e9a73ef1bd35c695^Aad454b189fe5785af397fd6067cf103268b6626e^A^ADavid Aguilar^AFri Nov 30 05:07:47 2007 -0800^Adavvid@gmail.com^Aupdated model/view/controller api
ad454b189fe5785af397fd6067cf103268b6626e^A^A (tag: refs/tags/v0.0)^ADavid Aguilar^AFri Nov 30 00:03:28 2007 -0800^Adavvid@gmail.com^Afirst cut of ugit
""".strip().replace(  # noqa
    '^A', chr(0x01)
)
LOG_LINES = LOG_TEXT.split('\n')


class DAGTestData:
    """Test data provided by the dag_context fixture"""

    def __init__(self, app_context, head='HEAD', count=1000):
        self.context = app_context
        self.params = dag.DAG(head, count)
        self.reader = dag.RepoReader(app_context, self.params)


@pytest.fixture
def dag_context(app_context):
    """Provide DAGTestData for use by tests"""
    return DAGTestData(app_context)


def _log_entry(oid, parents=""):
    fields = (oid, parents, "", "Author", "Date", "author@example.com", oid)
    return dag.LOGSEP.join(fields)


def test_repo_readers_isolate_interleaved_commit_graphs(app_context):
    shared_oid = "1" * 40
    parent_a_oid = "a" * 40
    parent_b_oid = "b" * 40
    output_a = "\n".join(
        (_log_entry(shared_oid, parent_a_oid), _log_entry(parent_a_oid))
    )
    output_b = "\n".join(
        (_log_entry(shared_oid, parent_b_oid), _log_entry(parent_b_oid))
    )
    reader_a = dag.RepoReader(app_context, dag.DAG("reader-a", 2), allow_git_init=False)
    reader_b = dag.RepoReader(app_context, dag.DAG("reader-b", 2), allow_git_init=False)

    with (
        patch(
            "cola.models.dag.core.run_command",
            side_effect=((0, output_a, ""), (0, output_b, "")),
        ),
        patch("cola.models.dag.prefs.logdate", return_value="default"),
    ):
        commits_a = reader_a.get()
        parent_a = next(commits_a)
        commits_b = list(reader_b.get())
        commits_a = [parent_a, *commits_a]

    tip_a = reader_a[shared_oid]
    tip_b = reader_b[shared_oid]
    parent_b = reader_b[parent_b_oid]
    assert tip_a is commits_a[1]
    assert tip_b is commits_b[1]
    assert tip_a is not tip_b
    assert tip_a.parents == [parent_a]
    assert tip_b.parents == [parent_b]
    assert parent_a is not parent_b
    assert parent_a.children == [tip_a]
    assert parent_b.children == [tip_b]
    assert reader_a.factory is not reader_b.factory
    assert reader_a.factory.commits is not reader_b.factory.commits


def test_repo_reader_reset_discards_objects_and_changed_input(app_context):
    shared_oid = "1" * 40
    parent_a_oid = "a" * 40
    parent_b_oid = "b" * 40
    output_a = "\n".join(
        (_log_entry(shared_oid, parent_a_oid), _log_entry(parent_a_oid))
    )
    output_b = "\n".join(
        (_log_entry(shared_oid, parent_b_oid), _log_entry(parent_b_oid))
    )
    reader = dag.RepoReader(app_context, dag.DAG("history", 2), allow_git_init=False)

    with (
        patch(
            "cola.models.dag.core.run_command",
            side_effect=((0, output_a, ""), (0, output_b, "")),
        ),
        patch("cola.models.dag.prefs.logdate", return_value="default"),
    ):
        list(reader.get())
        first_tip = reader[shared_oid]
        first_parent = reader[parent_a_oid]

        reader.reset()

        assert reader._objects == {}
        assert reader._topo_list == []
        assert reader._top_commit is None
        assert reader.factory.commits == {}
        assert reader.factory.root_generation == 0
        assert reader.cached is False

        list(reader.get())

    second_tip = reader[shared_oid]
    second_parent = reader[parent_b_oid]
    assert second_tip is not first_tip
    assert second_parent is not first_parent
    assert second_tip.parents == [second_parent]
    assert first_tip.parents == [first_parent]


def test_repo_reader_preserves_command_error(app_context):
    reader = dag.RepoReader(app_context, dag.DAG("history", 2), allow_git_init=False)

    with (
        patch(
            "cola.models.dag.core.run_command",
            return_value=(128, "", "fatal: bad revision"),
        ),
        patch("cola.models.dag.prefs.logdate", return_value="default"),
    ):
        assert list(reader.get()) == []

    assert reader.returncode == 128
    assert reader.error == "fatal: bad revision"


def test_repo_reader_success_clears_previous_command_error(app_context):
    reader = dag.RepoReader(app_context, dag.DAG("history", 2), allow_git_init=False)

    with (
        patch(
            "cola.models.dag.core.run_command",
            side_effect=(
                (128, "", "fatal: bad revision"),
                (0, "", ""),
            ),
        ),
        patch("cola.models.dag.prefs.logdate", return_value="default"),
    ):
        list(reader.get())
        reader.reset()
        list(reader.get())

    assert reader.returncode == 0
    assert reader.error == ""


def test_repo_reader_reset_clears_previous_command_error(app_context):
    reader = dag.RepoReader(app_context, dag.DAG("history", 2), allow_git_init=False)

    with (
        patch(
            "cola.models.dag.core.run_command",
            return_value=(128, "", "fatal: bad revision"),
        ),
        patch("cola.models.dag.prefs.logdate", return_value="default"),
    ):
        list(reader.get())

    reader.reset()

    assert reader.returncode == 0
    assert reader.error == ""



def test_repo_reader_isolates_overlapping_runs(app_context):
    shared_oid = "1" * 40
    parent_a_oid = "a" * 40
    parent_b_oid = "b" * 40
    output_a = "\n".join(
        (_log_entry(shared_oid, parent_a_oid), _log_entry(parent_a_oid))
    )
    output_b = "\n".join(
        (_log_entry(shared_oid, parent_b_oid), _log_entry(parent_b_oid))
    )
    reader = dag.RepoReader(app_context, dag.DAG("history", 2), allow_git_init=False)

    with (
        patch(
            "cola.models.dag.core.run_command",
            side_effect=((11, output_a, "old error"), (12, output_b, "new error")),
        ),
        patch("cola.models.dag.prefs.logdate", return_value="default"),
    ):
        old_commits = reader.get()
        old_parent = next(old_commits)
        old_factory = reader.factory

        new_commits = reader.get()
        new_parent = next(new_commits)
        new_factory = reader.factory
        new_tip = next(new_commits)
        with pytest.raises(StopIteration):
            next(new_commits)

        old_tip = next(old_commits)
        with pytest.raises(StopIteration):
            next(old_commits)

    assert old_factory is not new_factory
    assert old_tip.parents == [old_parent]
    assert old_parent.children == [old_tip]
    assert new_tip.parents == [new_parent]
    assert new_parent.children == [new_tip]
    assert old_tip is not new_tip
    assert reader.factory is new_factory
    assert reader._objects == {
        parent_b_oid: new_parent,
        shared_oid: new_tip,
    }
    assert reader._topo_list == [new_parent, new_tip]
    assert reader._top_commit is new_tip
    assert reader.cached is True
    assert reader.returncode == 12
    assert reader.error == "new error"


def test_repo_reader_reset_does_not_mutate_partial_run(app_context):
    tip_oid = "1" * 40
    parent_oid = "a" * 40
    output = "\n".join((_log_entry(tip_oid, parent_oid), _log_entry(parent_oid)))
    reader = dag.RepoReader(app_context, dag.DAG("history", 2), allow_git_init=False)

    with (
        patch(
            "cola.models.dag.core.run_command", return_value=(0, output, "")
        ),
        patch("cola.models.dag.prefs.logdate", return_value="default"),
    ):
        commits = reader.get()
        parent = next(commits)
        old_factory = reader.factory
        old_objects = reader._objects
        old_topo_list = reader._topo_list

        reader.reset()

        assert reader.factory is not old_factory
        assert reader._objects is not old_objects
        assert reader._topo_list is not old_topo_list
        assert reader.factory.commits == {}
        assert reader._objects == {}
        assert reader._topo_list == []
        assert reader._top_commit is None
        assert reader.cached is False

        tip = next(commits)
        with pytest.raises(StopIteration):
            next(commits)

    assert old_objects == {parent_oid: parent, tip_oid: tip}
    assert old_topo_list == [parent, tip]
    assert tip.parents == [parent]
    assert parent.children == [tip]
    assert reader.factory.commits == {}
    assert reader._objects == {}
    assert reader._topo_list == []
    assert reader._top_commit is None
    assert reader.cached is False


def test_repo_reader_publishes_command_status_before_first_yield(app_context):
    tip_oid = "1" * 40
    parent_oid = "a" * 40
    output = "\n".join((_log_entry(tip_oid, parent_oid), _log_entry(parent_oid)))
    reader = dag.RepoReader(app_context, dag.DAG("history", 2), allow_git_init=False)

    with (
        patch(
            "cola.models.dag.core.run_command",
            return_value=(17, output, "command failed"),
        ),
        patch("cola.models.dag.prefs.logdate", return_value="default"),
    ):
        commits = reader.get()
        next(commits)

    assert reader.returncode == 17
    assert reader.error == "command failed"
    assert reader.cached is False
    assert reader._top_commit is None


def test_repo_reader_keeps_command_status_after_processing_exception(app_context):
    tip_oid = "1" * 40
    parent_oid = "a" * 40
    output = "\n".join((_log_entry(tip_oid, parent_oid), _log_entry(parent_oid)))
    reader = dag.RepoReader(app_context, dag.DAG("history", 2), allow_git_init=False)

    with (
        patch(
            "cola.models.dag.core.run_command",
            return_value=(17, output, "command failed"),
        ),
        patch("cola.models.dag.prefs.logdate", return_value="default"),
    ):
        commits = reader.get()
        next(commits)
        with (
            patch.object(reader.factory, "new", side_effect=RuntimeError("boom")),
            pytest.raises(RuntimeError, match="boom"),
        ):
            next(commits)

    assert reader.returncode == 17
    assert reader.error == "command failed"
    assert reader.cached is False
    assert reader._top_commit is None


@patch('cola.models.dag.core')
def test_repo_reader(core, dag_context):
    commit_files()
    dag_context.context.model.update_status()
    expect = len(LOG_LINES)
    actual = 0
    core.run_command.return_value = (0, LOG_TEXT, '')
    for idx, _ in enumerate(dag_context.reader.get()):
        actual += 1

    assert expect == actual


@patch('cola.models.dag.core')
def test_repo_reader_order(core, dag_context):
    commits = [
        'ad454b189fe5785af397fd6067cf103268b6626e',
        '1ba04ad185cf9f04c56c8482e9a73ef1bd35c695',
        'fa5ad6c38be603e2ffd1f9b722a3a5c675f63de2',
        '103766573cd4e6799d3ee792bcd632b92cf7c6c0',
        'e3f5a2d0248de6197d6e0e63c901810b8a9af2f8',
        'f4fb8fd5baaa55d9b41faca79be289bb4407281e',
        '23e7eab4ba2c94e3155f5d261c693ccac1342eb9',
    ]
    core.run_command.return_value = (0, LOG_TEXT, '')
    for idx, commit in enumerate(dag_context.reader.get()):
        assert commits[idx] == commit.oid


@patch('cola.models.dag.core')
def test_repo_reader_parents(core, dag_context):
    parents = [
        [],
        ['ad454b189fe5785af397fd6067cf103268b6626e'],
        ['1ba04ad185cf9f04c56c8482e9a73ef1bd35c695'],
        ['fa5ad6c38be603e2ffd1f9b722a3a5c675f63de2'],
        ['fa5ad6c38be603e2ffd1f9b722a3a5c675f63de2'],
        ['e3f5a2d0248de6197d6e0e63c901810b8a9af2f8'],
        ['f4fb8fd5baaa55d9b41faca79be289bb4407281e'],
    ]
    core.run_command.return_value = (0, LOG_TEXT, '')
    for idx, commit in enumerate(dag_context.reader.get()):
        assert parents[idx] == [p.oid for p in commit.parents]


@patch('cola.models.dag.core')
def test_repo_reader_contract(core, dag_context):
    commit_files()
    dag_context.context.model.update_status()
    core.exists.return_value = True
    core.run_command.return_value = (0, LOG_TEXT, '')

    for idx, _ in enumerate(dag_context.reader.get()):
        pass

    core.run_command.assert_called()
    call_args = core.run_command.call_args

    assert 'log.abbrevCommit=false' in call_args[0][0]
    assert 'log.showSignature=false' in call_args[0][0]


def test_prepare_labels_single_remote_no_condensing():
    refs = ['remotes/origin/main']
    assert _prepare_labels(refs) == [
        ('remotes/origin/main', 'origin/main', None),
    ]


def test_prepare_labels_two_remotes_same_branch():
    refs = ['remotes/origin/main', 'remotes/myremote/main']
    assert _prepare_labels(refs) == [
        ('remotes/myremote/main', 'myremote/main', 'myremote/\u2026'),
        ('remotes/origin/main', 'origin/main', None),
    ]


def test_prepare_labels_three_remotes_same_branch():
    refs = ['remotes/origin/main', 'remotes/open/main', 'remotes/myremote/main']
    assert _prepare_labels(refs) == [
        ('remotes/myremote/main', 'myremote/main', 'myremote/\u2026'),
        ('remotes/open/main', 'open/main', 'open/\u2026'),
        ('remotes/origin/main', 'origin/main', None),
    ]


def test_prepare_labels_mixed_refs():
    refs = [
        'HEAD',
        'remotes/origin/main',
        'remotes/myremote/main',
        'heads/main',
        'tags/v1.0',
    ]
    assert _prepare_labels(refs) == [
        ('tags/v1.0', 'v1.0', None),
        ('remotes/myremote/main', 'myremote/main', 'myremote/\u2026'),
        ('remotes/origin/main', 'origin/main', 'origin/\u2026'),
        ('heads/main', 'main', None),
    ]


def test_prepare_labels_single_remote_with_local():
    refs = ['remotes/origin/main', 'heads/main']
    assert _prepare_labels(refs) == [
        ('remotes/origin/main', 'origin/main', 'origin/\u2026'),
        ('heads/main', 'main', None),
    ]


def test_prepare_labels_different_branch_names_no_condensing():
    refs = ['remotes/origin/main', 'remotes/origin/develop']
    assert _prepare_labels(refs) == [
        ('remotes/origin/develop', 'origin/develop', None),
        ('remotes/origin/main', 'origin/main', None),
    ]


def test_prepare_labels_multiple_groups():
    refs = [
        'remotes/origin/main',
        'remotes/myremote/main',
        'remotes/origin/feat',
        'remotes/myremote/feat',
    ]
    assert _prepare_labels(refs) == [
        ('remotes/myremote/feat', 'myremote/feat', 'myremote/\u2026'),
        ('remotes/origin/feat', 'origin/feat', None),
        ('remotes/myremote/main', 'myremote/main', 'myremote/\u2026'),
        ('remotes/origin/main', 'origin/main', None),
    ]


def test_prepare_labels_empty():
    assert _prepare_labels([]) == []


def test_prepare_labels_no_remotes():
    refs = ['HEAD', 'heads/main', 'tags/v1.0']
    assert _prepare_labels(refs) == [
        ('tags/v1.0', 'v1.0', None),
        ('heads/main', 'main', None),
    ]


def test_prepare_labels_two_groups_with_locals():
    refs = [
        'remotes/origin/main',
        'remotes/myremote/main',
        'heads/main',
        'remotes/origin/feat',
        'heads/feat',
    ]
    assert _prepare_labels(refs) == [
        ('remotes/origin/feat', 'origin/feat', 'origin/\u2026'),
        ('heads/feat', 'feat', None),
        ('remotes/myremote/main', 'myremote/main', 'myremote/\u2026'),
        ('remotes/origin/main', 'origin/main', 'origin/\u2026'),
        ('heads/main', 'main', None),
    ]
