# git-cola: The highly caffeinated Git GUI

    git-cola is a powerful Git GUI with a slick and intuitive user interface.

    Copyright (C) 2007-2020, David Aguilar and contributors

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

## SCREENSHOTS

Screenshots are available on the
[git-cola screenshots page](https://git-cola.github.io/screenshots.html).

## DOWNLOAD

    apt install git-cola

New releases are available on the
[git-cola download page](https://git-cola.github.io/downloads.html).

## FORK

    git clone git://github.com/git-cola/git-cola.git

[![git-cola build status](https://github.com/git-cola/git-cola/actions/workflows/main.yml/badge.svg?branch=main&event=push)](https://github.com/git-cola/git-cola/actions/workflows/main.yml)

[git-cola on github](https://github.com/git-cola/git-cola)

[git-cola google group](https://groups.google.com/group/git-cola/)


# NUTRITIONAL FACTS

## ACTIVE INGREDIENTS

* [git](https://git-scm.com/) 1.6.3 or newer.

* [Python](https://python.org/) 2.6 or newer (Python 2+3 compatible).

* [QtPy](https://github.com/spyder-ide/qtpy) 1.1.0 or newer.

* [argparse](https://pypi.python.org/pypi/argparse) 1.1 or newer.
  argparse is part of the stdlib in Python 2.7; install argparse separately if
  you are running on Python 2.6.

* [Sphinx](http://sphinx-doc.org/) for building the documentation.

git-cola uses QtPy, so you can choose between PyQt4, PyQt5, and
PySide by setting the `QT_API` environment variable to `pyqt4`, `pyqt5` or
`pyside` as desired.  `qtpy` defaults to `pyqt5` and falls back to `pyqt4`
if `pyqt5` is not installed.

Any of the following Python Qt libraries must be installed:

* [PyQt4](https://www.riverbankcomputing.com/software/pyqt/download)
  4.6 or newer

* [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5)
  5.2 or newer

* [PySide](https://github.com/PySide/PySide)
  1.1.0 or newer

Set `QT_API=pyqt4` in your environment if you have both
versions of PyQt installed and want to ensure that PyQt4 is used.

## ADDITIVES

git-cola enables additional features when the following
Python modules are installed.

[send2trash](https://github.com/hsoft/send2trash) enables cross-platform
"Send to Trash" functionality.

# BREWING INSTRUCTIONS

## RUN FROM SOURCE

You don't need to install git-cola to run it.
Running git-cola from its source tree is the easiest
way to try the latest version.

    git clone git://github.com/git-cola/git-cola.git
    cd git-cola
    ./bin/git-cola
    ./bin/git-dag

You can also start `cola` as a Python module if Python can find it.

    cd git-cola
    python -m cola
    python -m cola dag

Having git-cola's `bin/` directory in your path allows you to run
`git cola` like a regular built-in Git command:

    # Replace "$PWD/bin" with the path to git-cola's bin/ directory
    PATH="$PWD/bin":"$PATH"
    export PATH

    git cola
    git dag

The instructions below assume that you have git-cola present in your
`$PATH`.  Replace "git cola" with "./bin/git-cola" as needed if you'd like to
just run it in-place.

# DOCUMENTATION

* [HTML documentation](https://git-cola.readthedocs.io/en/latest/)

* [git-cola manual](share/doc/git-cola/git-cola.rst)

* [git-dag manual](share/doc/git-cola/git-dag.rst)

* [Keyboard shortcuts](https://git-cola.github.io/share/doc/git-cola/hotkeys.html)

* [Contributing guidelines](CONTRIBUTING.md)

# INSTALLATION

Normally you can just do "make install" to install git-cola
in your `$HOME` directory (`$HOME/bin`, `$HOME/share`, etc).
If you want to do a global install you can do

    make prefix=/usr install

The platform-specific installation methods below use the native
package manager.  You should use one of these so that all of git-cola's
dependencies are installed.

Distutils is used by the `Makefile` via `setup.py` to install git-cola and
its launcher scripts.  distutils replaces the `#!/usr/bin/env python` lines in
scripts with the full path to python at build time, which can be undesirable
when the runtime python is not the same as the build-time python.  To disable
the replacement of the `#!/usr/bin/env python` lines, pass `USE_ENV_PYTHON=1`
to `make`.

## LINUX

Linux is it! Your distro has probably already packaged git-cola.
If not, please file a bug against your distribution ;-)

### arch

Available in the [AUR](https://aur.archlinux.org/packages/git-cola/).

### debian, ubuntu

    apt install git-cola

### fedora

    dnf install git-cola

### gentoo

    emerge git-cola

### opensuse, sle

    zypper install git-cola

### slackware

Available in [SlackBuilds.org](http://slackbuilds.org/result/?search=git-cola).

### FreeBSD

    # install from official binary packages
    pkg install -r FreeBSD devel/git-cola
    # build from source
    cd /usr/ports/devel/git-cola && make clean install

## Ubuntu

[See here](https://packages.ubuntu.com/search?keywords=git-cola) for the
versions that are available in Ubuntu's repositories.

There was a [PPA by @pavreh](https://launchpad.net/~pavreh/+archive/ubuntu/git-cola)
but it has not been updated for a while.

## MAC OS X

[Homebrew](https://brew.sh/) is the easiest way to install
git-cola's Qt4 and PyQt4 dependencies.  We will use Homebrew to install
the git-cola recipe, but build our own .app bundle from source.

[Sphinx](http://sphinx-doc.org/latest/install.html) is used to build the
documentation.

    brew install sphinx-doc
    brew install git-cola

Once brew has installed git-cola you can:

1. Clone git-cola

    `git clone git://github.com/git-cola/git-cola.git && cd git-cola`

2. Build the git-cola.app application bundle

    ```
    make \
        PYTHON=$(brew --prefix python3)/bin/python3 \
        PYTHON_CONFIG=$(brew --prefix python3)/bin/python3-config \
        SPHINXBUILD=$(brew --prefix sphinx-doc)/bin/sphinx-build \
        git-cola.app
   ```

3. Copy it to /Applications

    `rm -fr /Applications/git-cola.app && cp -r git-cola.app /Applications`

Newer versions of Homebrew install their own `python3` installation and
provide the `PyQt5` modules for `python3` only.  You have to use
`python3 ./bin/git-cola` when running from the source tree.

### UPGRADING USING HOMEBREW

If you upgrade using `brew` then it is recommended that you re-install
git-cola's dependencies when upgrading.  Re-installing ensures that the
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

## WINDOWS INSTALLATION

IMPORTANT If you have a 64-bit machine, install the 64-bit versions only.
Do not mix 32-bit and 64-bit versions.

Download and install the following:

* [Git for Windows](https://git-for-windows.github.io/)

* [Git Cola](https://github.com/git-cola/git-cola/releases)

Once these are installed you can run Git Cola from the Start menu.

See "WINDOWS (continued)" below for more details.

# GOODIES

git cola ships with an interactive rebase editor called `git-cola-sequence-editor`.
`git-cola-sequence-editor` is used to reorder and choose commits when rebasing.
Start an interactive rebase through the "Rebase" menu, or through the
`git cola rebase` sub-command to use the `git-cola-sequence-editor`:

    git cola rebase origin/main

git-cola-sequence-editor can be launched independently of git cola by telling
`git rebase` to use it as its editor through the `GIT_SEQUENCE_EDITOR`
environment variable:

    env GIT_SEQUENCE_EDITOR="$PWD/bin/git-cola-sequence-editor" \
    git rebase -i origin/main

# COMMAND-LINE TOOLS

The git-cola command exposes various sub-commands that allow you to quickly
launch tools that are available from within the git-cola interface.
For example, `./bin/git-cola find` launches the file finder,
and `./bin/git-cola grep` launches the grep tool.

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

## HACKING

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

## SOURCE INSTALL

For Linux/Unix-like environments with symlinks, an easy way to use the latest
`git cola` is to keep a clone of the repository and symlink it into your
`~/bin` directory.  If `$HOME/bin` is not already in your `$PATH` you can
add these two lines to the bottom of your `~/.bashrc` to make the linked
tools available.

        PATH="$HOME/bin":"$PATH"
        export PATH

Then, install git-cola by linking it into your `~/bin`:

        mkdir -p ~/src ~/bin
        git clone git://github.com/git-cola/git-cola.git ~/src/git-cola
        (cd ~/bin &&
         ln -s ../src/git-cola/bin/git-cola &&
         ln -s ../src/git-cola/bin/git-dag)

You should then get the latest `git cola` in your shell.


## PACKAGING NOTES

Git Cola installs its modules into the default Python site-packages directory
(eg. `lib/python2.7/site-packages`), and in its own private `share/git-cola/lib`
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

# WINDOWS (continued)

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

## BUILDING WINDOWS INSTALLERS

Windows installers are built using

* [Pynsist](https://pynsist.readthedocs.io/en/latest/).

* [NSIS](http://nsis.sourceforge.net/Main_Page) is also needed.

To build the installer using Pynsist run:

    ./contrib/win32/run-pynsist.sh

This will generate an installer in `build/nsis/`.

## WINDOWS HISTORY BROWSER CONFIGURATION UPGRADE

You may need to configure your history browser if you are upgrading from an
older version of Git Cola.

`gitk` was originally the default history browser, but `gitk` cannot be
launched as-is on Windows because `gitk` is a shell script.

If you are configured to use `gitk`, then change your configuration to
go through Git's `sh.exe` on Windows.  Similarly, we must go through
`python.exe` if we want to use `git-dag`.

If you want to use gitk as your history browser open the
Preferences screen and change the history browser command to:

    "C:/Program Files/Git/bin/sh.exe" --login -i C:/Git/bin/gitk

git-dag became the default history browser on Windows in `v2.3`, so new
users should not need to configure anything.
