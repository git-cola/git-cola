git-cola v1.3.8 Release Notes
=============================

Usability, bells and whistles
-----------------------------
* Fresh and tasty SVG logos
* Branch review mode for reviewing topic branches
* Diff modes for diffing between tags, branches, or arbitrary diff expressions.
* The push dialog now selects the current branch by default. This is to prepare for upcoming git changes where git push will warn and later refuse to push when git-push is run without arguments
* Support 'open' and 'clone' commands on Windows
* Allow saving cola UI layouts
* Re-enable double-click-to-stage for unmerged entries. Disabling it for unmerged items was inconsistent, though safer
* Show diffs when navigating the status tree with the keyboard

Packaging
---------
* Work around pyuic4 bugs in the setup.py build script
* Mac OSX application bundles now available for download
