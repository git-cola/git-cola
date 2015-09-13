# This is a git-cola extension for Git's git-completion.bash script
#
# This script must be sourced *after* Git's git-completion.bash script.
# See git.git's contrib/completion/git-completion.bash for details.
#
# Completion is provided for "git cola ..." and "git dag ..." via the
# _git_cola() and _git_dag() functions.

__git_cola_common_options="--prompt --repo --version"
__git_cola_subcommands_list=

__git_cola_common_opts () {
	__gitcomp "$__git_cola_common_options $1"
}

_git_cola () {
	__git_has_doubledash && return

	if test -z "$__git_cola_subcommands_list"
	then
		__git_cola_subcommands_list=$(
			git cola --help-commands |
			grep '^    [a-z]' |
			grep -v cola |
			cut -d' ' -f5)
	fi

	local subcommand=$(__git_find_on_cmdline "$__git_cola_subcommands_list")

	case "$prev" in
	--repo)
		return
		;;
	esac

	if test -z "$subcommand"
	then
		__gitcomp "
			$__git_cola_subcommands_list
			$__git_cola_common_options
			--amend
			--help-commands
			--status-filter
		"
		return
	fi

	case "$subcommand" in
	am)
		return
		;;
	dag)
		_git_dag "$@"
		return
		;;
	archive|diff|merge)
		__git_complete_revlist
		__git_cola_common_opts
		;;
	grep)
		# do nothing
		;;
	pull)
		__git_cola_common_opts --rebase
		;;
	rebase)
		case "$prev" in
		--exec)
			return
			;;
		--whitespace)
			__gitcomp "nowarn warn fix error error-all"
			return
			;;
		--strategy)
			__gitcomp "resolve recursive octopus ours subtree"
			return
			;;
		--strategy-option)
			__gitcomp "ours theirs patience
				diff-algorithm=patience
				diff-algorithm=minimal
				diff-algorithm=histogram
				diff-algorithm=myers
				ignore-all-space
				ignore-space-at-eol
				ignore-space-change
				renormalize
				no-renormalize
				rename-threshold=
				subtree=
				"
			return
			;;
		esac

		__git_complete_revlist
		__git_cola_common_opts "
			--abort
			--autostash
			--autosquash
			--committer-date-is-author-date
			--continue
			--ignore-date
			--ignore-whitespace
			--edit-todo
			--exec
			--force-rebase
			--fork-point
			--merge
			--no-autosquash
			--no-ff
			--no-stat
			--onto
			--preserve-merges
			--quiet
			--rerere-autoupdate
			--root
			--skip
			--stat
			--stop
			--strategy
			--strategy-option
			--verbose
			--verify
			--whitespace
		"
		;;
	tag)
		case "$cword" in
		3)
			# do nothing
			;;
		*)
			__git_complete_revlist
			;;
		esac
		;;
	*)
		__git_cola_common_opts
		;;
	esac
}

_git_dag () {
	__git_has_doubledash && return

	if test "$prev" = "--max-count"
	then
		return
	fi
	__git_cola_common_opts --max-count
	__git_complete_revlist
}
