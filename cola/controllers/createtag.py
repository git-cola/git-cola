"""Provides CreateTagController to interact with the CreateTag view."""

import cola
from cola import signals
from cola import qobserver
from cola import qtutils
from cola.models import tag
from cola.views import createtag


def create_tag(revision=''):
    """Entry point for external callers."""
    model = tag.TagModel()
    if revision:
        model.revision = [revision]
    view = createtag.CreateTag(qtutils.active_window())
    ctl = CreateTagController(model, view)
    view.show()
    return ctl


class CreateTagController(qobserver.QObserver):
    def __init__(self, model, view):
        qobserver.QObserver.__init__(self, model, view)
        self.add_observables('tag_name', 'tag_msg', 'revision', 'sign_tag')
        self.add_callbacks(create_button=self.create_tag)
        self.refresh_view()

    def create_tag(self):
        """Verifies inputs and emits a notifier tag message."""
        if not self.model.tag_name:
            cola.notifier().broadcast(signals.information,
                                      self.tr('Missing Name'),
                                      self.tr('You must name the tag.'))
            return
        if (self.model.sign_tag and
                not self.model.tag_msg and
                not qtutils.question(self.view,
                                     'Use Empty Message?',
                                     'Signing is enabled and the tag '
                                     'message is empty.\n\n'
                                     'Continue?')):
            return
        cola.notifier().broadcast(signals.tag,
                                  self.model.tag_name,
                                  self.model.revision_item,
                                  sign=self.model.sign_tag,
                                  message=self.model.tag_msg)
        self.view.accept()
