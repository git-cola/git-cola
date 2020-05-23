# CONTRIBUTING GUIDELINES

Here are some guidelines for people who want to contribute their code
to this software.

## Make separate commits for logically separate changes.

## Run the pre-commit checks before committing

* `make check`

## Write tests

When adding new features or fixing defects, extend the unit tests to
cover the new behavior.  See the `tests/` directory for examples.
Find an appropriate test suite and extend it whenever possible.

## Be picky about whitespace

This project is very picky about code style.
The style here is the standard Python PEP-8 style:

http://www.python.org/dev/peps/pep-0008/

* Use the `make format` command to format the source code using `black`.

* Follow the same style as the existing code.

* Use 4-space indents.

* Use `variable_names_with_underscores`, AKA "snake case" naming.
  No camelCase.  The only exception is when overriding Qt functions.

* Do not introduce trailing whitespace.  The "Diff" viewer displays
  trailing whitespace in red, or you can use "git diff --check".

* If you use SublimeText, configure `newline_at_eof_on_save` to true.

https://robots.thoughtbot.com/no-newline-at-end-of-file

## Describe your changes well.

The first line of the commit message should be a short description (50
characters is the soft limit, see DISCUSSION in git-commit(1)), and
should skip the full stop.  It is also conventional in most cases to
prefix the first line with "area: " where the area is a filename or
identifier for the general area of the code being modified, e.g.

* push: allow pushing to multiple remotes

* grep: allow passing in command-line arguments

If in doubt which identifier to use, run "git log --no-merges" on the
files you are modifying to see the current conventions.

The body should provide a meaningful commit message, which:

* explains the problem the change tries to solve, iow, what is wrong
  with the current code without the change.

* justifies the way the change solves the problem, iow, why the
  result with the change is better.

* alternate solutions considered but discarded, if any.

Describe your changes in imperative mood, e.g. "make xyzzy do frotz"
instead of "[This patch] makes xyzzy do frotz" or "[I] changed xyzzy
to do frotz", as if you are giving orders to the codebase to change
its behaviour.  Try to make sure your explanation can be understood
without external resources. Instead of giving a URL to a mailing list
archive, summarize the relevant points of the discussion.

If you like, you can put extra tags at the end:

* "Reported-by:" is used to credit someone who found the bug that
  the patch attempts to fix.

* "Acked-by:" says that the person who is more familiar with the area
  the patch attempts to modify liked the patch.

* "Reviewed-by:", unlike the other tags, can only be offered by the
  reviewer and means that she is completely satisfied that the patch
  is ready for application.  It is usually offered only after a
  detailed review.

* "Tested-by:" is used to indicate that the person applied the patch
  and found it to have the desired effect.

You can also create your own tag or use one that's in common usage
such as "Thanks-to:", "Based-on-patch-by:", or "Helped-by:".

## Sign your work

To improve tracking of who did what, we've borrowed the
"sign-off" procedure from the Linux kernel project on patches
that are being emailed around.  Although core Git is a lot
smaller project it is a good discipline to follow it.

The sign-off is a simple line at the end of the explanation for
the patch, which certifies that you wrote it or otherwise have
the right to pass it on as an open-source patch.  The rules are
pretty simple: if you can certify the below:

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
are public and that a record of the contribution (including all
personal information I submit with it, including my sign-off) is
maintained indefinitely and may be redistributed consistent with
this project or the open source license(s) involved.

then you just add a line saying

Signed-off-by: Random J Developer <random@developer.example.org>

This line can be automatically added by Git if you run the git-commit
command with the -s option, or using the `Ctrl+i` hotkey in git-cola's
commit message editor.

Notice that you can place your own Signed-off-by: line when
forwarding somebody else's patch with the above rules for
D-C-O.  Indeed you are encouraged to do so.  Do not forget to
place an in-body "From: " line at the beginning to properly attribute
the change to its true author (see (2) above).

Also notice that a real name is used in the Signed-off-by: line. Please
don't hide your real name.

## Reporting Bugs

Please read [How to Report Bugs Effectively](http://www.chiark.greenend.org.uk/~sgtatham/bugs.html)
for some general tips on bug reporting.

## Internationalization and Localization

git-cola is translated to several languages.  When strings are presented to
the user they must use the `N_('<string>')` function so that `<string>` is
translated into a localized string.

The translation message files are the `*.po` files in the `po/` directory.
Adding a new translation entails creating a new language-specific `.po` file
and building the translation files using "make".  The `share/locale/`
directory tree is generated by "make" from the `po/*` source files.

When new (untranslated) strings are added to the project, the `git-cola.pot`
base template and the language-specific message files need to be updated with
the new strings.

To regenerate `git-cola.pot` and update `.po` files with new strings run:

    make pot

This will update `.po` files with untranslated strings which translators can
use to translate `git-cola`.

Untranslated strings are denoted by an empty "" string.

The `.mo` files have to be regenerated after each change by running:

    make mo

Alternate translations can be tested by setting `$LANG` when running, e.g.

    env LANG=zh_TW ./bin/git-cola

The [Gettext Language Code](https://www.gnu.org/software/gettext/manual/gettext.html#Language-Codes)
corresponds to the `.po` filename.  Country-specific suffixes use the
[Gettext country code](https://www.gnu.org/software/gettext/manual/gettext.html#Country-Codes).

We happily welcome pull requests with improvements to `git-cola`'s translations.

## Fork the repo on Github and create a pull request.
