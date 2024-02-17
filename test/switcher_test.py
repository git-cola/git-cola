"""Test Quick Switcher"""
from cola import icons
from cola.widgets import switcher


def test_switcher_item_with_only_key():
    """item text would be key by building item without name"""
    key = 'item-key'
    actual = switcher.switcher_item(key)

    assert actual.key == key
    assert actual.text() == key


def test_switcher_item_with_key_name_icon():
    """item text would be name by building item with key and name"""
    key = 'item-key'
    name = 'item-name'
    icon = icons.folder()

    actual = switcher.switcher_item(key, icon, name)

    assert actual.key == key
    assert actual.text() == name
