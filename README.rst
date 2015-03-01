.. image:: https://pypip.in/version/QtPy/badge.svg
   :target: https://pypi.python.org/pypi/QtPy/
   :alt: Latest PyPI version

.. image:: https://pypip.in/download/QtPy/badge.svg
   :target: https://pypi.python.org/pypi/QtPy/
   :alt: Number of PyPI downloads

.. image:: https://pypip.in/py_versions/QtPy/badge.svg
   :target: https://pypi.python.org/pypi/QtPy/
   :alt: Supported python version
   
.. image:: https://pypip.in/license/QtPy/badge.svg


About
-----


**QtPy** (pronounced *'cutie pie'*) is a small abstraction layer that lets you
write applications using a single api call to either PyQt or PySide. **QtPy**
also provides a set of additional QWidgets.

It provides support for PyQt5, PyQt4 and PySide using the PyQt5 layout (where
the QtGui module has been split into QtGui and QtWidgets).

Basically, you write your code as if you were using PyQt5 but import qt from
``qtpy`` instead of ``PyQt5``.

- `Issue tracker`_
- `Contributing`_
- `Changelog`_


Attribution and acknowledgements
--------------------------------

This project is based on the `pyqode.qt`_ project and the `spyderlib.qt`_
module from the `spyder`_ project.

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
::

  pip install qtpy

Testing
-------

TODO:

.. _spyder: https://github.com/spyder-ide/spyder
.. _spyderlib.qt: https://github.com/spyder-ide/spyder/tree/master/spyderlib/qt
.. _pyqode.qt: https://github.com/pyQode/pyqode.qt
.. _Changelog: https://github.com/goanpeca/QtPy/blob/master/CHANGELOG.rst
.. _Contributing: https://github.com/goanpeca/QtPy/blob/master/CONTRIBUTING.rst
.. _Issue tracker: https://github.com/goanpeca/QtPy/issues


