git-cola v1.3.7 Release Notes
=============================

Subsystems
----------
* git-difftool is now an official git command as of git-v1.6.3.
* git-difftool learned --no-prompt / -y and a corresponding difftool.prompt configuration variable

Usability, bells and whistles
-----------------------------
* Warn when non-ffwd is used for push/pull
* Allow Ctrl+C to exit cola when run from the command line

Fixes
-----
* Support Unicode fonts
* Handle interrupted system calls

Developer
--------
* PEP-8-ify more of the cola code base
* Added more tests

Packaging
---------
* All resources are installed into $prefix/share/git-cola. Closes Debian bug #5199972
