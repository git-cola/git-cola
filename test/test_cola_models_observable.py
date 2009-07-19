#!/usr/bin/env python
import unittest
import copy

from cola.models.observable import ObservableModel

class ConcreteModel(ObservableModel):
    """A concrete model for testing."""
    message_copy = 'copy'
    def copy(self, **opts):
        """Send notification from the model."""
        self.notify_message_observers(self.message_copy, **opts)

class ConcreteObserver(object):
    """A concrete observer for testing."""
    def __init__(self, model):
        self.opts = None
        self.model = None
        model.add_message_observer(ConcreteModel.message_copy,
                                   self.receive_message)

    def reset(self):
        """Reset test data back to a known good state."""
        self.opts = None
        self.model = None

    def receive_message(self, model, message, **opts):
        """Receive notification from the model."""
        self.opts = copy.deepcopy(opts)
        self.model = model


class ObservableModelTestCase(unittest.TestCase):
    """Tests the ObservableModel class."""
    def setUp(self):
        self.model = ConcreteModel()
        self.observer = ConcreteObserver(self.model)

    def test_notify_message_observers(self):
        """Test that notifications are delivered."""
        self.model.copy(hello='world')
        self.assertEqual(self.observer.opts, {'hello': 'world'})
        self.assertEqual(self.observer.model, self.model)

    def test_notify_message_observers_bogus_message(self):
        """Test that bogus messages are ignored."""
        self.assertRaises(ValueError, self.model.notify_message_observers,
                          'this-is-a-bogus-message')
        self.assertEqual(self.observer.opts, None)
        self.assertEqual(self.observer.model, None)

    def test_observing_multiple_models(self):
        """Test that we can attach to multiple models."""
        self.model.copy(foo='bar')
        self.assertEqual(self.observer.opts, {'foo': 'bar'})
        self.assertEqual(self.observer.model, self.model)

        model = ConcreteModel()
        model.add_message_observer(model.message_copy,
                                   self.observer.receive_message)
        model.copy(baz='quux')

        self.assertEqual(self.observer.opts, {'baz': 'quux'})
        self.assertEqual(self.observer.model, model)

        self.model.copy(foo='bar')
        self.assertEqual(self.observer.opts, {'foo': 'bar'})
        self.assertEqual(self.observer.model, self.model)


if __name__ == '__main__':
    unittest.main()
