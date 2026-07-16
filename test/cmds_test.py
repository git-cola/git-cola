"""Test the cmds module"""
import time
from unittest.mock import Mock
from unittest.mock import patch

from cola import cmds
from cola.widgets import revert


def test_Commit_strip_comments():
    """Ensure that commit messages are stripped of comments"""
    msg = 'subject\n\n#comment\nbody'
    expect = 'subject\n\nbody\n'
    actual = cmds.Commit.strip_comments(msg)
    assert expect == actual


def test_commit_strip_comments_unicode():
    """Ensure that unicode is preserved in stripped commit messages"""
    msg = chr(0x1234) + '\n\n#comment\nbody'
    expect = chr(0x1234) + '\n\nbody\n'
    actual = cmds.Commit.strip_comments(msg)
    assert expect == actual


def test_unix_path_win32():
    path = r'Z:\Program Files\git-cola\bin\git-dag'
    expect = '/Z/Program Files/git-cola/bin/git-dag'
    actual = cmds.unix_path(path, is_win32=lambda: True)
    assert expect == actual


def test_unix_path_network_win32():
    path = r'\\Z\Program Files\git-cola\bin\git-dag'
    expect = '//Z/Program Files/git-cola/bin/git-dag'
    actual = cmds.unix_path(path, is_win32=lambda: True)
    assert expect == actual


def test_unix_path_is_a_noop_on_sane_platforms():
    path = r'/:we/don\t/need/no/stinking/badgers!'
    expect = path
    actual = cmds.unix_path(path, is_win32=lambda: False)
    assert expect == actual


def test_revert_dialog_summary_contains_file_and_line_counts():
    diff_text = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1,2 @@
