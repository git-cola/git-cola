#!/usr/bin/env python
from __future__ import absolute_import, division, unicode_literals
import unittest

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from cola.widgets import branch


class BranchesTestCase(unittest.TestCase):
    """Tests related to the branches widget"""

    def test_create_tree_entries(self):
        names = [
            'abc',
            'cat/abc',
            'cat/def',
            'xyz/xyz',
        ]
        root = branch.create_tree_entries(names)
        self.assertEqual(3, len(root.children))
        # 'abc'
        abc = root.children[0]
        self.assertEqual('abc', abc.basename)
        self.assertEqual('abc', abc.refname)
        self.assertEqual([], abc.children)
        # 'cat'
        cat = root.children[1]
        self.assertEqual('cat', cat.basename)
        self.assertEqual(None, cat.refname)
        self.assertEqual(2, len(cat.children))
        # 'cat/abc'
        cat_abc = cat.children[0]
        self.assertEqual('abc', cat_abc.basename)
        self.assertEqual('cat/abc', cat_abc.refname)
        self.assertEqual([], cat_abc.children)
        # 'cat/def'
        cat_def = cat.children[1]
        self.assertEqual('def', cat_def.basename)
        self.assertEqual('cat/def', cat_def.refname)
        self.assertEqual([], cat_def.children)
        # 'xyz'
        xyz = root.children[2]
        self.assertEqual('xyz', xyz.basename)
        self.assertEqual(None, xyz.refname)
        self.assertEqual(1, len(xyz.children))
        # 'xyz/xyz'
        xyz_xyz = xyz.children[0]
        self.assertEqual('xyz', xyz_xyz.basename)
        self.assertEqual('xyz/xyz', xyz_xyz.refname)
        self.assertEqual([], xyz_xyz.children)

    def test_create_name_dict(self):
        """Test transforming unix path-like names into a nested dict"""
        branches = [
            'top_1/child_1/child_1_1',
            'top_1/child_1/child_1_2',
            'top_1/child_2/child_2_1/child_2_1_1',
            'top_1/child_2/child_2_1/child_2_1_2',
        ]
        result = branch.create_name_dict(branches)
        inner_child = {'child_2_1_2': {}, 'child_2_1_1': {}}
        self.assertEqual(
            {
                'top_1': {
                    'child_1': {'child_1_2': {}, 'child_1_1': {}},
                    'child_2': {'child_2_1': inner_child},
                }
            },
            result,
        )

    def test_create_toplevel_item(self):
        names = [
            'child_1',
            'child_2/child_2_1',
            'child_2/child_2_2',
        ]
        tree = branch.create_tree_entries(names)
        tree.basename = 'top'
        result = branch.create_toplevel_item(tree)
        self.assertEqual('top', result.name)
        self.assertEqual(2, result.childCount())
        self.assertEqual('child_1', result.child(0).name)
        self.assertEqual('child_1', result.child(0).refname)
        self.assertEqual('child_2', result.child(1).name)
        self.assertEqual(None, result.child(1).refname)
        self.assertEqual(2, result.child(1).childCount())
        self.assertEqual('child_2_1', result.child(1).child(0).name)
        self.assertEqual('child_2_2', result.child(1).child(1).name)
        self.assertEqual('child_2/child_2_1', result.child(1).child(0).refname)
        self.assertEqual('child_2/child_2_2', result.child(1).child(1).refname)

    def test_get_toplevel_item(self):
        items = _create_top_item()
        result = branch.get_toplevel_item(items['child_1'])
        self.assertTrue(items['top'] is result)

        result = branch.get_toplevel_item(items['sub_child_2_1'])
        self.assertTrue(items['top'] is result)

    def test_refname_attribute(self):
        items = _create_top_item()

        result = items['child_1'].refname
        self.assertEqual('child_1', result)

        result = items['sub_child_2_2'].refname
        self.assertEqual('child_2/sub_child_2_2', result)

    def test_should_return_a_valid_child_on_find_child(self):
        """Test the find_child function."""
        items = _create_top_item()
        child = branch.find_by_refname(items['top'], 'child_1')
        self.assertEqual('child_1', child.refname)

        child = branch.find_by_refname(items['top'], 'child_2/sub_child_2_2')
        self.assertEqual('sub_child_2_2', child.name)

    def test_should_return_empty_state_on_save_state(self):
        """Test the save_state function."""
        top = _create_item('top', None, False)
        tree_helper = branch.BranchesTreeHelper()
        result = tree_helper.save_state(top)
        self.assertEqual({'top': {}}, result)

    def test_should_return_a_valid_state_on_save_state(self):
        """Test the save_state function."""
        items = _create_top_item()
        tree_helper = branch.BranchesTreeHelper()
        result = tree_helper.save_state(items['top'])
        self.assertEqual(
            {
                'top': {
                    'child_1': {},
                    'child_2': {'sub_child_2_1': {}, 'sub_child_2_2': {}},
                }
            },
            result,
        )


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
    item.isExpanded = MagicMock(return_value=expanded)
    return item


if __name__ == '__main__':
    unittest.main()
