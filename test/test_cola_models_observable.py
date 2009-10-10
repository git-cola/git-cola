#!/usr/bin/env python
import unittest
import copy

from cola.models.observable import ObservableModel

class ConcreteModel(ObservableModel):
    """A concrete model for testing."""
    message_copy = 'copy'
    def copy(self, *args, **opts):
        """Send notification from the model."""
        self.notify_message_observers(self.message_copy, *args, **opts)

class ConcreteObserver(object):
    """A concrete observer for testing."""
    def __init__(self, model):
        self.args = None
        self.opts = None
        model.add_message_observer(ConcreteModel.message_copy,
                                   self.receive_message)

    def reset(self):
        """Reset test data back to a known good state."""
        self.args = None
        self.opts = None

    def receive_message(self, *args, **opts):
        """Receive notification from the model."""
        self.args = args
        self.opts = opts


class ObservableModelTestCase(unittest.TestCase):
    """Tests the ObservableModel class."""
    def setUp(self):
        self.model = ConcreteModel()
        self.observer = ConcreteObserver(self.model)

    def test_notify_message_observers(self):
        """Test that notifications are delivered."""
        self.model.copy(hello='world')
        self.assertEqual(self.observer.args, (),)
        self.assertEqual(self.observer.opts, {'hello': 'world'})

    def test_observing_multiple_models(self):
        """Test that we can attach to multiple models."""
        self.model.copy(self.model, foo='bar')
        self.assertEqual(self.observer.args, (self.model,))
        self.assertEqual(self.observer.opts, {'foo': 'bar'})

        model = ConcreteModel()
        model.add_message_observer(model.message_copy,
                                   self.observer.receive_message)
        model.copy(model, baz='quux')
        self.assertEqual(self.observer.args, (model,))
        self.assertEqual(self.observer.opts, {'baz': 'quux'})

        self.model.copy(foo='bar')
        self.assertEqual(self.observer.args, (),)
        self.assertEqual(self.observer.opts, {'foo': 'bar'})


if __name__ == '__main__':
    unittest.main()