-old
+new
+line
"""

    summary = revert.summarize_changes(diff_text, ['README.md'])

    assert summary['file_count'] == 1
    assert summary['changed_lines'] == 3
    assert summary['added_lines'] == 2
    assert summary['removed_lines'] == 1


def test_context_edit_command():
    context = Mock()
    context.timestamp = time.time()
    model = context.model

    cmd = cmds.EditModel(context)
    cmd.new_diff_text = 'test_diff_text'
    cmd.new_diff_type = 'test_diff_type'
    cmd.new_mode = 'test_mode'
    cmd.new_filename = 'test_filename'
    cmd.do()

    model.set_diff_text.assert_called_once_with('test_diff_text')
    model.set_diff_type.assert_called_once_with('test_diff_type')
    model.set_mode.assert_called_once_with('test_mode')
    assert model.filename == 'test_filename'


@patch('cola.interaction.Interaction.confirm')
def test_submodule_add(confirm):
    # "git submodule" should not be called if the answer is "no"
    context = Mock()
    url = 'url'
    path = ''
    reference = ''
    branch = ''
    depth = 0
    cmd = cmds.SubmoduleAdd(context, url, path, branch, depth, reference)

    confirm.return_value = False
    cmd.do()
    assert not context.git.submodule.called

    expect = ['--', 'url']
    actual = cmd.get_args()
    assert expect == actual

    cmd.path = 'path'
    expect = ['--', 'url', 'path']
    actual = cmd.get_args()
    assert expect == actual

    cmd.reference = 'ref'
    expect = ['--reference', 'ref', '--', 'url', 'path']
    actual = cmd.get_args()
    assert expect == actual

    cmd.branch = 'branch'
    expect = ['--branch', 'branch', '--reference', 'ref', '--', 'url', 'path']
    actual = cmd.get_args()
    assert expect == actual

    cmd.reference = ''
    cmd.branch = ''
    cmd.depth = 1
    expect = ['--depth', '1', '--', 'url', 'path']
    actual = cmd.get_args()
    assert expect == actual

    # Run the command and assert that "git submodule" was called.
    confirm.return_value = True
    context.cfg.get = Mock(return_value=1)
    context.git.submodule.return_value = (0, '', '')
    cmd.do()
    context.git.submodule.assert_called_once_with('add', *expect)
    assert context.model.update_file_status.called
    assert context.model.update_submodules_list.called


@patch('cola.version.check_git')
@patch('cola.interaction.Interaction.confirm')
def test_submodule_update(confirm, check_git):
    context = Mock()
    path = 'sub/path'
    update_path_cmd = cmds.SubmoduleUpdate(context, path)
    update_all_cmd = cmds.SubmodulesUpdate(context)

    # Nothing is called when confirm() returns False.
    confirm.return_value = False

    update_path_cmd.do()
    assert not context.git.submodule.called

    update_all_cmd.do()
    assert not context.git.submodule.called

    # Confirm command execution.
    confirm.return_value = True

    # Test the old command-line arguments first
    check_git.return_value = False

    expect = ['update', '--', 'sub/path']
    actual = update_path_cmd.get_args()
    assert expect == actual

    context.model.update_file_status = Mock()
    context.cfg.get = Mock(return_value=1)
    context.git.submodule = Mock(return_value=(0, '', ''))
    update_path_cmd.do()
    context.git.submodule.assert_called_once_with(*expect)
    assert context.model.update_file_status.called

    expect = ['update']
    actual = update_all_cmd.get_args()
    assert expect == actual

    context.model.update_file_status = Mock()
    context.git.submodule = Mock(return_value=(0, '', ''))
    update_all_cmd.do()
    context.git.submodule.assert_called_once_with(*expect)
    assert context.model.update_file_status.called

    # Test the new command-line arguments (git v1.6.5+)
    check_git.return_value = True

    expect = ['update', '--recursive', '--', 'sub/path']
    actual = update_path_cmd.get_args()
    assert expect == actual

    context.model.update_file_status = Mock()
    context.git.submodule = Mock(return_value=(0, '', ''))
    update_path_cmd.do()
    context.git.submodule.assert_called_once_with(*expect)
    assert context.model.update_file_status.called

    expect = ['update', '--recursive']
    actual = update_all_cmd.get_args()
    assert expect == actual

    context.model.update_file_status = Mock()
    context.git.submodule = Mock(return_value=(0, '', ''))
    update_all_cmd.do()
    context.git.submodule.assert_called_once_with(*expect)
    assert context.model.update_file_status.called


@patch('cola.cmds.Interaction')
@patch('cola.cmds.prefs')
def test_undo_last_commit_confirms_action(prefs, interaction):
    """Test the behavior around confirmation of UndoLastCommit actions"""
    context = Mock()
    context.model = Mock()
    # First, test what happens when the commit is published and we say "yes".
    prefs.check_published_commits = Mock(return_value=True)
    context.model.is_commit_published = Mock(return_value=True)
    interaction.confirm = Mock(return_value=True)

    cmd = cmds.UndoLastCommit(context)
    assert cmd.confirm()
    context.model.is_commit_published.assert_called_once()
    interaction.confirm.assert_called_once()

    # Now, test what happens when we say "no".
    interaction.confirm = Mock(return_value=False)
    assert not cmd.confirm()
    interaction.confirm.assert_called_once()

    # Now check what happens when the commit is published but our preferences
    # say to not check for published commits.
    prefs.check_published_commits = Mock(return_value=False)
    context.model.is_commit_published = Mock(return_value=True)
    interaction.confirm = Mock(return_value=True)

    assert cmd.confirm()
    context.model.is_commit_published.assert_not_called()
    interaction.confirm.assert_called_once()

    # Lastly, check what when the commit is not published and we do check
    # for published commits.
    prefs.check_published_commits = Mock(return_value=True)
    context.model.is_commit_published = Mock(return_value=False)
    interaction.confirm = Mock(return_value=True)

    assert cmd.confirm()
    context.model.is_commit_published.assert_called_once()
    interaction.confirm.assert_called_once()


@patch('cola.widgets.revert.RevertConfirmDialog')
def test_revert_unstaged_edits_confirm(mock_dialog):
    context = Mock()
    context.model.head = 'HEAD'

    selection = Mock()
    selection.staged = ['staged_file.txt']
    selection.modified = ['modified_file.txt']

    cmd = cmds.RevertUnstagedEdits(context)
    cmd.selection = Mock()
    cmd.selection.selection = Mock(return_value=selection)

    cmd.get_diff_output = Mock(return_value='diff_output')

    mock_dialog.return_value.exec.return_value = 1
    mock_dialog.Accepted = 1

    assert cmd.confirm()

    mock_dialog.assert_called_once_with(
        context,
        cmds.N_('Revert Unstaged Changes?'),
        cmds.N_(
            'This operation removes unstaged edits from selected files.\n'
            'These changes cannot be recovered.'
        ),
        'diff_output',
        ['staged_file.txt'],
    )


@patch('cola.widgets.revert.RevertConfirmDialog')
def test_revert_unstaged_edits_confirm_unstaged_only(mock_dialog):
    context = Mock()
    context.model.head = 'HEAD'

    selection = Mock()
    selection.staged = []
    selection.modified = ['modified_file.txt']

    cmd = cmds.RevertUnstagedEdits(context)
    cmd.selection = Mock()
    cmd.selection.selection = Mock(return_value=selection)

    cmd.get_diff_output = Mock(return_value='diff_output')

    mock_dialog.return_value.exec.return_value = 1
    mock_dialog.Accepted = 1

    assert cmd.confirm()

    mock_dialog.assert_called_once_with(
        context,
        cmds.N_('Revert Unstaged Changes?'),
        cmds.N_(
            'This operation removes unstaged edits from selected files.\n'
            'These changes cannot be recovered.'
        ),
        'diff_output',
        ['modified_file.txt'],
    )
