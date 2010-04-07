import unittest

from cola import cmdfactory

class UserInputWrapper(object):
    def __init__(self):
        self.callbacks = {
                'hello': self._hello,
                'echo': self._echo,
        }
    def _hello(self):
        return 'world'

    def _echo(self, *args, **opts):
        return args, opts


class CommandFactoryTestCase(unittest.TestCase):
    def setUp(self):
        self.factory = cmdfactory.CommandFactory()
        self.factory.add_command_wrapper(UserInputWrapper())

    def test_prompt_user_hello_world(self):
        self.assertEquals(self.factory.prompt_user('hello'), 'world')

    def test_prompt_user_echo(self):
        args = (42,)
        opts = {'one': 1}
        self.assertEquals(self.factory.prompt_user('echo', *args, **opts),
                          (args, opts))

    def test_raises_on_unknown_callback(self):
        self.assertRaises(NotImplementedError,
                          self.factory.prompt_user, 'unknown-callback')


if __name__ == '__main__':
    unittest.main()
