# History of changes

## Version 1.11.2 (2021-09-23)

### Issues Closed

* [Issue 248](https://github.com/spyder-ide/qtpy/issues/248) - Missing QtDataVisualization ([PR 249](https://github.com/spyder-ide/qtpy/pull/249) by [@dalthviz](https://github.com/dalthviz))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 249](https://github.com/spyder-ide/qtpy/pull/249) - PR: Add handling for QtDataVisualization when missing, by [@dalthviz](https://github.com/dalthviz) ([248](https://github.com/spyder-ide/qtpy/issues/248))

In this release 1 pull request was closed.


----


## Version 1.11.1 (2021-09-13)

### Issues Closed

* [Issue 245](https://github.com/spyder-ide/qtpy/issues/245) - Importing `qtpy.uic` raises an exception ([PR 246](https://github.com/spyder-ide/qtpy/pull/246) by [@dalthviz](https://github.com/dalthviz))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 246](https://github.com/spyder-ide/qtpy/pull/246) - PR: Wrap `pysideuic` and `pyside2uic` imports since they could be unavailable, by [@dalthviz](https://github.com/dalthviz) ([245](https://github.com/spyder-ide/qtpy/issues/245))
* [PR 244](https://github.com/spyder-ide/qtpy/pull/244) - qtpy/tests/test_uic.py: skip if pyside2uic not installed, by [@AndrewAmmerlaan](https://github.com/AndrewAmmerlaan)

In this release 2 pull requests were closed.


----


## Version 1.11.0 (2021-09-03)

### Issues Closed

* [Issue 201](https://github.com/spyder-ide/qtpy/issues/201) - Missing QWebEngineProfile from QtWebEngineWidgets ([PR 242](https://github.com/spyder-ide/qtpy/pull/242) by [@dalthviz](https://github.com/dalthviz))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 243](https://github.com/spyder-ide/qtpy/pull/243) - PR: `QtDataVisualization` backward compatibility handling on Windows, by [@dalthviz](https://github.com/dalthviz)
* [PR 242](https://github.com/spyder-ide/qtpy/pull/242) - PR: Add `QtWebEngineWidgets.QWebEngineProfile` for PyQt5 and PySide2, by [@dalthviz](https://github.com/dalthviz) ([201](https://github.com/spyder-ide/qtpy/issues/201))
* [PR 228](https://github.com/spyder-ide/qtpy/pull/228) - PR: Rename QtDatavisualization to use uppercase v, by [@antlarr](https://github.com/antlarr)
* [PR 219](https://github.com/spyder-ide/qtpy/pull/219) - PR: Add support for QStyleOptionFrameV3 from PyQt4, by [@PierreRaybaut](https://github.com/PierreRaybaut)
* [PR 218](https://github.com/spyder-ide/qtpy/pull/218) - PR: Add QtWinExtras module, by [@phil65](https://github.com/phil65)
* [PR 209](https://github.com/spyder-ide/qtpy/pull/209) - PR: Add support for QtSerialPort add-on, by [@Stanowczo](https://github.com/Stanowczo)
* [PR 205](https://github.com/spyder-ide/qtpy/pull/205) - PR: Add support for the QtPositioning module, by [@avalentino](https://github.com/avalentino)
* [PR 202](https://github.com/spyder-ide/qtpy/pull/202) - PR: Add loadUiType implementation for PySide2, by [@avalentino](https://github.com/avalentino)

In this release 8 pull requests were closed.


----


## Version 1.10.0 (2021-08-17)

### Issues Closed

* [Issue 238](https://github.com/spyder-ide/qtpy/issues/238) - PySide2 and Python3.9: xml.etree.ElementTree.Element' object has no attribute 'getchildren
* [Issue 222](https://github.com/spyder-ide/qtpy/issues/222) - Imported modules are not respected
* [Issue 220](https://github.com/spyder-ide/qtpy/issues/220) - MNT: Stop using ci-helpers in appveyor.yml
* [Issue 206](https://github.com/spyder-ide/qtpy/issues/206) - DeprecationWarning for getchildren ([PR 224](https://github.com/spyder-ide/qtpy/pull/224) by [@irrcombat](https://github.com/irrcombat))
* [Issue 198](https://github.com/spyder-ide/qtpy/issues/198) - PyQt4-sip==4.19.13 not supported

In this release 5 issues were closed.

### Pull Requests Merged

* [PR 241](https://github.com/spyder-ide/qtpy/pull/241) - PR: Update setup.py classifiers, by [@dalthviz](https://github.com/dalthviz)
* [PR 230](https://github.com/spyder-ide/qtpy/pull/230) - PR: Fix imported modules logic if 'FORCE_QT_API' is empty, by [@hiaselhans](https://github.com/hiaselhans)
* [PR 224](https://github.com/spyder-ide/qtpy/pull/224) - PR: Support python 3.9 `custom_widgets` iteration, by [@irrcombat](https://github.com/irrcombat) ([206](https://github.com/spyder-ide/qtpy/issues/206))
* [PR 215](https://github.com/spyder-ide/qtpy/pull/215) - PR: Slight typo fix, by [@altendky](https://github.com/altendky)
* [PR 214](https://github.com/spyder-ide/qtpy/pull/214) - PR: Handle QtCore.SignalInstance/pyqtBoundSignal, by [@altendky](https://github.com/altendky)
* [PR 208](https://github.com/spyder-ide/qtpy/pull/208) - PR: Move CI to Github Actions, by [@goanpeca](https://github.com/goanpeca)
* [PR 204](https://github.com/spyder-ide/qtpy/pull/204) - PR: Add Python 3.9 compatibility for `collections.abc` module, by [@tirkarthi](https://github.com/tirkarthi)
* [PR 199](https://github.com/spyder-ide/qtpy/pull/199) - PR: Add support to PyQt4-sip 4.19.13, by [@milanmatic](https://github.com/milanmatic)

In this release 8 pull requests were closed.


----


## Version 1.9.0 (2019-07-23)

### New features

* Add the FORCE_QT_API environment variable to keep using the Qt
  bindings selected with the QT_API variable and avoid switching
  to the currently imported bindings. This allows to have
  applications that import PySide and PyQt bindings at the same
  time (which is possible if both bindings are compiled for the
  same Qt version).

### Issues Closed

* [Issue 195](https://github.com/spyder-ide/qtpy/issues/195) - Errors in the Qt3D modules with PySide2 5.12.4+ and Python 2 ([PR 196](https://github.com/spyder-ide/qtpy/pull/196))
* [Issue 192](https://github.com/spyder-ide/qtpy/issues/192) - Binding Selection Logic ([PR 194](https://github.com/spyder-ide/qtpy/pull/194))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 196](https://github.com/spyder-ide/qtpy/pull/196) - PR: Don't load Qt3D modules for buggy versions of PySide2 ([195](https://github.com/spyder-ide/qtpy/issues/195))
* [PR 194](https://github.com/spyder-ide/qtpy/pull/194) - PR: Add FORCE_QT_API environment variable ([192](https://github.com/spyder-ide/qtpy/issues/192))

In this release 2 pull requests were closed.


----


## Version 1.8.0 (2019-06-12)

### New features

* Add support for several Qt 3D modules.

### Issues Closed

* [Issue 172](https://github.com/spyder-ide/qtpy/issues/172) - Support for Qt3D ([PR 191](https://github.com/spyder-ide/qtpy/pull/191))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 191](https://github.com/spyder-ide/qtpy/pull/191) - PR: Add Qt 3D bindings ([172](https://github.com/spyder-ide/qtpy/issues/172))

In this release 1 pull request was closed.


----


## Version 1.7.1 (2019-05-05)


### Pull Requests Merged

* [PR 189](https://github.com/spyder-ide/qtpy/pull/189) - PR: Skip testing PyQt4 and PySide in Python 3.5
* [PR 188](https://github.com/spyder-ide/qtpy/pull/188) - PR: Trivial maintenance tweaks
* [PR 187](https://github.com/spyder-ide/qtpy/pull/187) - PR: Avoid deprecated "from collections import MutableMapping"

In this release 3 pull requests were closed.


----


## Version 1.7.0 (2019-03-16)

### New features

* Add support for QtCharts.

### Pull Requests Merged

* [PR 186](https://github.com/spyder-ide/qtpy/pull/186) - PR: Generate PyPI long description from README.md
* [PR 183](https://github.com/spyder-ide/qtpy/pull/183) - PR: Add QtCharts module support
* [PR 182](https://github.com/spyder-ide/qtpy/pull/182) - PR: Prevent warnings for equivalent APIs
* [PR 176](https://github.com/spyder-ide/qtpy/pull/176) - PR: Don't warn about bindings change if user did not specify a binding

In this release 4 pull requests were closed.


----


## Version 1.6 (2019-01-12)

### New features

* Add support for QtQuickWidgets.

### Issues Closed

* [Issue 178](https://github.com/spyder-ide/qtpy/issues/178) - Error when import QtCore.__version__ in PySide2 ([PR 180](https://github.com/spyder-ide/qtpy/pull/180))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 181](https://github.com/spyder-ide/qtpy/pull/181) - PR: Restore QWebEngineSettings for PySide2
* [PR 180](https://github.com/spyder-ide/qtpy/pull/180) - PR: Add QtCore.__version__ for PySide2 ([178](https://github.com/spyder-ide/qtpy/issues/178))
* [PR 179](https://github.com/spyder-ide/qtpy/pull/179) - PR: Add QtQuickWidgets

In this release 3 pull requests were closed.


----


## Version 1.5.2 (2018-10-20)


### Pull Requests Merged

* [PR 175](https://github.com/spyder-ide/qtpy/pull/175) - PR: Fix tests
* [PR 174](https://github.com/spyder-ide/qtpy/pull/174) - PR: Add support for PySide2.QtOpenGL

In this release 2 pull requests were closed.


----


## Version 1.5.1 (2018-09-18)

### Issues Closed

* [Issue 170](https://github.com/spyder-ide/qtpy/issues/170) - Can't catch PythonQtError ([PR 173](https://github.com/spyder-ide/qtpy/pull/173))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 173](https://github.com/spyder-ide/qtpy/pull/173) - PR: Make PythonQtError inherit from RuntimeError to be easily catchable ([170](https://github.com/spyder-ide/qtpy/issues/170))

In this release 1 pull request was closed.

----


## Version 1.5 (2018-08-25)

### New features

* Add support for QtLocation, QtMultimediaWidgets, QtQml, QtQuick,
  QtWebChannel, QtWebSockets and QtXmlPatterns.
* Raise an error when trying to use the wrong combination of macOS
  and Qt versions.

### Issues Closed

* [Issue 155](https://github.com/spyder-ide/qtpy/issues/155) - Add warnings for Qt 5.9 in macOS 10.9 and Qt 5.11 and macOS 10.11 ([PR 168](https://github.com/spyder-ide/qtpy/pull/168))
* [Issue 153](https://github.com/spyder-ide/qtpy/issues/153) - Shim PyQt5 ToPyDateTime for compatibility with PySide2 ([PR 169](https://github.com/spyder-ide/qtpy/pull/169))
* [Issue 123](https://github.com/spyder-ide/qtpy/issues/123) - Wrap QWebChannel module ([PR 157](https://github.com/spyder-ide/qtpy/pull/157))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 169](https://github.com/spyder-ide/qtpy/pull/169) - PR: Shim PyQt5 QDateTime.toPyDateTime to QDateTime.toPython for compatibility with PySide2 ([153](https://github.com/spyder-ide/qtpy/issues/153))
* [PR 168](https://github.com/spyder-ide/qtpy/pull/168) - PR: Raise error when trying to use the wrong combination of macOS and Qt versions ([155](https://github.com/spyder-ide/qtpy/issues/155))
* [PR 167](https://github.com/spyder-ide/qtpy/pull/167) - PR: Migrate to CircleCI 2.0
* [PR 163](https://github.com/spyder-ide/qtpy/pull/163) - PR: Add QtLocation
* [PR 162](https://github.com/spyder-ide/qtpy/pull/162) - PR: Update readme to remove funding appeal, harmonize with other readmes and minor fixes
* [PR 161](https://github.com/spyder-ide/qtpy/pull/161) - PR: Fix pyside2 wheels install
* [PR 157](https://github.com/spyder-ide/qtpy/pull/157) - PR: Add more Qt modules ([123](https://github.com/spyder-ide/qtpy/issues/123))

In this release 7 pull requests were closed.


----


## Version 1.4.2 (2018-05-06)

### Issues Closed

* [Issue 150](https://github.com/spyder-ide/qtpy/issues/150) - PySide2-5.11 alpha2 compatibility ([PR 151](https://github.com/spyder-ide/qtpy/pull/151))
* [Issue 144](https://github.com/spyder-ide/qtpy/issues/144) - ValueError: API 'QString' has already been set to version 1 at line 141 in __init__.py file. ([PR 152](https://github.com/spyder-ide/qtpy/pull/152))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 152](https://github.com/spyder-ide/qtpy/pull/152) - PR: Catch ValueError when trying to set sip API ([144](https://github.com/spyder-ide/qtpy/issues/144))
* [PR 151](https://github.com/spyder-ide/qtpy/pull/151) - PR: Add a preventive change for PySide-5.11a2 ([150](https://github.com/spyder-ide/qtpy/issues/150))
* [PR 149](https://github.com/spyder-ide/qtpy/pull/149) - PR: Use Qt official wheels to run tests for PySide2
* [PR 148](https://github.com/spyder-ide/qtpy/pull/148) - PR: Remove internal conda recipe

In this release 4 pull requests were closed.


----


## Version 1.4.1 (2018-04-28)

### New features

* Show a warning when QT_API is changed automatically by qtpy.

### Issues Closed

* [Issue 145](https://github.com/spyder-ide/qtpy/issues/145) - Raise a warning if QT_API value is changed automatically ([PR 146](https://github.com/spyder-ide/qtpy/pull/146))
* [Issue 142](https://github.com/spyder-ide/qtpy/issues/142) - On OSX qtpy applications are forcing discrete graphics ([PR 143](https://github.com/spyder-ide/qtpy/pull/143))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 147](https://github.com/spyder-ide/qtpy/pull/147) - PR: Add better compatibility with PySide2
* [PR 146](https://github.com/spyder-ide/qtpy/pull/146) - PR: Add a warning if API is changed automatically ([145](https://github.com/spyder-ide/qtpy/issues/145))
* [PR 143](https://github.com/spyder-ide/qtpy/pull/143) - PR: Avoid using PyQt5.Qt, which imports unneeded stuff and forces discrete GPU on OSX ([142](https://github.com/spyder-ide/qtpy/issues/142))

In this release 3 pull requests were closed.


----


## Version 1.4 (2018-03-11)

### New features

* Add support for QtHelp and QtSql
* Use already imported bindings

### Issues Closed

* [Issue 138](https://github.com/spyder-ide/qtpy/issues/138) - If one binding has already been imported, then qtpy should just use it ([PR 139](https://github.com/spyder-ide/qtpy/pull/139))
* [Issue 135](https://github.com/spyder-ide/qtpy/issues/135) - Add Wrapper for QtSql [feature request] ([PR 136](https://github.com/spyder-ide/qtpy/pull/136))
* [Issue 131](https://github.com/spyder-ide/qtpy/issues/131) - Methods missing from QStandardPaths when QT_API=pyqt4
* [Issue 127](https://github.com/spyder-ide/qtpy/issues/127) - Add Wrapper for QtHelp [feature request] ([PR 128](https://github.com/spyder-ide/qtpy/pull/128))

In this release 4 issues were closed.

### Pull Requests Merged

* [PR 140](https://github.com/spyder-ide/qtpy/pull/140) - PR: Pin PyQt5 to 5.9.2 in CircleCI because 5.10 is generating segfaults
* [PR 139](https://github.com/spyder-ide/qtpy/pull/139) - PR: If a Qt binding is already imported, then use it. ([138](https://github.com/spyder-ide/qtpy/issues/138))
* [PR 136](https://github.com/spyder-ide/qtpy/pull/136) - PR: Add QtSql wrapper (incl. test) ([135](https://github.com/spyder-ide/qtpy/issues/135))
* [PR 132](https://github.com/spyder-ide/qtpy/pull/132) - PR: Changes to QDesktop split 
* [PR 128](https://github.com/spyder-ide/qtpy/pull/128) - PR: Add QtHelp Wrapper ([127](https://github.com/spyder-ide/qtpy/issues/127))

In this release 5 pull requests were closed.


----


## Version 1.3.1 (2017-08-21)

### Bugs fixed

**Issues**

* [Issue 129](https://github.com/spyder-ide/qtpy/issues/129) - Spurious cache files in PyPI tarball
* [Issue 119](https://github.com/spyder-ide/qtpy/issues/119) - Importing qtpy should not raise exceptions

In this release 2 issues were closed

**Pull requests**

* [PR 130](https://github.com/spyder-ide/qtpy/pull/130) - PR: No cache files included in the release tarball
* [PR 126](https://github.com/spyder-ide/qtpy/pull/126) - PR: Remove Quantified Code badge because the service doesn't exist anymore
* [PR 121](https://github.com/spyder-ide/qtpy/pull/121) - PR: Warn if QHeaderView deprecated methods are used

In this release 3 pull requests were merged


----


## Version 1.3 (2017-08-12)

### New features

* Add support for PySide2 and PyQt 4.6

### Bugs fixed

**Issues**

* [Issue 124](https://github.com/spyder-ide/qtpy/issues/124) - Typo in readme title
* [Issue 111](https://github.com/spyder-ide/qtpy/issues/111) - Update Readme for 1.3 release
* [Issue 110](https://github.com/spyder-ide/qtpy/issues/110) - Add tests for untested modules
* [Issue 101](https://github.com/spyder-ide/qtpy/issues/101) - Missing: QtOpenGL Module
* [Issue 89](https://github.com/spyder-ide/qtpy/issues/89) - QDesktopServices split into QDesktopServices and QStandardPaths
* [Issue 57](https://github.com/spyder-ide/qtpy/issues/57) - qInstallMessageHandler <-> qInstallMsgHandler
* [Issue 15](https://github.com/spyder-ide/qtpy/issues/15) - Feature Request: PySide2 support

In this release 7 issues were closed

**Pull requests**

* [PR 125](https://github.com/spyder-ide/qtpy/pull/125) - PR: Fix typo in Readme.
* [PR 117](https://github.com/spyder-ide/qtpy/pull/117) - PR: Add compatibility for the rename of qInstallMsgHandler to qInstallMessageHandler
* [PR 115](https://github.com/spyder-ide/qtpy/pull/115) - PR: Update Readme to reflect that we actually use the PySide2 layout
* [PR 114](https://github.com/spyder-ide/qtpy/pull/114) - PR: Update Readme to mention that we now support PySide2.
* [PR 113](https://github.com/spyder-ide/qtpy/pull/113) - PR: Add tests for Qtdesigner, QtNetwork, QtPrintSupport, QtSvg and QtTest.
* [PR 112](https://github.com/spyder-ide/qtpy/pull/112) - PR: Follow QStandardPaths location in Qt5 for PyQt4/PySide
* [PR 109](https://github.com/spyder-ide/qtpy/pull/109) - PR: Add a coveragerc file
* [PR 106](https://github.com/spyder-ide/qtpy/pull/106) - PR: Add support for PyQt 4.6
* [PR 102](https://github.com/spyder-ide/qtpy/pull/102) - PR: Add a new QtOpenGL module
* [PR 84](https://github.com/spyder-ide/qtpy/pull/84) - PR: Add PySide2 support

In this release 10 pull requests were merged


----


## Version 1.2.1 (2017/01/21)

### Bugs fixed

**Pull requests**

* [PR 98](https://github.com/spyder-ide/qtpy/pull/98) - PR: Don't use Travis to test macOS because it slows down the entire spyder-ide organization
* [PR 97](https://github.com/spyder-ide/qtpy/pull/97) - PR: Update Appveyor badge in Readme because of moving to an org account
* [PR 94](https://github.com/spyder-ide/qtpy/pull/94) - PR: Include test suite in sdist

In this release 3 pull requests were merged


----


## Version 1.2 (2017/01/08)

### New features

* Add support for QtMultimedia
* Use relative imports so its vendored more easily

### Bugs fixed

**Issues**

* [Issue 83](https://github.com/spyder-ide/qtpy/issues/83) - Include core doc files in PyPi releases
* [Issue 78](https://github.com/spyder-ide/qtpy/issues/78) - Request for a new bugfix release
* [Issue 75](https://github.com/spyder-ide/qtpy/issues/75) - Missing copyright headers
* [Issue 67](https://github.com/spyder-ide/qtpy/issues/67) - uic.loadUiType is missing
* [Issue 64](https://github.com/spyder-ide/qtpy/issues/64) - QHeaderView.setSectionResizeMode
* [Issue 49](https://github.com/spyder-ide/qtpy/issues/49) - QtMultimedia support

In this release 6 issues were closed

**Pull requests**

* [PR 93](https://github.com/spyder-ide/qtpy/pull/93) - Restore uic full namespace for PyQt5 and PyQt4
* [PR 92](https://github.com/spyder-ide/qtpy/pull/92) - Add missing copyright header in _patch/qheaderview.py
* [PR 91](https://github.com/spyder-ide/qtpy/pull/91) - Use star imports in QtSvg again instead of direct ones (reverts PR #55)
* [PR 88](https://github.com/spyder-ide/qtpy/pull/88) - PR: Add manifest
* [PR 74](https://github.com/spyder-ide/qtpy/pull/74) - Move QStringListModel to QtCore
* [PR 71](https://github.com/spyder-ide/qtpy/pull/71) - PR: Use relative imports so its vendored more easily
* [PR 65](https://github.com/spyder-ide/qtpy/pull/65) - Introduce renamed methods of QHeaderView in PyQt4 and PySide
* [PR 59](https://github.com/spyder-ide/qtpy/pull/59) - Don't install qtpy as a conda package in CircleCI
* [PR 58](https://github.com/spyder-ide/qtpy/pull/58) - Remove reference to how qtpy is pronounced in README
* [PR 55](https://github.com/spyder-ide/qtpy/pull/55) - PR: Add explicit imports to QtSvg module
* [PR 50](https://github.com/spyder-ide/qtpy/pull/50) - Add support for QtMultimedia

In this release 11 pull requests were merged


----


## Version 1.1.2 (2016-08-08)

### Bugfixes

**Pull requests**

* [PR 54](https://github.com/spyder-ide/qtpy/pull/54) - PR: Fix/ci
* [PR 53](https://github.com/spyder-ide/qtpy/pull/53) - PR: Move tests to module so they can be run when installed
* [PR 52](https://github.com/spyder-ide/qtpy/pull/52) - PR: Update readme
* [PR 51](https://github.com/spyder-ide/qtpy/pull/51) - PR: Add circle ci
* [PR 47](https://github.com/spyder-ide/qtpy/pull/47) - Remove PyQt variant symbols from QtCore
* [PR 46](https://github.com/spyder-ide/qtpy/pull/46) - del QtWidgets.QStyleOptionViewItemV4
* [PR 45](https://github.com/spyder-ide/qtpy/pull/45) - Allow QT_API values that are not completely in lower case

In this release 7 pull requests were merged


----


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
