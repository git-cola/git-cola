# Command-line Wrappers

The scripts in this directory are provided for convenience. They allow running
`git-cola` directly from the source tree without needing to use a virtualenv or
`pip install --editable .` to generate the entry point scripts.

The `git cola`, `git cola-rebase-editor` and `git dag` Git sub-commands are provided by
the `git-cola`, `git-cola-rebase-editor` and `git-dag` setuptools entry point scripts.

The entry points are the real commands that get installed by `make install` and are
configured in the `entry_points` section in [setup.cfg](../setup.cfg).
