from unittest.mock import Mock
from unittest.mock import patch

from cola.widgets import remote


class FakeCheckbox:
    def __init__(self, checked):
        self.checked = checked
        self.blocked = False

    def isChecked(self):
        return self.checked

    def setChecked(self, value):
        self.checked = value

    def blockSignals(self, value):
        previous = self.blocked
        self.blocked = value
        return previous


class DummyPushDialog:
    def __init__(self):
        self.remember_upstream_checkbox_state = False
        self.context = Mock()
        self.force_checkbox = FakeCheckbox(False)
        self.prompt_checkbox = FakeCheckbox(True)
        self.tags_checkbox = FakeCheckbox(False)
        self.upstream_checkbox = FakeCheckbox(False)


def test_push_export_state_remembers_upstream_when_enabled():
    dialog = DummyPushDialog()
    dialog.remember_upstream_checkbox_state = True
    dialog.upstream_checkbox.setChecked(True)
    with patch.object(remote.RemoteActionDialog, 'export_state', return_value={}):
        state = remote.Push.export_state(dialog)
    assert state['set_upstream_branch']


def test_push_export_state_omits_upstream_when_not_remembered():
    dialog = DummyPushDialog()
    dialog.remember_upstream_checkbox_state = False
    dialog.upstream_checkbox.setChecked(True)
    with patch.object(remote.RemoteActionDialog, 'export_state', return_value={}):
        state = remote.Push.export_state(dialog)
    assert 'set_upstream_branch' not in state


def test_push_apply_state_restores_upstream_when_remembered():
    dialog = DummyPushDialog()
    with patch.object(remote.RemoteActionDialog, 'apply_state', return_value=True):
        result = remote.Push.apply_state(dialog, {'set_upstream_branch': True})
    assert result
    assert dialog.remember_upstream_checkbox_state
    assert dialog.upstream_checkbox.isChecked()


def test_push_apply_state_does_not_restore_upstream_when_not_remembered():
    dialog = DummyPushDialog()
    dialog.upstream_checkbox.setChecked(False)
    with patch.object(remote.RemoteActionDialog, 'apply_state', return_value=True):
        result = remote.Push.apply_state(dialog, {})
    assert result
    assert not dialog.remember_upstream_checkbox_state
    assert not dialog.upstream_checkbox.isChecked()


def test_upstream_checkbox_toggled_disabling_clears_remember_state():
    dialog = DummyPushDialog()
    dialog.remember_upstream_checkbox_state = True
    with patch('cola.widgets.remote.Interaction.confirm') as confirm:
        remote.Push.upstream_checkbox_toggled(dialog, False)
    assert not dialog.remember_upstream_checkbox_state
    confirm.assert_not_called()


def test_upstream_checkbox_toggled_enabling_prompts_to_remember():
    dialog = DummyPushDialog()
    with (
        patch('cola.widgets.remote.icons.question', return_value=None),
        patch('cola.widgets.remote.Interaction.confirm', return_value=True) as confirm,
    ):
        remote.Push.upstream_checkbox_toggled(dialog, True)
    assert dialog.remember_upstream_checkbox_state
    confirm.assert_called_once()


def test_upstream_checkbox_toggled_enabling_keeps_one_time_behavior():
    dialog = DummyPushDialog()
    with (
        patch('cola.widgets.remote.icons.question', return_value=None),
        patch(
            'cola.widgets.remote.Interaction.confirm',
            return_value=False,
        ) as confirm,
    ):
        remote.Push.upstream_checkbox_toggled(dialog, True)
    assert not dialog.remember_upstream_checkbox_state
    confirm.assert_called_once()


def test_upstream_checkbox_toggled_enabling_skips_prompt_when_remembered():
    dialog = DummyPushDialog()
    dialog.remember_upstream_checkbox_state = True
    with patch('cola.widgets.remote.Interaction.confirm') as confirm:
        remote.Push.upstream_checkbox_toggled(dialog, True)
    confirm.assert_not_called()
