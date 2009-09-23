from PyQt4.QtCore import SIGNAL

_signals = dict(add_signoff = SIGNAL('add_signoff'),
                amend = SIGNAL('amend'),
                amend_mode = SIGNAL('amend_mode'),
                apply_diff_selection = SIGNAL('apply_diff_selection'),
                branch_mode = SIGNAL('branch_mode'),
                commit = SIGNAL('commit'),
                edit = SIGNAL('edit'),
                checkout = SIGNAL('checkout'),
                delete = SIGNAL('delete'),
                diff = SIGNAL('diff'),
                diff_expr_mode = SIGNAL('diff_expr_mode'),
                diff_mode = SIGNAL('diff_mode'),
                diff_staged = SIGNAL('diff_staged'),
                diff_text = SIGNAL('diff_text'),
                diffstat = SIGNAL('diffstat'),
                difftool = SIGNAL('difftool'),
                editor_text = SIGNAL('editor_text'),
                grep = SIGNAL('grep'),
                information = SIGNAL('information'),
                log_text = SIGNAL('log_text'),
                load_commit_message = SIGNAL('load_commit_message'),
                mergetool = SIGNAL('mergetool'),
                mode = SIGNAL('mode'),
                modified_summary = SIGNAL('modified_summary'),
                open_repo = SIGNAL('open_repo'),
                redo = SIGNAL('redo'),
                rescan = SIGNAL('rescan'),
                reset_mode = SIGNAL('reset_mode'),
                review_branch_mode = SIGNAL('review_branch_mode'),
                show_untracked = SIGNAL('show_untracked'),
                stage = SIGNAL('stage'),
                stage_diffs = SIGNAL('stage_diffs'),
                stage_modified = SIGNAL('stage_modified'),
                stage_untracked = SIGNAL('stage_untracked'),
                staged_summary = SIGNAL('staged_summary'),
                unmerged_summary = SIGNAL('unmerged_summary'),
                undo = SIGNAL('undo'),
                undo_diffs = SIGNAL('undo_diffs'),
                unstage = SIGNAL('unstage'),
                unstage_diffs = SIGNAL('unstage_diffs'),
                unstage_all = SIGNAL('unstage_all'),
                untracked_summary = SIGNAL('untracked_summary'))

_signals_names = {}
for name, signal in _signals.iteritems():
    _signals_names[signal] = name

# Bring signals into the module namespace
globals().update(_signals)

def name(signal):
    """Return the name for a signal."""
    return _signals_names.get(signal, 'no-name')
