"""Simple data container for the CreateTag dialog."""

import cola
from cola.models import observable

class TagModel(observable.ObservableModel):
    def __init__(self):
        observable.ObservableModel.__init__(self)
        self.tag_msg = ''
        self.tag_name = ''
        self.revision = ['HEAD'] + cola.model().all_branches()
        self.sign_tag = False
