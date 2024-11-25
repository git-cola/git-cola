# git-cola maintenance scripts

This branch is intended to be checked out into a "todo" directory within a
git-cola worktree. This is the reason that git-cola's .gitignore mentions "todo".

The release script assumes that you have a clone of git-cola.github.io in a "pages"
subdirectory of the git-cola repository. Your directory structure should look roughly
like this:

	git-cola            # clone of git-cola
	git-cola/pages      # clone of git-cola.github.io
	git-cola/todo       # a worktree with git-cola's "todo" branch

You can create this structure by running these commands using
[garden](https://gitlab.com/garden-rs/garden) (`cargo install garden-tools`)
from a clone of the git-cola repository.

```bash
garden grow pages
garden grow todo
```


## Release checklist

The following steps should be taken when creating a new release.

* `garden check` and make sure all tests and checks are passing.

* `./todo/set-version vX.Y.Z` to update the version number recorded in the source.
This script is equivalent to updating the following files to mention the new version.

  * `cola/_version.py`
  * `share/metainfo/*.appdata.xml`
  * `pynsist.cfg`
  * `docs/relnotes.rst`
  * `pyproject.toml`


* `./todo/commit-version` to commit the above changes (`git commit -asm'git-cola vX.Y.Z'`)

* `./todo/tag` to add the new tag (`git tag -sm'git-cola X.Y'`)

* `garden dev` to update the egg-info to use the tagged version

* `git cola push` to push the changes

```bash
git push origin main
git push --tags origin
git push git-cola main
git push --tags git-cola
```

* `garden wheel` to build wheels.

* `garden publish` to publish to [pypi](https://pypi.org/project/git-cola/).

* `garden clean` to clean out older files.

* `git -C pages pull` to make sure that the `pages` worktree is up to date.

* `vx env3 ./todo/release --all` to build installers and update the `pages` repo.

* `vim pages/_config.yml` to update the release date and version.

* `./todo/pages.sh` to commit update to "pages".

* `./todo/update-qtpy ~/src/python/qtpy` to upgrade the vendored qtpy library after
creating the release so that the new dev cycle is done against the latest qtpy.
