git-cola v1.3.9 Release Notes
=============================

Usability, bells and whistles
-----------------------------
* Add a "classic" view for browsing the entire repository
* Handle diff expressions with spaces
* Handle renamed files

Portability
-----------
* Handle carat '^' characters in diff expressions on Windows
* Workaround a PyQt 4.5/4.6 QThreadPool bug

Documentation
-------------
* Add keyboard shortcut documentation
* Add more API documentation

Fixes
-----
* Fix the diff expression used when reviewing branches
* Fix a bug when pushing branches
* Fix X11 warnings
* Fix interrupted system calls on Mac OS X
