git-cola v1.3.6 Release Notes
=============================

Subsystems
----------
* Support Kompare in git-difftool
* Add a unique configuration namespace for git-difftool
* The diff.tool git-config value defines the default diff tool

Usability, bells and whistles
-----------------------------
* The stash dialog allows passing the --keep-index option
* Warn when amending a published commit
* Simplify the file-across-revisions comparison dialog
* Select 'origin' by default in fetch/push/pull
* Remove the search field from the log widget
* The log window moved into a drawer widget at the bottom of the UI
* Log window display can be configured with cola.showoutput = {never, always, errors}. 'errors' is the default

Developer
---------
* Improve nose unittest usage

Packaging
---------
* Add a Windows/msysGit installer
* Include private versions of simplejson and jsonpickle for ease of installation and development
