# git-cola: The highly caffeinated git GUI

    git-cola is a powerful git GUI with a slick and intuitive user interface.

    Copyright (C) 2007-2012, David Aguilar and contributors

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
[git-cola screenshots page](http://git-cola.github.com/screenshots.html).

## DOWNLOAD

    apt-get install git-cola python-pyinotify

New releases are available on the
[git-cola download page](http://git-cola.github.com/downloads.html).

## FORK

    git clone git://github.com/git-cola/git-cola.git cola

[git-cola on github](https://github.com/git-cola/git-cola)

[git-cola google group](http://groups.google.com/group/git-cola/)


# NUTRITIONAL FACTS


## ACTIVE INGREDIENTS

* [git](http://git-scm.com/) 1.6.3 or newer

* [Python](http://python.org/) 2.6 or newer

* [PyQt4](http://www.riverbankcomputing.co.uk/software/pyqt/download) 4.4 or newer

## INOTIFY

[pyinotify](https://github.com/seb-m/pyinotify) >= 0.7.1
enables inotify support on Linux.

# BREWING INSTRUCTIONS

Normally you can just do "make install" to install *git-cola*
in your `$HOME` directory (`$HOME/bin`, `$HOME/share`, etc).
If you want to do a global install you can do

    make prefix=/usr install

You don't need to `make` to run it, though.
*git-cola* is designed to run directly out of its source tree.

    git clone git://github.com/git-cola/git-cola.git cola
    cola/bin/git-cola
    cola/bin/git-dag

## MAC OS X

Whether you install cola yourself with `make install` or
use the `git-cola.app` bundle, you will need to install
*Qt4* and *PyQt4*.

The easiest way to do this is to [install homebrew](http://mxcl.github.com/homebrew/)
and use it to install git-cola.

    brew install git-cola

Once brew has installed git-cola (and its dependencies) you use
`git-cola.app` or install from source using `make install`.

Installing these packages also gives you a PyQt development
environment which can be used for building your own applications
or hacking on cola itself.


## WINDOWS INSTALLATION

Download the latest stable Git, Python 2.6, and Py26-PyQt4 installers

* [msysGit](http://code.google.com/p/msysgit/)

* [Python](http://python.org/download/)

* [PyQt](http://www.riverbankcomputing.co.uk/software/pyqt/download/)

* [git-cola Installer](https://github.com/git-cola/git-cola/downloads)

Once these are installed you can run *git-cola* from the Start menu or
from a Git Bash by typing `cola`.

If you are developing *git-cola* on Windows you can run the code by
using the `win32/cola` shell script.

    /c/Python26/python setup.py build
    win32/cola

The `win32/cola` script assumes that you have `python` installed in
either `/c/Python26` or `/c/Python25`.  Adjust accordingly.
