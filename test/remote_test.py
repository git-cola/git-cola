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
        self.REMEMBER_UPSTREAM_STATE_KEY = 'remember_upstream'
        self.UPSTREAM_STATE_KEY = 'upstream'
        self._remember_upstream_checkbox = False
        self.context = Mock()
        self.force_checkbox = FakeCheckbox(False)
        self.prompt_checkbox = FakeCheckbox(True)
        self.tags_checkbox = FakeCheckbox(False)
        self.upstream_checkbox = FakeCheckbox(False)


def test_push_export_state_remembers_upstream_when_enabled():
    dialog = DummyPushDialog()
    dialog._remember_upstream_checkbox = True
    dialog.upstream_checkbox.setChecked(True)
    with patch.object(remote.RemoteActionDialog, 'export_state', return_value={}):
        state = remote.Push.export_state(dialog)
    assert state['remember_upstream'] is True
    assert state['upstream'] is True


def test_push_export_state_omits_upstream_when_not_remembered():
    dialog = DummyPushDialog()
    dialog._remember_upstream_checkbox = False
    dialog.upstream_checkbox.setChecked(True)
    with patch.object(remote.RemoteActionDialog, 'export_state', return_value={}):
        state = remote.Push.export_state(dialog)
    assert state['remember_upstream'] is False
    assert 'upstream' not in state


def test_push_apply_state_restores_upstream_when_remembered():
    dialog = DummyPushDialog()
    with patch.object(remote.RemoteActionDialog, 'apply_state', return_value=True):
        result = remote.Push.apply_state(
            dialog, {'remember_upstream': True, 'upstream': True}
        )
    assert result is True
    assert dialog._remember_upstream_checkbox is True
    assert dialog.upstream_checkbox.isChecked() is True


def test_push_apply_state_does_not_restore_upstream_when_not_remembered():
    dialog = DummyPushDialog()
    dialog.upstream_checkbox.setChecked(False)
    with patch.object(remote.RemoteActionDialog, 'apply_state', return_value=True):
        result = remote.Push.apply_state(
            dialog, {'remember_upstream': False, 'upstream': True}
        )
    assert result is True
    assert dialog._remember_upstream_checkbox is False
    assert dialog.upstream_checkbox.isChecked() is False


def test_upstream_checkbox_toggled_disabling_clears_remember_state():
    dialog = DummyPushDialog()
    dialog._remember_upstream_checkbox = True
    with patch('cola.widgets.remote.Interaction.confirm') as confirm:
        remote.Push.upstream_checkbox_toggled(dialog, False)
    assert dialog._remember_upstream_checkbox is False
    confirm.assert_not_called()


def test_upstream_checkbox_toggled_enabling_prompts_to_remember():
    dialog = DummyPushDialog()
    with (
        patch('cola.widgets.remote.icons.question', return_value=None),
        patch('cola.widgets.remote.Interaction.confirm', return_value=True) as confirm,
    ):
        remote.Push.upstream_checkbox_toggled(dialog, True)
    assert dialog._remember_upstream_checkbox is True
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
    assert dialog._remember_upstream_checkbox is False
    confirm.assert_called_once()


def test_upstream_checkbox_toggled_enabling_skips_prompt_when_remembered():
    dialog = DummyPushDialog()
    dialog._remember_upstream_checkbox = True
    with patch('cola.widgets.remote.Interaction.confirm') as confirm:
        remote.Push.upstream_checkbox_toggled(dialog, True)
    confirm.assert_not_called()
