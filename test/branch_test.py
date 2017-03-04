#!/usr/bin/env python
from __future__ import absolute_import, division, unicode_literals

import unittest

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from cola.compat import odict
from cola.widgets.branch import BranchesTreeHelper, BranchTreeWidgetItem


class BranchesTreeHelperTestCase(unittest.TestCase):
    """Tests the BranchesTreeHelper class."""

    def test_should_return_a_valid_dict_on_group_branches(self):
        """Test the group_branches function."""
        branches = ['top_1/child_1/child_1_1',
                    'top_1/child_1/child_1_2',
                    'top_1/child_2/child_2_1/child_2_1_1',
                    'top_1/child_2/child_2_1/child_2_1_2']
        tree_helper = BranchesTreeHelper()

        result = tree_helper.group_branches(branches, '/')
        self.assertEqual({'top_1':
                              {'child_1': {'child_1_2': {}, 'child_1_1': {}},
                               'child_2': {'child_2_1': {'child_2_1_2': {},
                                                         'child_2_1_1': {}}}}},
                         result)

    def test_should_create_a_valid_top_item_on_create_top_level_item(self):
        """Test the create_top_level_item function."""
        dict_children = odict()
        dict_children['child_1'] = {}
        dict_children['child_2'] = odict()
        dict_children['child_2']['child_2_1'] = {}
        dict_children['child_2']['child_2_2'] = {}
        tree_helper = BranchesTreeHelper()

        result = tree_helper.create_top_level_item('top', dict_children)
        self.assertEqual('top', result.name)
        self.assertEqual(2, result.childCount())
        self.assertEqual('child_1', result.child(0).name)
        self.assertEqual('child_2', result.child(1).name)
        self.assertEqual(2, result.child(1).childCount())
        self.assertEqual('child_2_1', result.child(1).child(0).name)
        self.assertEqual('child_2_2', result.child(1).child(1).name)

    def test_should_return_a_valid_top_item_on_get_root(self):
        """Test the get_root function."""
        items = self._create_top_item()
        tree_helper = BranchesTreeHelper()

        result = tree_helper.get_root(items['child_1'])
        self.assertEqual(items['top'], result)

        result = tree_helper.get_root(items['sub_child_2_1'])
        self.assertEqual(items['top'], result)

    def test_should_return_a_valid_branch_name_on_get_full_name(self):
        """Test the get_full_name function."""
        items = self._create_top_item()
        tree_helper = BranchesTreeHelper()

        result = tree_helper.get_full_name(items['child_1'], '/')
        self.assertEqual('child_1', result)

        result = tree_helper.get_full_name(items['sub_child_2_2'], '/')
        self.assertEqual('child_2/sub_child_2_2', result)

    def test_should_return_a_valid_child_on_find_child(self):
        """Test the find_child function."""
        items = self._create_top_item()
        tree_helper = BranchesTreeHelper()

        child = tree_helper.find_child(items['top'], 'child_1')
        self.assertEqual('child_1', child.name)

        child = tree_helper.find_child(items['top'], 'child_2/sub_child_2_2')
        self.assertEqual('sub_child_2_2', child.name)

    def test_should_return_empty_state_on_save_state(self):
        """Test the save_state function."""
        top = self._create_item('top', False)
        tree_helper = BranchesTreeHelper()

        result = tree_helper.save_state(top)
        self.assertEqual({'top': {}}, result)

    def test_should_return_a_valid_state_on_save_state(self):
        """Test the save_state function."""
        items = self._create_top_item()
        tree_helper = BranchesTreeHelper()

        result = tree_helper.save_state(items['top'])
        self.assertEqual({'top': {'child_1': {}, 'child_2': {
            'sub_child_2_1': {}, 'sub_child_2_2': {}}}}, result)

    def _create_item(self, name, expanded):
        item = BranchTreeWidgetItem(name)
        item.isExpanded = MagicMock(return_value=expanded)

        return item

    def _create_top_item(self):
        top = self._create_item('top', True)
        child_1 = self._create_item('child_1', False)
        child_2 = self._create_item('child_2', True)
        sub_child_2_1 = self._create_item('sub_child_2_1', False)
        sub_child_2_2 = self._create_item('sub_child_2_2', False)

        child_2.addChildren([sub_child_2_1, sub_child_2_2])
        top.addChildren([child_1, child_2])

        return {'top': top, 'child_1': child_1, 'sub_child_2_1': sub_child_2_1,
                'sub_child_2_2': sub_child_2_2}

if __name__ == '__main__':
    unittest.main()
