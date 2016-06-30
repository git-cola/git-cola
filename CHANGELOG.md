# History of changes

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
