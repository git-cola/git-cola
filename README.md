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
