Next-up Issues
==============

https://github.com/git-cola/git-cola/issues/493 - git add -N partial untracked
https://github.com/git-cola/git-cola/issues/709 - UI unresponsive large LFS
https://github.com/git-cola/git-cola/issues/552 - diff against arbitrary ref
https://github.com/git-cola/git-cola/issues/555 - nautilus integration
https://github.com/git-cola/git-cola/issues/798 - snap package

Notes
=====

snap package home/git interface
https://forum.snapcraft.io/t/new-interface-proprosal-the-git-interface/5498/2

Ideas
=====

- flesh out the rest of the commented-out toolbarcmds.py items

- flesh out the undo/redo stack

- when pushing new branches, automatically set the upstream?

- break apart widgets.remote into push, pull, fetch and reusable widgets

- look at keyPressEvent for the tree mixin in widgets.standard and
  try to rewrite it in using QAction hotkey shortcuts.

- replace the listwidget in stash with a tree widget

- compact, in-widget gitk-like history view

- take advantage of `git log --topo-order` (see docs) when laying out the DAG.

- make dragging locked tools move the main UI

- Create a RemoteBranchLineEdit for completing line edits with remote branches
