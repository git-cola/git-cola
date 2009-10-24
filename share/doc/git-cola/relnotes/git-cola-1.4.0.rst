git-cola v1.4.0 Release Notes
=============================

This release focuses on a redesign of the git-cola user interface,
a tags interface, and better integration of the 'cola classic' widget.
A flexible interface based on configurable docks is used to manage the
various cola widgets.

Usability, bells and whistles
-----------------------------
* New main GUI is flexible and user-configurable
* Individual widgets can be detached and rearranged arbitrarily
* Add an interface for creating tags
* Provide a fallback SSH_ASKPASS implementation to prompt for SSH passwords on fetch/push/pull
* The commit message editor displays the current row/column and warns when lines get too long
* The cola classic widget displays upstream changes
* 'git cola --classic' launches cola classic in standalone mode
* Provide more information in log messages

Fixes
-----
* Inherit the window manager's font settings
* Miscellaneous PyQt4 bug fixes and workarounds

Developer
---------
* Removed all usage of Qt Designer .ui files
* Simpler model/view architecture
* Selection now lives in the model
* Centralized model notifications are used to keep views in sync
* The git command class was made thread-safe
* Less coupling between model and view actions
* The status view was rewritten to use the MVC architecture
* Added more documentation and tests
