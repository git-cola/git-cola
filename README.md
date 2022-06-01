# git-cola: The highly caffeinated Git GUI

Git Cola is a powerful Git GUI with a slick and intuitive user interface.

    git clone https://github.com/git-cola/git-cola

[![Build status](https://github.com/git-cola/git-cola/actions/workflows/main.yml/badge.svg?branch=main&event=push)](https://github.com/git-cola/git-cola/actions/workflows/main.yml)

* [Screenshots](https://git-cola.github.io/screenshots.html)

* [Downloads](https://git-cola.github.io/downloads.html)


# Documentation

* [Keyboard shortcuts](https://git-cola.github.io/share/doc/git-cola/hotkeys.html)

* [HTML documentation](https://git-cola.readthedocs.io/en/latest/)

* [Git Cola documentation](docs/git-cola.rst)

* [Git DAG documentation](docs/git-dag.rst)

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


## Optional Features

Git Cola enables additional features when the following
Python modules are installed.

[send2trash](https://github.com/hsoft/send2trash) enables cross-platform
"Send to Trash" functionality.


# Installation

**IMPORTANT**: never run `pip install` as root or outside of a Python virtualenv!

You can install the latest released version using `pip`:

    python3 -m venv env3
    ./env3/bin/pip install git-cola
    ./env3/bin/git-cola

Add the `env3/bin` directory to your `$PATH` (or symlink to `bin/git-cola` from somewhere
in your `$PATH`) allows you to launch Git Cola like any other built-in `git` command:

    git cola
    git dag

## Python Virtual Environments

If you don't have PyQt installed then the easiest way to get it is to use a Python
virtualenv and install Git Cola into it in "editable" mode so that you can "upgrade"
Git Cola by running `git pull`.

    # Create a virtualenv called "env3" and activate it.
    python3 -m venv env3
    source env3/bin/activate

    # One-time setup: install optional requirements for development.
    make requirements-dev requirements-optional

    # Install git-cola in "editable" mode so that it uses the source tree.
    make develop

    # Run Git Cola via the "git-cola" Git subcommand.
    git cola

If you add `env3/bin` (or symlink to `bin/git-cola` ) to your `$PATH` then you can
run `git cola` as if it were a builtin `git` command.

## Standalone Installation

Running `make install` will install Git Cola in your `$HOME` directory
(`$HOME/bin/git-cola`, `$HOME/lib`, etc).

If you want to do a global install you can do

    make prefix=/usr/local install

The `Makefile` also supports `DESTDIR`:

    make DESTDIR=/tmp/stage prefix=/usr/local install

## Linux

Linux is it! Your distro has probably already packaged `git-cola`.
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

    # Install from official binary packages
    pkg install -r FreeBSD devel/git-cola

    # Build from source
    cd /usr/ports/devel/git-cola && make clean install


## macOS

For most end-users we recommend using either Homebrew or `pip install git-cola`
inside of a virtualenv.

You can install Git Cola using the same `Makefile` steps above to install from source.

### Homebrew

An easy way to install Git Cola is to use [Homebrew](https://brew.sh/) .
Use Homebrew to install the git-cola recipe:

    brew install git-cola

If you install using Homebrew you can stop at this step.
You don't need to clone the repo or anything.

### git-cola.app

If you have all of the dependencies installed, either via `pip` or `brew` then
you can build a shell `git-cola.app` app bundle wrapper for use in `/Applications`.

If you'd like to build a `git-cola.app` bundle for `/Applications` run this command:

    make git-cola.app

You will need to periodically rebuild the app wrapper whenever Python is upgraded.

### Updating macOS and Homebrew

Updating macOS can often break Homebrew-managed software.

If you upgrade your macOS version and Git Cola no longer runs then then it is
recommended that you re-install Git Cola's dependencies after upgrading.

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

If you already have Git Cola's dependencies installed then you can 
start `cola` as a Python module if you have the source code available.

    python -m cola
    python -m cola dag


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

Auto-format `cola/i18n/*.po` files before committing when updating translations:

    $ make po

When submitting patches, consult the
[contributing guidelines](CONTRIBUTING.md).


## Packaging Notes

Git Cola installs its modules into the default Python site-packages directory
(eg. `lib/python3.7/site-packages`) using setuptools.

While end-users can use `pip install git-cola` to install Git Cola, distribution
packagers should use the `make prefix=/usr` install process. Git Cola's `Makefile` wraps
`pip install --prefix=<prefix>` to provide a packaging-friendly `make install` target.


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

    git config --global cola.pythonlocation /c/Python39

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
