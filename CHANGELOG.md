# History of changes

## Version 1.1.1 (2016-07-01)

### Bugfixes

**Pull requests**

* [PR 44](https://github.com/spyder-ide/qtpy/pull/44) - Make qtpy to set the QT_API environment variable

In this release 1 pull requests were merged


---


## Version 1.1 (2016-06-30)

### New features

* Make importing `qtpy` thread-safe
* Add a uic module to make loadUI work for PySide
* Add QtTest support for PySide

### Bugfixes

**Issues**

* [Issue 42](https://github.com/spyder-ide/qtpy/issues/42) - Wrong old PyQt4 version check
* [Issue 21](https://github.com/spyder-ide/qtpy/issues/21) - Patch QComboBox with PySide?
* [Issue 16](https://github.com/spyder-ide/qtpy/issues/16) - Add loadUI functionality

In this release 3 issues were closed

**Pull requests**

* [PR 43](https://github.com/spyder-ide/qtpy/pull/43) - Don't check PyQt version with qtpy's version for old PyQt versions
* [PR 41](https://github.com/spyder-ide/qtpy/pull/41) - `qtpy.__version__` should be QtPy version, not Qt version
* [PR 40](https://github.com/spyder-ide/qtpy/pull/40) - Mention qt-helpers in README.md, and add myself to AUTHORS.md
* [PR 39](https://github.com/spyder-ide/qtpy/pull/39) - Fix remaining segmentation fault that occurs with the patched QComboBox in PySide
* [PR 38](https://github.com/spyder-ide/qtpy/pull/38) - QtTest for PySide
* [PR 37](https://github.com/spyder-ide/qtpy/pull/37) - Automatically load custom widget classes when using PySide
* [PR 33](https://github.com/spyder-ide/qtpy/pull/33) - Ignore case for QT_API env variable in qtpy submodules
* [PR 32](https://github.com/spyder-ide/qtpy/pull/32) - Remove QItemSelectionModel from QtWidgets for PyQt4 and PySide
* [PR 31](https://github.com/spyder-ide/qtpy/pull/31) - Add compatibility for QItemSelectionModel
* [PR 29](https://github.com/spyder-ide/qtpy/pull/29) - Use ci-helpers (from Astropy) for CI and enable AppVeyor
* [PR 28](https://github.com/spyder-ide/qtpy/pull/28) - Make tests.py into proper unit test, and add Qt version info to pytest header
* [PR 27](https://github.com/spyder-ide/qtpy/pull/27) - Make sure loadUi is available
* [PR 25](https://github.com/spyder-ide/qtpy/pull/25) - Add patched version of QComboBox

In this release 13 pull requests were merged


---


## Version 1.0.2 (2016-06-02)

### New features

* Add a WEBENGINE constant to QtWebEngineWidgets, which is True if Qt 5 comes with the WebEngine module and False otherwise.

### Bugfixes

**Pull requests**

* [PR 24](https://github.com/spyder-ide/qtpy/pull/24) - Add constant to QtWebEngineWidgets to see if we are using WebEngine or WebKit
* [PR 23](https://github.com/spyder-ide/qtpy/pull/23) - Fix "Prefer `format()` over string interpolation operator" issue

In this release 2 pull requests were merged


---


## Version 1.0.1 (2016-04-10)

### Bugfixes

**Issues**

* [Issue 18](https://github.com/spyder-ide/qtpy/issues/18) - QIntValidator left in QtWidgets, should be in QtGui

In this release 1 issues were closed

**Pull requests**

* [PR 19](https://github.com/spyder-ide/qtpy/pull/19) - Import QIntValidator in QtGui and remove it from QtWidgets

In this release 1 pull requests were merged


----

## Version 1.0 (2016-03-22)

* Add QtWebEngineWidgets module for Qt 5.6. This module replaces the previous
  QtWebKit one.

* Import the right objects in QtGui, QtWidgets and QtCore

* Add a QtPrintSupport module


---


## Version 0.1.3 (2015-12-30)

* Add tests and continuous integration

## Version 0.1.2 (2015-03-01)

* First release
