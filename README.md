# git-cola: The highly caffeinated Git GUI

Git Cola is a powerful Git GUI with a slick and intuitive user interface.

    git clone https://github.com/git-cola/git-cola

[![Build status](https://github.com/git-cola/git-cola/actions/workflows/main.yml/badge.svg?branch=main&event=push)](https://github.com/git-cola/git-cola/actions/workflows/main.yml)

* [Screenshots](https://git-cola.github.io/screenshots.html)

* [Downloads](https://git-cola.github.io/downloads.html)


# Documentation

* [HTML documentation](https://git-cola.readthedocs.io/en/latest/)

* [Git Cola documentation](share/doc/git-cola/git-cola.rst)

* [Git DAG documentation](share/doc/git-cola/git-dag.rst)

* [Keyboard shortcuts](https://git-cola.github.io/share/doc/git-cola/hotkeys.html)

* [Contributing guidelines](CONTRIBUTING.md)


# Requirements

## Build

* [Sphinx](http://sphinx-doc.org/) is used to generate the documentation.

## Runtime

* [Git](https://git-scm.com/) 2.2.0 or newer.

* [Python](https://python.org/) 3.6 or newer.

* [QtPy](https://github.com/spyder-ide/qtpy) 1.1.0 or newer.

Git Cola uses QtPy, so you can choose between PyQt5 and PySide2 by setting
the `QT_API` environment variable to `pyqt5` or `pyside2` as desired.
`qtpy` defaults to `pyqt5` and falls back to `pyside2` if `pyqt5` is not installed.

Any of the following Python Qt libraries must be installed:

* [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5)
  5.6 or newer.

* [PySide2](https://github.com/PySide/PySide)
  5.11.0 or newer.

Set `QT_API=pyqt4` in your environment if you have both
versions of PyQt installed and want to ensure that PyQt4 is used.

## Optional Features

Git Cola enables additional features when the following
Python modules are installed.

[send2trash](https://github.com/hsoft/send2trash) enables cross-platform
"Send to Trash" functionality.


# How to Install Git Cola

## Run from Source

You can run Git Cola directly from its source tree and try the latest version
without needing to `make install` it.

    git clone https://github.com/git-cola/git-cola
    cd git-cola
    ./bin/git-cola
    ./bin/git-dag

You can also start `cola` as a Python module if Python can find it.

    cd git-cola
    python -m cola
    python -m cola dag

Having git-cola's `bin/` directory in your path allows you to run
`git cola` like a regular built-in Git command:

    # Replace "$HOME/git-cola/bin" with the path to git-cola's bin/ directory
    PATH="$HOME/git-cola/bin":"$PATH"
    export PATH

    git cola
    git dag

The instructions below assume that you have git-cola present in your
`$PATH`.  Replace `git cola` with `./bin/git-cola` to run it in-place.

## Python Virtual Environments

If you don't have PyQt installed then the easiest way to get it is to use a Python
virtualenv and install PyQt5 inside of it.

    python3 -m venv env3
    ./env3/bin/pip install -r requirements/requirements.txt

You can then run Git Cola using the `env3` virtualenv.

    ./env3/bin/python ./bin/git-cola

## Standalone Installation

Running `make install` will install Git Cola in your `$HOME` directory
(`$HOME/bin/git-cola`, `$HOME/share/git-cola`, etc).

If you want to do a global install you can do

    make prefix=/usr install

Distutils is used by the `Makefile` via `setup.py` to install git-cola and
its launcher scripts.  distutils replaces the `#!/usr/bin/env python` lines in
scripts with the full path to python at build time, which can be undesirable
when the runtime python is not the same as the build-time python.

To disable the replacement of the `#!/usr/bin/env python` lines, pass `USE_ENV_PYTHON=1`
to `make`.

## Linux

Linux is it! Your distro has probably already packaged git-cola.
If not, please file a bug against your distribution ;-)

### Arch

Available in the [AUR](https://aur.archlinux.org/packages/git-cola/).

### Debian, Ubuntu

    apt install git-cola

### Fedora

    dnf install git-cola

### Gentoo

    emerge git-cola

### OpenSUSE, SLE

    zypper install git-cola

### Slackware

Available in [SlackBuilds.org](http://slackbuilds.org/result/?search=git-cola).

### Ubuntu

[See here](https://packages.ubuntu.com/search?keywords=git-cola) for the
versions that are available in Ubuntu's repositories.

There was a [PPA by @pavreh](https://launchpad.net/~pavreh/+archive/ubuntu/git-cola)
but it has not been updated for a while.


## FreeBSD

    # install from official binary packages
    pkg install -r FreeBSD devel/git-cola

    # build from source
    cd /usr/ports/devel/git-cola && make clean install

## macOS

[Homebrew](https://brew.sh/) is the easiest way to install
Git Cola's PyQt5 dependencies.  We will use Homebrew to install
the git-cola recipe, but build our own .app bundle from source.

[Sphinx](http://sphinx-doc.org/latest/install.html) is used to build the
documentation.

    brew install sphinx-doc
    brew install git-cola

Once brew has installed `git-cola` you can:

1. Clone the git-cola repositroy

    git clone https://github.com/git-cola/git-cola
    cd git-cola

2. Build the git-cola.app application bundle

    make \
        PYTHON=$(brew --prefix python3)/bin/python3 \
        PYTHON_CONFIG=$(brew --prefix python3)/bin/python3-config \
        SPHINXBUILD=$(brew --prefix sphinx-doc)/bin/sphinx-build \
        git-cola.app

3. Copy it to /Applications

    rsync -ar --delete git-cola.app/ /Applications/git-cola.app/

Newer versions of Homebrew install their own `python3` installation and
provide the `PyQt5` modules for `python3` only.  You have to use
`python3 ./bin/git-cola` when running from the source tree.

### Upgrading using Homebrew

If you upgrade using `brew` then it is recommended that you re-install
Git Colaa's dependencies when upgrading.  Re-installing ensures that the
Python modules provided by Homebrew will be properly set up.

A quick fix when upgrading to newer versions of XCode or macOS is to
reinstall pyqt5.

    brew reinstall pyqt@5

You may also need to relink your pyqt installation:

    brew link pyqt@5

This is required when upgrading to a modern (post-10.11 El Capitan) Mac OS X.
Homebrew now bundles its own Python3 installation instead of using the
system-provided default Python.

If the "brew reinstall" command above does not work then re-installing from
scratch using the instructions below should get things back in shape.

    # update homebrew
    brew update

    # uninstall git-cola and its dependencies
    brew uninstall git-cola
    brew uninstall pyqt5
    brew uninstall sip

    # re-install git-cola and its dependencies
    brew install git-cola

## Windows

IMPORTANT If you have a 64-bit machine, install the 64-bit versions only.
Do not mix 32-bit and 64-bit versions.

Download and install the following:

* [Git for Windows](https://git-for-windows.github.io/)

* [Git Cola](https://github.com/git-cola/git-cola/releases)

Once these are installed you can run Git Cola from the Start menu.

See "Windows (Continued)" below for more details.


# Goodies

Git Cola ships with an interactive rebase editor called `git-cola-sequence-editor`.
`git-cola-sequence-editor` is used to reorder and choose commits when rebasing.
Start an interactive rebase through the "Rebase" menu, or through the
`git cola rebase` sub-command to use the `git-cola-sequence-editor`:

    git cola rebase @{upstream}

`git-cola-sequence-editor` can be launched independently of git cola by telling
`git rebase` to use it as its editor through the `GIT_SEQUENCE_EDITOR`
environment variable:

    export GIT_SEQUENCE_EDITOR="$HOME/git-cola/bin/git-cola-sequence-editor"
    git rebase -i @{upstream}


# Git Cola Sub-commands

The `git-cola` command exposes various sub-commands that allow you to quickly
launch tools that are available from within the git-cola interface.
For example, `git cola find` launches the file finder,
and `git cola grep` launches the grep tool.

See `git cola --help-commands` for the full list of commands.

    $ git cola --help-commands
    usage: git-cola [-h]
    
                    {cola,am,archive,branch,browse,config,
                     dag,diff,fetch,find,grep,merge,pull,push,
                     rebase,remote,search,stash,tag,version}
                    ...
    
    valid commands:
      {cola,am,archive,branch,browse,config,
       dag,diff,fetch,find,grep,merge,pull,push,
       rebase,remote,search,stash,tag,version}

        cola                start git-cola
        am                  apply patches using "git am"
        archive             save an archive
        branch              create a branch
        browse              browse repository
        config              edit configuration
        dag                 start git-dag
        diff                view diffs
        fetch               fetch remotes
        find                find files
        grep                grep source
        merge               merge branches
        pull                pull remote branches
        push                push remote branches
        rebase              interactive rebase
        remote              edit remotes
        search              search commits
        stash               stash and unstash changes
        tag                 create tags
        version             print the version

## Development

The following commands should be run during development:

    # Run the unit tests
    $ make test

    # Run tests and longer-running pylint and flake8 checks
    $ make check

    # Run tests against multiple python interpreters using tox
    $ make tox

The test suite can be found in the [test](test) directory.

Commits and pull requests are automatically tested for code quality
using [GitHub Actions](https://github.com/git-cola/git-cola/actions/workflows/main.yml).

Auto-format `po/*.po` files before committing when updating translations:

    $ make po

When submitting patches, consult the
[contributing guidelines](CONTRIBUTING.md).


## Packaging Notes

Git Cola installs its modules into the default Python site-packages directory
(eg. `lib/python3.7/site-packages`), and in its own private `share/git-cola/lib`
area by default.  The private modules are redundant and not needed when cola's modules
have been installed into the site-packages directory.

Git Cola will prefer its private modules when the `share/git-cola/lib` directory
exists, but they are not required to exist.  This directory is optional, and can
be safely removed if the cola modules have been installed into site-packages
and are importable through the default `sys.path`.

To suppress the installation of the private (redundant) `share/git-cola/lib/cola`
package, specify `make NO_PRIVATE_LIBS=1 ...` when invoking `make`,
or export `GIT_COLA_NO_PRIVATE_LIBS=1` into the build environment.

    make NO_PRIVATE_LIBS=1 ...

Git Cola installs a vendored copy of its QtPy dependency by default.
Git Cola provides a copy of the `qtpy` module in its private modules area
when installing Git Cola so that you are not required to install QtPy separately.
If you'd like to provide your own `qtpy` module, for example from the `python-qtpy`
Debian package, then specify `make NO_VENDOR_LIBS=1 ...` when invoking `make`,
or export `GIT_COLA_NO_VENDOR_LIBS=1` into the build environment.

    make NO_VENDOR_LIBS=1 ...

Python3 users on debian will need to install `python3-distutils` in order
to run the Makefile's installation steps.  `distutils` is a Python build
requirement, but not needed at runtime.

# Windows (Continued)

## Microsoft Visual C++ 2015 Redistributable

Earlier versions of Git Cola may have shipped without `vcruntime140.dll`  and may
not run on machines that are missing this DLL.

To fix this, download the
[Microsoft Visual C++ 2015 Redistributable](https://www.microsoft.com/en-us/download/details.aspx?id=52685)
and install it

Git Cola v4.0.0 and newer include this DLL and do not require this to be installed
separately.

## Development

In order to develop Git Cola on Windows you will need to install
Python3 and pip.  Install PyQt5 using `pip install PyQt5`
to make the PyQt5 bindings available to Python.

Once these are installed you can use `python.exe` to run
directly from the source tree.  For example, from a Git Bash terminal:

    /c/Python36/python.exe ./bin/git-cola

## Multiple Python versions

If you have multiple versions of Python installed, the `contrib/win32/cola`
launcher script might choose the newer version instead of the python
that has PyQt installed.  In order to resolve this, you can set the
`cola.pythonlocation` git configuration variable to tell cola where to
find python.  For example:

    git config --global cola.pythonlocation /c/Python36

## Building Windows Installers

Windows installers are built using

* [Pynsist](https://pynsist.readthedocs.io/en/latest/).

* [NSIS](http://nsis.sourceforge.net/Main_Page) is also needed.

To build the installer using Pynsist run:

    ./contrib/win32/run-pynsist.sh

This will generate an installer in `build/nsis/`.

## Windows "History Browser" Configuration Upgrade

You may need to configure your history browser if you are upgrading from an
older version of Git Cola on Windows.

`gitk` was originally the default history browser, but `gitk` cannot be
launched as-is on Windows because `gitk` is a shell script.

If you are configured to use `gitk`, then change your configuration to
go through Git's `sh.exe` on Windows.  Similarly, we must go through
`python.exe` if we want to use `git-dag`.

If you want to use gitk as your history browser open the
Preferences screen and change the history browser command to:

    "C:/Program Files/Git/bin/sh.exe" --login -i C:/Git/bin/gitk

`git-dag` became the default history browser on Windows in `v2.3`, so new
users do not need to configure anything.
