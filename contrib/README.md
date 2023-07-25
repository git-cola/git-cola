# Git Cola Accessories

## Bash shell completion

The [git-cola-completion.bash](git-cola-complation.bash) script can be sourced
by `.bashrc` or `/etc/bash_completion.d` to provide completion for `git cola`
on the command-line.

Git Cola's bash completion script requires that you have Git's
[git-completion.bash](https://github.com/git/git/blob/master/contrib/completion/git-completion.bash)
setup via your `.bashrc`. Git Cola's completion script is a plugin / extension
to Git's `git-completion.bash`.


## Zsh shell completion

* The [_git-cola zsh completion script](_git-cola) is a completion script for `zsh`.
This script is only able to offer completions for the dashed `git-cola` command.
Completions for `git cola` are not currently available.

To use it, copy `_git-cola` to the location where you keep your zsh completion scripts
(ie. `mkdir  -p ~/.config/zsh/completion && cp _git-cola ~/.config/zsh/completion`)
and then add the directory to zsh's `$fpath` in your `~/.zshrc` before initializing
the completion system using `compinit`:

    # ~/.zshrc shell completion setup
    fpath=(~/.config/zsh/completion $fpath)
    autoload -U +X compinit
    compinit


## macOS-related files

The [darwin](darwin) directory contains resources for creating Mac OS X
git-cola.app application bundles.


## Windows-related files

The [win32](win32) directory contains packaging-related utilities and
resources for the Windows installer.  If you're developing git-cola on
Windows then you can use the `cola` and `dag` helper scripts to launch
git-cola from your source tree without needing to have python.exe in your path.
