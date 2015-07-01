git-cola's release scripts
==========================

Creating a new release
----------------------
From the top of the git-cola repository a release can then be created by
running:

	Meta/release --all

This branch is intended to be checked out in a seperate repository within a
git-cola repository, e.g. at git-cola/Meta (and is the reason that git-cola's
.gitignore mentions "Meta".  The release script assumes that you have a clone
of git-cola.github.com sibling to the git-cola repository.  Your directory
structure should look roughly like this:

	$HOME/src/git-cola
	$HOME/src/git-cola.github.com

"$HOME/src" can be any arbitrary directory.

Release checklist
-----------------
The following steps should be taken when creating a new release.

* Update `cola/_version.py` with the new version number

* Update `pynsist.cfg` with the new version number

* Create `doc/relnotes/$VERSION.rst` from the pre-release notes in
  `doc/relnotes/unreleased.rst`.

* Update `doc/relnotes/unreleased.rst` to point to the new stable version.

* Commit the above changes as `git commit -sm'git-cola vX.Y'`

* Tag the repo, `git tag -sm'git-cola X.Y'`

* Push the changes to make them available to github for the release.

    git push git-cola master &&
    git push --tags git-cola &&
    git push origin master &&
    git push --tags origin

* Start a Windows VM session

* Run `Meta/release --all` to build the installers and update
  the sibling `git-cola.github.com` repository.

* Commit `git-cola.github.com` changes, `git commit -sm'git-cola vX.Y'`
  and push them to github.
