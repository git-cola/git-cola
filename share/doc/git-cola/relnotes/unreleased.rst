git-cola v2.1.2 (unreleased)
============================

Usability, bells and whistles
-----------------------------
* `git cola rebase` now defaults to `@{upstream}`, and generally
  uses the same CLI syntax as `git rebase`.

* Updated zh_TW translations.

Fixes
-----
* `git cola` will now allow starting an interactive rebase with a dirty
  worktree when `rebase.autostash` is set.

  https://github.com/git-cola/git-cola/issues/360
