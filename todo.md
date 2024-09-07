# Ideas

- [undo/redo support](https://github.com/git-cola/git-cola/issues/531)

- flesh out the rest of the commented-out toolbarcmds.py items

* [git add -N partially staged files](https://github.com/git-cola/git-cola/issues/493)
- [staged diffs are not displayed without commits](https://github.com/git-cola/git-cola/issues/1110)

- [pull action for the branch dialog](https://github.com/git-cola/git-cola/issues/1055)

- [global config editor](https://github.com/git-cola/git-cola/issues/147)

- DAG enhancements
* [image diff in the DAG view](https://github.com/git-cola/git-cola/issues/1052)
* [rebase to parent commit via DAG](https://github.com/git-cola/git-cola/issues/1056)
* [launch DAG from branches widget](https://github.com/git-cola/git-cola/issues/796)
* [diff against worktree](https://github.com/git-cola/git-cola/issues/608)
* [display tags and branches in commit list](https://github.com/git-cola/git-cola/issues/579)
* [git forest visualization](https://github.com/git-cola/git-cola/issues/352)
* [display as panel](https://github.com/git-cola/git-cola/issues/1128)
* [DAG layout is not remembered](https://github.com/git-cola/git-cola/issues/1174)
* [crashes when selecting large diff](https://github.com/git-cola/git-cola/issues/1074)
* [compact in-widget gitk-like history view](https://github.com/git-cola/git-cola/issues/1044)
* [DAG graph layout](https://github.com/git-cola/git-cola/issues/1418)
* [Copy changelog from commit range](https://github.com/git-cola/git-cola/issues/783)
* take advantage of `git log --topo-order` (see docs) when laying out the DAG.

- [nautilus / file explorer integration](https://github.com/git-cola/git-cola/issues/555)
* [git cola here option for Windows](https://github.com/git-cola/git-cola/issues/928)
* [windows shell / explorer integration](https://github.com/git-cola/git-cola/issues/831)

- make dragging locked tools move the main UI

- [remove deleted tracking branches](https://github.com/git-cola/git-cola/issues/1220)
This should prompt per-branch with options to Cancel, Delete, or Delete All.

- [set author date when committing](https://github.com/git-cola/git-cola/issues/810)

- [i18n for git-cola.github.io](https://github.com/git-cola/git-cola/issues/635)

- [custom git clone destination](https://github.com/git-cola/git-cola/issues/897)

- [opt-in gitmoji support](https://github.com/git-cola/git-cola/issues/722)

- [favorites window customization](https://github.com/git-cola/git-cola/issues/619)

- [github repository management](https://github.com/git-cola/git-cola/issues/532)

- [close tool after creating commit](https://github.com/git-cola/git-cola/issues/439)

- [add favorites recursively](https://github.com/git-cola/git-cola/issues/427)

- [amend last commit when rebasing](https://github.com/git-cola/git-cola/issues/363)
- [rebase commit message editing](https://github.com/git-cola/git-cola/issues/417)

- [system notification when commits are available upstream](https://github.com/git-cola/git-cola/issues/361)

- [open multiple repos using tabs](https://github.com/git-cola/git-cola/issues/1247)
Would require some major rework, but should be possible by making it so that
each repository to has its own ApplicationContext.

- Performance
* [UI unresponsive large LFS files](https://github.com/git-cola/git-cola/issues/709)
* [slow diff on jupyter notebooks](https://github.com/git-cola/git-cola/issues/1316)
- [memory usage grows when browsing poedit](https://github.com/git-cola/git-cola/issues/809)

- [word diff support](https://github.com/git-cola/git-cola/issues/623)
* [display whitespace-only diffs differently](https://github.com/git-cola/git-cola/issues/537)

- [display renamed files](https://github.com/git-cola/git-cola/issues/1172)

- [editorconfig support for the commit message editor](https://github.com/git-cola/git-cola/issues/1165)

- [revert staged edits freezes](https://github.com/git-cola/git-cola/issues/1064)

* [single instance per repo](https://github.com/git-cola/git-cola/issues/527)
* [single instance per repo 2](https://github.com/git-cola/git-cola/issues/575)

- [only show currently checked-out branches in push/pull dialog](https://github.com/git-cola/git-cola/issues/536)

- [filesystem notifications causes the diff widget to continually update](https://github.com/git-cola/git-cola/issues/699)
* [use watchdog for filesystem change notification](https://github.com/git-cola/git-cola/issues/655)

- [display recently modified branches](https://github.com/git-cola/git-cola/issues/415)

- [temporary change author identity](https://github.com/git-cola/git-cola/issues/387)

- [check authorship configuration](https://github.com/git-cola/git-cola/issues/385)

- [git clean support](https://github.com/git-cola/git-cola/issues/366)

- [support the OS theme changing from light to dark](https://github.com/git-cola/git-cola/issues/1403)

- Create a RemoteBranchLineEdit for completing line edits with remote branches

- replace the listwidget in stash with a tree widget

- look at keyPressEvent for the tree mixin in widgets.standard and try to rewrite it in
using QAction hotkey shortcuts.

- [GIT_DIR is not respected](https://github.com/git-cola/git-cola/issues/1233)
We should disable some operations (e.g. opening repositories) when these
variables are being used so that the user is required to set both GIT_DIR
and GIT_WORKTREE.

- [Custom keybindings](https://github.com/git-cola/git-cola/issues/1399)
  Would require a major rework of how keybindings are handled.

- [show line change amount in status](https://github.com/git-cola/git-cola/issues/355)
* [make status panel more intuitive](https://github.com/git-cola/git-cola/issues/944)

- [snap package](https://github.com/git-cola/git-cola/issues/798)

- [git-deps integration](https://github.com/git-cola/git-cola/issues/418)
Add an example plugin and documentation.

- [main window flash bang effect on Windows](https://github.com/git-cola/git-cola/issues/1398)


# Historical / Unresolved Issues

- [commit message cursor jumps on fedora after 30 chars](https://github.com/git-cola/git-cola/issues/1301)

- [git-bindir does not work on Windows](https://github.com/git-cola/git-cola/issues/1258)
Reporter was able to use the `GIT_COLA_GIT` environment variable instead.

- [startup window issues on Linux Mint](https://github.com/git-cola/git-cola/issues/1186)


# Notes

* [snap package home/git interface](https://forum.snapcraft.io/t/new-interface-proprosal-the-git-interface/5498/2)
