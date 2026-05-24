import argparse
import sys
import types
from unittest.mock import MagicMock

from cola import app
from qtpy import QtCore


def test_setup_environment():
    # If the function doesn't throw an exception we are happy.
    assert hasattr(app, 'setup_environment')
    app.setup_environment()


def test_add_common_arguments():
    # If the function doesn't throw an exception we are happy.
    parser = argparse.ArgumentParser()
    assert hasattr(app, 'add_common_arguments')
    app.add_common_arguments(parser)


def test_set_application_name_sets_qt_application_name():
    """The Qt application name is set unconditionally on every platform."""
    app._set_application_name()
    assert QtCore.QCoreApplication.applicationName() == 'Git Cola'


class _ExplodingAppKit(types.ModuleType):
    """Stand-in module whose attribute access always fails.

    Used to assert that the code under test does NOT reach the AppKit
    branch -- if it does, the test fails with a clear AssertionError.
    """

    def __init__(self):
        super().__init__('AppKit')

    def __getattr__(self, name):
        raise AssertionError(f'AppKit.{name} accessed unexpectedly')


def test_set_application_name_is_a_noop_on_non_darwin(monkeypatch):
    """On non-darwin platforms the Cocoa surfaces are never touched."""
    monkeypatch.setattr(sys, 'platform', 'linux')
    monkeypatch.setitem(sys.modules, 'AppKit', _ExplodingAppKit())

    # Must not raise, must not touch AppKit.
    app._set_application_name()
    assert QtCore.QCoreApplication.applicationName() == 'Git Cola'


def test_set_application_name_survives_missing_appkit(monkeypatch):
    """If PyObjC isn't installed, the function returns without crashing."""
    monkeypatch.setattr(sys, 'platform', 'darwin')
    # Force `from AppKit import ...` inside the function to raise ImportError
    # by stashing a non-module object under that key.
    monkeypatch.setitem(sys.modules, 'AppKit', None)

    # Must not raise.
    app._set_application_name()
    assert QtCore.QCoreApplication.applicationName() == 'Git Cola'


def _make_fake_appkit():
    """Build a fake AppKit module that captures every Cocoa write we make."""
    fake_info = {}
    info_dict = MagicMock()
    info_dict.setObject_forKey_.side_effect = lambda value, key: fake_info.__setitem__(
        key, value
    )

    bundle = MagicMock()
    bundle.localizedInfoDictionary.return_value = None
    bundle.infoDictionary.return_value = info_dict

    ns_bundle = MagicMock()
    ns_bundle.mainBundle.return_value = bundle

    process_info_instance = MagicMock()
    ns_process_info = MagicMock()
    ns_process_info.processInfo.return_value = process_info_instance

    module = types.ModuleType('AppKit')
    module.NSBundle = ns_bundle
    module.NSProcessInfo = ns_process_info
    return module, fake_info, process_info_instance


def test_set_application_name_patches_cocoa_surfaces_on_darwin(monkeypatch):
    """On darwin we set CFBundleName, CFBundleDisplayName, and processName."""
    monkeypatch.setattr(sys, 'platform', 'darwin')
    fake_appkit, captured_info, process_info_instance = _make_fake_appkit()
    monkeypatch.setitem(sys.modules, 'AppKit', fake_appkit)

    app._set_application_name()

    assert captured_info == {
        'CFBundleName': 'Git Cola',
        'CFBundleDisplayName': 'Git Cola',
    }
    process_info_instance.setProcessName_.assert_called_once_with('Git Cola')


def test_set_application_name_swallows_cocoa_exceptions(monkeypatch):
    """A failure inside the Cocoa block must not crash app startup.

    The function is best-effort -- it intentionally swallows any AppKit
    exception because a cosmetic naming failure must not prevent git-cola
    from launching.
    """
    monkeypatch.setattr(sys, 'platform', 'darwin')
    fake_appkit, _captured_info, _process_info = _make_fake_appkit()
    # Make every NSBundle call blow up.
    fake_appkit.NSBundle.mainBundle.side_effect = RuntimeError('boom')
    monkeypatch.setitem(sys.modules, 'AppKit', fake_appkit)

    # Must not raise.
    app._set_application_name()
    # Qt-side name still got set despite the AppKit explosion.
    assert QtCore.QCoreApplication.applicationName() == 'Git Cola'
