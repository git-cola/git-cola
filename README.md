About
-----

**QtPy** (pronounced *'cutie pie'*) is a small abstraction layer that lets you
write applications using a single api call to either PyQt or PySide. **QtPy**
also provides a set of additional QWidgets.

It provides support for PyQt5, PyQt4 and PySide using the PyQt5 layout (where
the QtGui module has been split into QtGui and QtWidgets).

Basically, you write your code as if you were using PyQt5 but import qt from
``qtpy`` instead of ``PyQt5``.

Attribution and acknowledgements
--------------------------------

This project is based on the **[pyqode.qt](https://github.com/pyQode/pyqode.qt)** project and the *[spyderlib](https://github.com/spyder-ide/spyder/tree/master/spyderlib/qt).qt*
module from the **[spyder](https://github.com/spyder-ide/spyder)** project.

Unlike **pyqode.qt** this is not a namespace package so it is not *tied*
to a particular project, or namespace.

License
-------

This project is licensed under the MIT license.

Requirements
------------
You need *PyQt5* or *PyQt4* or *PySide* installed on your system to make use
of QtPy.

Installation
------------
```python
  pip install qtpy
```

Testing
-------
TODO:

