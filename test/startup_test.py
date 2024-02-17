"""Test Startup Dialog (git cola --prompt) Context Menu and related classes"""
from cola.widgets import startup

from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


def test_get_with_default_repo(app_context):
    """Test BuildItem::get for default repo"""
    path = '/home/foo/git-cola'
    name = 'git-cola'
    mode = startup.ICON_MODE
    is_bookmark = True

    app_context.cfg.set_repo('cola.defaultrepo', path)
    builder = startup.BuildItem(app_context)

    actual = builder.get(path, name, mode, is_bookmark)

    assert actual.path == path
    assert actual.name == name
    assert actual.mode == startup.ICON_MODE
    assert actual.is_default
    assert actual.is_bookmark
    assert actual.text() == name
    assert actual.isEditable()


def test_get_with_non_default_repo(app_context):
    """Test BuildItem::get for non-default repo"""
    default_repo_path = '/home/foo/default_repo'
    path = '/home/foo/git-cola'
    name = 'git-cola'
    mode = startup.ICON_MODE
    is_bookmark = True

    app_context.cfg.set_repo('cola.defaultrepo', default_repo_path)
    builder = startup.BuildItem(app_context)

    actual = builder.get(path, name, mode, is_bookmark)

    assert actual.path == path
    assert actual.name == name
    assert not actual.is_default
    assert actual.is_bookmark == is_bookmark
    assert actual.text() == name
    assert actual.isEditable()


def test_get_with_item_from_recent(app_context):
    """Test BuildItem::get for repository from recent list"""
    path = '/home/foo/git-cola'
    name = 'git-cola'
    mode = startup.ICON_MODE
    is_bookmark = False

    app_context.cfg.set_repo('cola.defaultrepo', path)
    builder = startup.BuildItem(app_context)

    actual = builder.get(path, name, mode, is_bookmark)

    assert actual.path == path
    assert actual.name == name
    assert actual.is_default
    assert not actual.is_bookmark
    assert actual.text() == name
    assert actual.isEditable()


def test_get_with_list_mode(app_context):
    """Test BuildItem::get for list mode building"""
    path = '/home/foo/git-cola'
    name = 'git-cola'
    mode = startup.LIST_MODE
    is_bookmark = True

    app_context.cfg.set_repo('cola.defaultrepo', path)
    builder = startup.BuildItem(app_context)

    actual = builder.get(path, name, mode, is_bookmark)

    assert actual.path == path
    assert actual.name == name
    assert actual.is_default
    assert actual.is_bookmark
    assert actual.text() == path
    assert not actual.isEditable()
