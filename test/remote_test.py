from unittest.mock import Mock
from unittest.mock import patch

from cola.widgets import remote


class FakeCheckbox:
    def __init__(self, checked):
        self.checked = checked

    def isChecked(self):
        return self.checked

    def setChecked(self, value):
        self.checked = value


class DummyPushDialog:
    def __init__(self):
        self.UPSTREAM_STATE_KEY = 'upstream'
        self.context = Mock()
        self.context.settings = Mock()
        self.context.settings.get_value.return_value = None
        self.force_checkbox = FakeCheckbox(False)
        self.prompt_checkbox = FakeCheckbox(True)
        self.tags_checkbox = FakeCheckbox(False)
        self.upstream_checkbox = FakeCheckbox(False)
        self.name = Mock(return_value='push')


def test_push_export_state_remembers_upstream_when_enabled():
    dialog = DummyPushDialog()
    dialog.upstream_checkbox.setChecked(True)
    with (
        patch.object(remote.RemoteActionDialog, 'export_state', return_value={}),
        patch(
            'cola.widgets.remote.prefs.remember_push_tracking_checkbox',
            return_value=True,
        ),
    ):
        state = remote.Push.export_state(dialog)
    assert state['upstream'] is True


def test_push_export_state_does_not_remember_upstream_when_disabled():
    dialog = DummyPushDialog()
    dialog.upstream_checkbox.setChecked(True)
    with (
        patch.object(remote.RemoteActionDialog, 'export_state', return_value={}),
        patch(
            'cola.widgets.remote.prefs.remember_push_tracking_checkbox',
            return_value=False,
        ),
    ):
        state = remote.Push.export_state(dialog)
    assert 'upstream' not in state


def test_push_apply_state_restores_upstream_when_enabled():
    dialog = DummyPushDialog()
    dialog.context.settings.get_value.return_value = None
    with (
        patch.object(remote.RemoteActionDialog, 'apply_state', return_value=True),
        patch(
            'cola.widgets.remote.prefs.remember_push_tracking_checkbox',
            return_value=True,
        ),
    ):
        result = remote.Push.apply_state(dialog, {'upstream': True})
    assert result is True
    assert dialog.upstream_checkbox.isChecked() is True


def test_push_apply_state_prefers_settings_value_when_enabled():
    dialog = DummyPushDialog()
    dialog.context.settings.get_value.return_value = True
    with (
        patch.object(remote.RemoteActionDialog, 'apply_state', return_value=True),
        patch(
            'cola.widgets.remote.prefs.remember_push_tracking_checkbox',
            return_value=True,
        ),
    ):
        result = remote.Push.apply_state(dialog, {'upstream': False})
    assert result is True
    assert dialog.upstream_checkbox.isChecked() is True


def test_push_apply_state_ignores_upstream_when_disabled():
    dialog = DummyPushDialog()
    dialog.upstream_checkbox.setChecked(False)
    with (
        patch.object(remote.RemoteActionDialog, 'apply_state', return_value=True),
        patch(
            'cola.widgets.remote.prefs.remember_push_tracking_checkbox',
            return_value=False,
        ),
    ):
        result = remote.Push.apply_state(dialog, {'upstream': True})
    assert result is True
    assert dialog.upstream_checkbox.isChecked() is False


def test_push_remember_action_state_saves_when_enabled():
    dialog = DummyPushDialog()
    dialog.upstream_checkbox.setChecked(True)
    with patch(
        'cola.widgets.remote.prefs.remember_push_tracking_checkbox',
        return_value=True,
    ):
        remote.Push.remember_action_state(dialog)
    dialog.context.settings.set_value.assert_called_once_with('push', 'upstream', True)


def test_push_remember_action_state_does_nothing_when_disabled():
    dialog = DummyPushDialog()
    with patch(
        'cola.widgets.remote.prefs.remember_push_tracking_checkbox',
        return_value=False,
    ):
        remote.Push.remember_action_state(dialog)
    dialog.context.settings.set_value.assert_not_called()
