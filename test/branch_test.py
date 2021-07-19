"""Tests related to the branches widget"""
from __future__ import absolute_import, division, print_function, unicode_literals

from cola.widgets import branch

from .helper import Mock


def test_create_tree_entries():
    names = [
        'abc',
        'cat/abc',
        'cat/def',
        'xyz/xyz',
    ]
    root = branch.create_tree_entries(names)
    expect = 3
    actual = len(root.children)
    assert expect == actual

    # 'abc'
    abc = root.children[0]
    expect = 'abc'
    actual = abc.basename
    assert expect == actual
    expect = 'abc'
    actual = abc.refname
    assert expect == actual
    expect = []
    actual = abc.children
    assert expect == actual

    # 'cat'
    cat = root.children[1]
    expect = 'cat'
    actual = 'cat'
    assert expect == actual
    assert cat.refname is None
    expect = 2
    actual = len(cat.children)
    assert expect == actual

    # 'cat/abc'
    cat_abc = cat.children[0]
    expect = 'abc'
    actual = cat_abc.basename
    assert expect == actual
    expect = 'cat/abc'
    actual = cat_abc.refname
    assert expect == actual
    expect = []
    actual = cat_abc.children
    assert expect == actual

    # 'cat/def'
    cat_def = cat.children[1]
    expect = 'def'
    actual = cat_def.basename
    assert expect == actual
    expect = 'cat/def'
    actual = cat_def.refname
    assert expect == actual
    expect = []
    actual = cat_def.children
    assert expect == actual

    # 'xyz'
    xyz = root.children[2]
    expect = 'xyz'
    actual = xyz.basename
    assert expect == actual
    assert xyz.refname is None
    expect = 1
    actual = len(xyz.children)
    assert expect == actual

    # 'xyz/xyz'
    xyz_xyz = xyz.children[0]
    expect = 'xyz'
    actual = xyz_xyz.basename
    assert expect == actual

    expect = 'xyz/xyz'
    actual = xyz_xyz.refname
    assert expect == actual

    expect = []
    actual = xyz_xyz.children
    assert expect == actual


def test_create_name_dict():
    """Test transforming unix path-like names into a nested dict"""
    branches = [
        'top_1/child_1/child_1_1',
        'top_1/child_1/child_1_2',
        'top_1/child_2/child_2_1/child_2_1_1',
        'top_1/child_2/child_2_1/child_2_1_2',
    ]
    inner_child = {'child_2_1_2': {}, 'child_2_1_1': {}}
    expect = {
        'top_1': {
            'child_1': {'child_1_2': {}, 'child_1_1': {}},
            'child_2': {'child_2_1': inner_child},
        }
    }
    actual = branch.create_name_dict(branches)
    assert expect == actual


def test_create_toplevel_item():
    names = [
        'child_1',
        'child_2/child_2_1',
        'child_2/child_2_2',
    ]
    tree = branch.create_tree_entries(names)
    tree.basename = 'top'
    top = branch.create_toplevel_item(tree)

    expect = 'top'
    actual = top.name
    assert expect == actual

    expect = 2
    actual = top.childCount()
    assert expect == actual

    expect = 'child_1'
    actual = top.child(0).name
    assert expect == actual

    expect = 'child_1'
    actual = top.child(0).refname
    assert expect == actual

    expect = 'child_2'
    actual = top.child(1).name
    assert expect == actual

    assert top.child(1).refname is None

    expect = 2
    actual = top.child(1).childCount()
    assert expect == actual

    expect = 'child_2_1'
    actual = top.child(1).child(0).name
    assert expect == actual

    expect = 'child_2_2'
    actual = top.child(1).child(1).name
    assert expect == actual

    expect = 'child_2/child_2_1'
    actual = top.child(1).child(0).refname
    assert expect == actual

    expect = 'child_2/child_2_2'
    actual = top.child(1).child(1).refname
    assert expect == actual


def test_get_toplevel_item():
    items = _create_top_item()
    actual = branch.get_toplevel_item(items['child_1'])
    assert items['top'] is actual

    actual = branch.get_toplevel_item(items['sub_child_2_1'])
    assert items['top'] is actual


def test_refname_attribute():
    items = _create_top_item()

    actual = items['child_1'].refname
    expect = 'child_1'
    assert expect == actual

    actual = items['sub_child_2_2'].refname
    expect = 'child_2/sub_child_2_2'
    assert expect == actual


def test_should_return_a_valid_child_on_find_child():
    """Test the find_child function."""
    items = _create_top_item()
    child = branch.find_by_refname(items['top'], 'child_1')
    assert child.refname == 'child_1'

    child = branch.find_by_refname(items['top'], 'child_2/sub_child_2_2')
    assert child.name == 'sub_child_2_2'


def test_should_return_empty_state_on_save_state():
    """Test the save_state function."""
    top = _create_item('top', None, False)
    tree_helper = branch.BranchesTreeHelper()
    actual = tree_helper.save_state(top)
    assert {'top': {}} == actual


def test_should_return_a_valid_state_on_save_state():
    """Test the save_state function."""
    items = _create_top_item()
    tree_helper = branch.BranchesTreeHelper()
    actual = tree_helper.save_state(items['top'])
    expect = {
        'top': {
            'child_1': {},
            'child_2': {'sub_child_2_1': {}, 'sub_child_2_2': {}},
        }
    }
    assert expect == actual


def _create_top_item():
    top = _create_item('top', None, True)
    child_1 = _create_item('child_1', 'child_1', False)
    child_2 = _create_item('child_2', None, True)
    sub_child_2_1 = _create_item('sub_child_2_1', 'child_2/sub_child_2_1', False)
    sub_child_2_2 = _create_item('sub_child_2_2', 'child_2/sub_child_2_2', False)

    child_2.addChildren([sub_child_2_1, sub_child_2_2])
    top.addChildren([child_1, child_2])

    return {
        'top': top,
        'child_1': child_1,
        'sub_child_2_1': sub_child_2_1,
        'sub_child_2_2': sub_child_2_2,
    }


def _create_item(name, refname, expanded):
    item = branch.BranchTreeWidgetItem(name, refname=refname)
    item.isExpanded = Mock(return_value=expanded)
    return item
