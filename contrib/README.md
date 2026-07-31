# Git Fanta Accessories

## Bash shell completion

The [git-fanta-completion.bash](git-fanta-complation.bash) script can be sourced
by `.bashrc` or `/etc/bash_completion.d` to provide completion for `git fanta`
on the command-line.

Git Fanta's bash completion script requires that you have Git's
[git-completion.bash](https://github.com/git/git/blob/master/contrib/completion/git-completion.bash)
setup via your `.bashrc`. Git Fanta's completion script is a plugin / extension
to Git's `git-completion.bash`.


## Zsh shell completion

* The [_git-fanta zsh completion script](_git-fanta) is a completion script for `zsh`.
This script is only able to offer completions for the dashed `git-fanta` command.
Completions for `git fanta` are not currently available.

To use it, copy `_git-fanta` to the location where you keep your zsh completion scripts
(ie. `mkdir  -p ~/.config/zsh/completion && cp _git-fanta ~/.config/zsh/completion`)
and then add the directory to zsh's `$fpath` in your `~/.zshrc` before initializing
the completion system using `compinit`:

    # ~/.zshrc shell completion setup
    fpath=(~/.config/zsh/completion $fpath)
    autoload -U +X compinit
    compinit


## macOS-related files

The [darwin](darwin) directory contains resources for creating Mac OS X
git-fanta.app application bundles.


## Windows-related files

The [win32](win32) directory contains packaging-related utilities and
resources for the Windows installer.  If you're developing git-fanta on
Windows then you can use the `cola` and `dag` helper scripts to launch
git-fanta from your source tree without needing to have python.exe in your path.
