- replace QMessagebox with custom widgets so we can save their sizes and
  make them have sensible behavior: resizable, better initial size,
  have the details shown by default.
- custom buttons?  Pass in an dict of names and button labels?
  (name, label, fn)?

- when pushing new branches, automatically set the upstream?
- break apart widgets.remote into push, pull, fetch and reusable widgets

- look at keyPressEvent for the tree mixin in widgets.standard and
  try to rewrite it in using QAction hotkey shortcuts.

- replace the listwidget in stash with a tree widget

- compact, in-widget gitk-like history view

- take advantage of `git log --topo-order` (see docs) when laying out the DAG.

- make dragging locked tools move the main UI

- Create a RemoteBranchLineEdit for completing line edits with remote branches
