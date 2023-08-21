import textwrap

from . import core
from . import diffparse
from . import utils
from .i18n import N_
from .interaction import Interaction
from .models import prefs


def wrap_comment(context, text):
    indent = prefs.comment_char(context) + ' '
    return (
        textwrap.fill(
            text,
            width=80,
            initial_indent=indent,
            subsequent_indent=indent,
        )
        + '\n'
    )


def strip_comments(context, text):
    comment_char = prefs.comment_char(context)
    return '\n'.join(
        line for line in text.split('\n') if not line.startswith(comment_char)
    )


def patch_edit_header(context, *, reverse, apply_to_worktree):
    if apply_to_worktree:
        header = N_(
            'Edit the following patch, which will then be applied to the worktree to'
            ' revert the changes:'
        )
    else:
        if reverse:
            header = N_(
                'Edit the following patch, which will then be applied to the staging'
                ' area to unstage the changes:'
            )
        else:
            header = N_(
                'Edit the following patch, which will then be applied to the staging'
                ' area to stage the changes:'
            )
    return wrap_comment(context, header)


def patch_edit_footer(context):
    parts = [
        '---',
        N_(
            "To avoid applying removal lines ('-'), change them to context lines (' ')."
        ),
        N_("To avoid applying addition lines ('+'), delete them."),
        N_('To abort applying this patch, remove all lines.'),
        N_("Lines starting with '%s' will be ignored.") % prefs.comment_char(context),
        N_(
            'It is not necessary to update the hunk header lines as they will be'
            ' regenerated automatically.'
        ),
    ]
    return ''.join(wrap_comment(context, part) for part in parts)


def edit_patch(patch, encoding, context, *, reverse, apply_to_worktree):
    patch_file_path = utils.tmp_filename('edit', '.patch')
    try:
        content_parts = [
            patch_edit_header(
                context, reverse=reverse, apply_to_worktree=apply_to_worktree
            ),
            patch.as_text(file_headers=False),
            patch_edit_footer(context),
        ]
        core.write(patch_file_path, ''.join(content_parts), encoding=encoding)
        status, _, _ = core.run_command(
            [*utils.shell_split(prefs.editor(context)), patch_file_path]
        )
        if status == 0:
            patch_text = strip_comments(
                context, core.read(patch_file_path, encoding=encoding)
            )
        else:
            Interaction.log(
                N_('Editor returned %s exit code.  Not applying patch.') % status
            )
            patch_text = ''
        return diffparse.Patch.parse(patch.filename, patch_text)
    finally:
        core.unlink(patch_file_path)
