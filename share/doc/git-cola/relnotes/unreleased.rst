git-cola v2.1.2 (unreleased)
============================

Usability, bells and whistles
-----------------------------
* Updated zh_TW translations.

* `git cola rebase` now defaults to `@{upstream}`, and generally
  uses the same CLI syntax as `git rebase`.

* The commit message editor now allows you to bypass commit hooks
  by selecting the "Bypass Commit Hooks" option.  This is equivalent
  to passing the `--no-verify` option to `git commit`.

  https://github.com/git-cola/git-cola/issues/357

Fixes
-----
* `git cola` will now allow starting an interactive rebase with a dirty
  worktree when `rebase.autostash` is set.

  https://github.com/git-cola/git-cola/issues/360
