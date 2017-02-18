#!/usr/bin/env python

from __future__ import absolute_import, division, unicode_literals

import unittest

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from cola import icons
from cola.widgets.branch import BranchesTreeHelper, BranchTreeWidgetItem


class BranchesTreeHelperTestCase(unittest.TestCase):
    """Tests the BranchesTreeHelper class."""

    def test_should_return_a_valid_dict_on_group_branches(self):
        """Test the group_branches function."""
        branches = ['top_1/child_1/child_1_1', 'top_1/child_1/child_1_2',
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

        dict_children = {"child_1": {}, "child_2": {"child_2_1": {},
                                                    "child_2_2": {}}}

        tree_helper = BranchesTreeHelper()
        result = tree_helper.create_top_level_item("top", dict_children,
                                                   icons.branch())
        self.assertEqual("top", result.name)
        self.assertEqual(2, result.childCount())
        self.assertEqual("child_1", result.child(0).name)
        self.assertEqual("child_2", result.child(1).name)
        self.assertEqual(2, result.child(1).childCount())
        self.assertEqual("child_2_1", result.child(1).child(0).name)
        self.assertEqual("child_2_2", result.child(1).child(1).name)

    def test_should_return_a_valid_top_item_on_get_root(self):
        """Test the get_root function."""

        top = self._create_item("top", True)
        child_1 = self._create_item("child_1", False)
        child_2 = self._create_item("child_2", True)
        sub_child_2_1 = self._create_item("sub_child_2_1", False)
        sub_child_2_2 = self._create_item("sub_child_2_2", False)

        child_2.addChildren([sub_child_2_1, sub_child_2_2])
        top.addChildren([child_1, child_2])

        tree_helper = BranchesTreeHelper()

        result = tree_helper.get_root(child_1)
        self.assertEqual(top, result)

        result = tree_helper.get_root(sub_child_2_1)
        self.assertEqual(top, result)

    def test_should_return_a_valid_branch_name_on_get_full_name(self):
        """Test the get_full_name function."""

        top = self._create_item("top", True)
        child_1 = self._create_item("child_1", False)
        child_2 = self._create_item("child_2", True)
        sub_child_2_1 = self._create_item("sub_child_2_1", False)
        sub_child_2_2 = self._create_item("sub_child_2_2", False)

        child_2.addChildren([sub_child_2_1, sub_child_2_2])
        top.addChildren([child_1, child_2])

        tree_helper = BranchesTreeHelper()

        result = tree_helper.get_full_name(child_1, '/')
        self.assertEqual('child_1', result)

        result = tree_helper.get_full_name(sub_child_2_2, '/')
        self.assertEqual('child_2/sub_child_2_2', result)

    def test_should_return_empty_state_on_save_state(self):
        """Test the save_state function."""
        tree_helper = BranchesTreeHelper()

        top = self._create_item("top", False)

        result = tree_helper.save_state(top)
        self.assertEqual({"top": {}}, result)

    def test_should_return_a_valid_state_on_save_state(self):
        """Test the save_state function."""
        tree_helper = BranchesTreeHelper()

        top = self._create_item("top", True)
        child_1 = self._create_item("child_1", False)
        child_2 = self._create_item("child_2", True)
        sub_child_2_1 = self._create_item("sub_child_2_1", False)
        sub_child_2_2 = self._create_item("sub_child_2_2", False)

        child_2.addChildren([sub_child_2_1, sub_child_2_2])
        top.addChildren([child_1, child_2])

        result = tree_helper.save_state(top)
        self.assertEqual({"top": {"child_1": {}, "child_2": {
            "sub_child_2_1": {}, "sub_child_2_2": {}}}}, result)

    def _create_item(self, name, expanded):
        item = BranchTreeWidgetItem(name, icons.ellipsis())
        item.isExpanded = MagicMock(return_value=expanded)

        return item

if __name__ == '__main__':
    unittest.main()
