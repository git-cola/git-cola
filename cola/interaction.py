from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys

from . import core
from .i18n import N_


# The dependency injection calls to install() in ColaApplication's constructor
# triggers method-already-defined pylint warnings.  Silence that warning.
#
# pylint: disable=function-redefined
class Interaction(object):
    """Prompts the user and answers questions"""

    VERBOSE = bool(os.getenv('GIT_COLA_VERBOSE'))

    @classmethod
    def command(cls, title, cmd, status, out, err):
        """Log a command and display error messages on failure"""
        cls.log_status(status, out, err)
        if status != 0:
            cls.command_error(title, cmd, status, out, err)

    @classmethod
    def command_error(cls, title, cmd, status, out, err):
        """Display an error message for a failed command"""
        core.print_stderr(title)
        core.print_stderr('-' * len(title))
        core.print_stderr(cls.format_command_status(cmd, status))
        core.print_stdout('')
        if out:
            core.print_stdout(out)
        if err:
            core.print_stderr(err)

    @staticmethod
    def format_command_status(cmd, status):
        return N_('"%(command)s" returned exit status %(status)d') % dict(
            command=cmd, status=status
        )

    @staticmethod
    def format_out_err(out, err):
        """Format stdout and stderr into a single string"""
        details = out or ''
        if err:
            if details and not details.endswith('\n'):
                details += '\n'
            details += err
        return details

    @staticmethod
    def information(title, message=None, details=None, informative_text=None):
        if message is None:
            message = title
        scope = {}
        scope['title'] = title
        scope['title_dashes'] = '-' * len(title)
        scope['message'] = message
        scope['details'] = ('\n' + details) if details else ''
        scope['informative_text'] = (
            ('\n' + informative_text) if informative_text else ''
        )
        sys.stdout.write(
            """
%(title)s
%(title_dashes)s
%(message)s%(informative_text)s%(details)s\n"""
            % scope
        )
        sys.stdout.flush()

    @classmethod
    def critical(cls, title, message=None, details=None):
        """Show a warning with the provided title and message."""
        cls.information(title, message=message, details=details)

    @classmethod
    def confirm(
        cls,
        title,
        text,
        informative_text,
        ok_text,
        icon=None,
        default=True,
        cancel_text=None,
    ):

        cancel_text = cancel_text or 'Cancel'
        icon = icon or '?'

        cls.information(title, message=text, informative_text=informative_text)
        if default:
            prompt = '%s? [Y/n] ' % ok_text
        else:
            prompt = '%s? [y/N] ' % ok_text
        sys.stdout.write(prompt)
        sys.stdout.flush()
        answer = sys.stdin.readline().strip()
        if answer:
            result = answer.lower().startswith('y')
        else:
            result = default
        return result

    @classmethod
    def question(cls, title, message, default=True):
        return cls.confirm(title, message, '', ok_text=N_('Continue'), default=default)

    @classmethod
    def run_command(cls, title, cmd):
        cls.log('# ' + title)
        cls.log('$ ' + core.list2cmdline(cmd))
        status, out, err = core.run_command(cmd)
        cls.log_status(status, out, err)
        return status, out, err

    @classmethod
    def confirm_config_action(cls, _context, name, _opts):
        return cls.confirm(
            N_('Run %s?') % name,
            N_('Run the "%s" command?') % name,
            '',
            ok_text=N_('Run'),
        )

    @classmethod
    def log_status(cls, status, out, err=None):
        msg = ((out + '\n') if out else '') + ((err + '\n') if err else '')
        cls.log(msg)
        cls.log('exit status %s' % status)

    @classmethod
    def log(cls, message):
        if cls.VERBOSE:
            core.print_stdout(message)

    @classmethod
    def save_as(cls, filename, title):
        if cls.confirm(title, 'Save as %s?' % filename, '', ok_text='Save'):
            return filename
        return None

    @staticmethod
    def async_command(title, command, runtask):
        pass

    @classmethod
    def choose_ref(cls, _context, title, button_text, default=None, icon=None):
        icon = icon or '?'
        cls.information(title, button_text)
        return sys.stdin.readline().strip() or default
