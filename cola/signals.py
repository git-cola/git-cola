from PyQt4.QtCore import SIGNAL

_signals = dict(amend = SIGNAL('amend'),
                amend_mode = SIGNAL('amend_mode'),
                edit = SIGNAL('edit'),
                checkout = SIGNAL('checkout'),
                delete = SIGNAL('delete'),
                diff = SIGNAL('diff'),
                diff_staged = SIGNAL('diff_staged'),
                diffstat = SIGNAL('diffstat'),
                difftool = SIGNAL('difftool'),
                information = SIGNAL('information'),
                log_text = SIGNAL('log_text'),
                mergetool = SIGNAL('mergetool'),
                modified_summary = SIGNAL('modified_summary'),
                redo = SIGNAL('redo'),
                reset_mode = SIGNAL('reset_mode'),
                show_untracked = SIGNAL('show_untracked'),
                stage = SIGNAL('stage'),
                stage_diffs = SIGNAL('stage_diffs'),
                staged_summary = SIGNAL('staged_summary'),
                text = SIGNAL('text'),
                unmerged_summary = SIGNAL('unmerged_summary'),
                undo = SIGNAL('undo'),
                undo_diffs = SIGNAL('undo_diffs'),
                unstage = SIGNAL('unstage'),
                unstage_diffs = SIGNAL('unstage_diffs'),
                untracked_summary = SIGNAL('untracked_summary'))

_signals_names = {}
for name, signal in _signals.iteritems():
    _signals_names[signal] = name

# Bring signals into the module namespace
globals().update(_signals)

def name(signal):
    """Return the name for a signal."""
    return _signals_names.get(signal, 'no-name')
