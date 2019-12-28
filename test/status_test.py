#!/usr/bin/env python
from __future__ import absolute_import, division, unicode_literals
import unittest
import unittest.mock as mock

from . import helper

from cola.widgets import status


class TestCase(unittest.TestCase):

    def test_block_signal_context_mgr_loop(self):
        m = mock.MagicMock()
        m.signalsBlocked = lambda : False

        with status.BlockSignals(m):
            pass

        assert m.blockSignals.called
        assert len(m.blockSignals.call_args_list) == 2
        call1, call2 = m.blockSignals.call_args_list

        args, _ = call1
        assert args == (True,)

        args, _ = call2
        assert args == (False,)


    def test_block_signal_context_mgr_noop(self):
        m = mock.MagicMock()
        m.signalsBlocked = lambda : True

        with status.BlockSignals(m):
            pass

        assert m.blockSignals.called
        assert len(m.blockSignals.call_args_list) == 2
        call1, call2 = m.blockSignals.call_args_list

        args, _ = call1
        assert args == (True,)

        args, _ = call2
        assert args == (True,) # set to original

    def test_block_signal_context_mgr_exception(self):
        m = mock.MagicMock()
        m.signalsBlocked = lambda : False

        class MyException(Exception):
            pass

        # test proper pass-through of exceptions
        with self.assertRaises(MyException) as ex:
            with status.BlockSignals(m):
                raise MyException('blah')

        # ensure exception does not stop it from doing right thing
        assert m.blockSignals.called
        assert len(m.blockSignals.call_args_list) == 2
        call1, call2 = m.blockSignals.call_args_list

        args, _ = call1
        assert args == (True,)

        args, _ = call2
        assert args == (False,)

    def test_block_signal_context_mgr_multi(self):
        m = mock.MagicMock()
        m.signalsBlocked = lambda : False

        m2 = mock.MagicMock()
        m2.signalsBlocked = lambda : True

        with status.BlockSignals(m, m2):
            pass

        assert m.blockSignals.called
        assert len(m.blockSignals.call_args_list) == 2
        call1, call2 = m.blockSignals.call_args_list

        args, _ = call1
        assert args == (True,)

        args, _ = call2
        assert args == (False,)

        assert m2.blockSignals.called
        assert len(m2.blockSignals.call_args_list) == 2
        call1, call2 = m2.blockSignals.call_args_list

        args, _ = call1
        assert args == (True,)

        args, _ = call2
        assert args == (True,)



if __name__ == '__main__':
    unittest.main()
