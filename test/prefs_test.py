from cola.models import prefs

from . import helper
from .helper import app_context


# prevent unused imports lint errors.
assert app_context is not None


def test_remember_push_tracking_checkbox_default(app_context):
    assert prefs.remember_push_tracking_checkbox(app_context) is False


def test_remember_push_tracking_checkbox_enabled(app_context):
    helper.run_git('config', 'cola.rememberpushtrackingcheckbox', 'true')
    app_context.cfg.reset()
    assert prefs.remember_push_tracking_checkbox(app_context) is True
