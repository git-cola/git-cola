Keyboard Shortcuts
==================
`git cola` has many useful keyboard shortcuts.

Learn about them by either pressing the ``?`` key,
choosing ``Help -> Keyboard shortcuts`` from the main menu,
or by consulting the
`git cola keyboard shortcuts reference <../hotkeys.html>`_.

Apply Patches using `git am`
============================
Use the ``File -> Apply Patches`` menu item to begin applying patches.

Dragging and dropping patches onto the `git cola` interface
adds the patches to the list of patches to apply using
`git am <http://schacon.github.com/git/git-am.html>`_.

You can drag either a set of patches or a directory containing patches.
Patches can be sorted using in the interface and are applied in the
same order as is listed in the list.

When a directory is dropped `git cola` walks the directory
tree in search of patches.  `git cola` sorts the list of
patches after they have all been found.  This allows you
to control the order in which patchs are applied by placing
patchsets into alphanumerically-sorted directories.

Custom GUI Layouts
==================
`git cola` remembers modifications to the layout and arrangement
of tools within the `git cola` interface.  Changes are saved
and restored at application shutdown/startup.

`git cola` can be configured to not save custom layouts--
simply uncheck the `Save Window Settings` option in the
`git cola` preferences.
