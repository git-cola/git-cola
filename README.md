## QtPy: Abtraction layer for PyQt5/PyQt4/PySide

**QtPy** (pronounced *'cutie pie'*) is a small abstraction layer that lets you
write applications using a single API call to either PyQt or PySide.

It provides support for PyQt5, PyQt4 and PySide using the PyQt5 layout (where
the QtGui module has been split into QtGui and QtWidgets).

Basically, you write your code as if you were using PyQt5 but import Qt modules
from `qtpy` instead of `PyQt5`.


### Attribution and acknowledgements

This project is based on the [pyqode.qt](https://github.com/pyQode/pyqode.qt)
project and the [spyderlib.qt](https://github.com/spyder-ide/spyder/tree/2.3/spyderlib/qt)
module from the [Spyder](https://github.com/spyder-ide/spyder) project.

Unlike `pyqode.qt` this is not a namespace package, so it is not tied
to a particular project or namespace.


### License

This project is licensed under the MIT license.


### Requirements

You need PyQt5, PyQt4 or PySide installed in your system to make use
of QtPy. If several of these packages are found, PyQt5 is used by
default unless you set the `QT_API` environment variable.

`QT_API` can take the following values:

* `pyqt5` (to use PyQt5).
* `pyqt` or `pyqt4` (to use PyQt4).
* `pyside` (to use PySide).


### Installation

```bash
pip install qtpy
```

or

```bash
conda install qtpy
```
