from cola import gitcfg
from cola import observable
from cola.cmds import BaseCommand


class PreferencesModel(observable.Observable):
    message_config_updated = 'config_updated'

    def __init__(self):
        observable.Observable.__init__(self)
        self.config = gitcfg.instance()

    def set_config(self, source, config, value):
        if source == 'repo':
            self.config.set_repo(config, value)
        else:
            self.config.set_user(config, value)
        message = self.message_config_updated
        self.notify_observers(message, source, config, value)

    def get_config(self, source, config):
        if source == 'repo':
            return self.config.get_repo(config)
        else:
            return self.config.get(config)


class SetConfig(BaseCommand):
    def __init__(self, model, source, config, value):
        BaseCommand.__init__(self)
        self.undoable = True
        self.source = source
        self.config = config
        self.value = value
        self.old_value = None
        self.model = model

    def do(self):
        self.old_value = self.model.get_config(self.source, self.config)
        self.model.set_config(self.source, self.config, self.value)

    def undo(self):
        if self.old_value is None:
            return
        self.model.set_config(self.source, self.config, self.old_value)
