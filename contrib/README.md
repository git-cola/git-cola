Miscellaneous git-cola utilities
================================

The [git-cola bash completion script](git-cola-complation.bash) can be sourced
by `.bashrc` or `/etc/bash_completion.d` to provide completion for `git cola`
on the command-line.

The [travis-build script](travis-build) lets you execute git-cola's
[travis build script](../.travis.yml) locally.  This makes it possible
to debug the travis build on your local machine.  e.g. you can execute
the python2.7 integration tests in .travis.yaml using your system-default
python2.7 inside a virtualenv:

    $ virtualenv --python /usr/bin/python2.7 env27
    $ source env27/bin/activate
    $ pip install pyyaml
    $ ./contrib/travis-build -V 2.7 .travis.yaml

This script can run any travis-like build.yaml file, so we use it to provide a
[python2.6 build script](build-python2.6.sh) and accompanying
[yaml build config](build-python2.6.yaml) that bootstraps a python2.6
virtualenv in the `env26` directory for running the .travis.yaml unit tests.

`build-python2.6.sh` was developed on Debian/sid, where python2.6 is not
available and SSLv3 has been removed.  This allows us to run the unittests
for compatibility testing.  This script uses your existing Qt library,
and rebuilds Python, sip, and PyQt4.

[build-git-cola.sh](build-git-cola.sh) shows how to build git-cola on an older
Unix/Linux OS, such as RHEL5, where Python 2.6 or newer is not available, and
we want to use a newer version of Qt4 than what is provided on the system.
This script rebuilds all of Qt4, Python, and PyQt4.

The [darwin](darwin) directory contains resources for creating Mac OS X
git-cola.app application bundles.

The [win32](win32) directory contains packaging-related utilities and
resources for the Windows installer.  If you're developing git-cola on
Windows then you can use the `cola` and `dag` helper scripts to launch
git-cola from your source tree without needing to have python.exe in your path.
