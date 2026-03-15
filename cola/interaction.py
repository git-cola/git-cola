from __future__ import annotations
import os
import sys
from typing import TYPE_CHECKING

from . import core
from .i18n import N_

if TYPE_CHECKING:
    from .types import TextType


class Interaction:
    """Prompts the user and answers questions"""

    VERBOSE = bool(os.getenv('GIT_COLA_VERBOSE'))

    @classmethod
    def command(
        cls,
        title: TextType,
        cmd: list[TextType] | str,
        status: int,
        out: TextType,
        err: TextType,
    ) -> None:
        """Log a command and display error messages on failure"""
        cls.log_status(status, out, err)
        if status != 0:
            cls.command_error(title, cmd, status, out, err)

    @classmethod
    def command_error(
        cls,
        title: str,
        cmd: list[TextType] | str,
        status: int,
        out: TextType,
        err: TextType,
    ) -> None:
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
    def format_command_status(cmd: list[TextType] | str, status: int) -> str:
        return N_('"%(command)s" returned exit status %(status)d') % {
            'command': cmd,
            'status': status,
        }

    @staticmethod
    def format_out_err(out: core.UStr, err: core.UStr) -> str:
        """Format stdout and stderr into a single string"""
        details = out or ''
        if err:
            if details and not details.endswith('\n'):
                details += '\n'
            details += err
        return details

    @staticmethod
    def information(
        title: str,
        message: str | None = None,
        details: str | None = None,
        informative_text: str | None = None,
    ) -> None:
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
    def critical(
        cls, title: str, message: str | None = None, details: str | None = None
    ) -> None:
        """Show a warning with the provided title and message."""
        cls.information(title, message=message, details=details)

    @classmethod
    def confirm(
        cls,
        title: str,
        text: str,
        informative_text: str,
        ok_text: str,
        icon=None,
        default: bool = True,
        cancel_text: str | None = None,
    ) -> bool:
        cancel_text = cancel_text or 'Cancel'
        icon = icon or '?'

        cls.information(title, message=text, informative_text=informative_text)
        if default:
            prompt = '%s? [Y/n] ' % ok_text
        else:
            prompt = '%s? [y/N] ' % ok_text
        sys.stdout.write(prompt)
        sys.stdout.flush()
        answer: str = sys.stdin.readline().strip()
        if answer:
            result = answer.lower().startswith('y')
        else:
            result = default
        return result

    @classmethod
    def question(cls, title: str, message: str, default: bool = True) -> bool:
        return cls.confirm(title, message, '', ok_text=N_('Continue'), default=default)

    @classmethod
    def run_command(
        cls, title: str, cmd: list[str]
    ) -> tuple[int, core.UStr, core.UStr]:
        cls.log('# ' + title)
        cls.log('$ ' + core.list2cmdline(cmd))
        status, out, err = core.run_command(cmd)
        cls.log_status(status, out, err)
        return status, out, err

    @classmethod
    def confirm_config_action(cls, _context, name: str, _opts) -> bool:
        return cls.confirm(
            N_('Run %s?') % name,
            N_('Run the "%s" command?') % name,
            '',
            ok_text=N_('Run'),
        )

    @classmethod
    def log_status(
        cls, status: int, out: TextType, err: TextType | None = None
    ) -> None:
        """Emit status, out, and err into the log"""
        msg = ''
        if out:
            msg += out + '\n'
        if err:
            msg += err + '\n'
        cls.log(msg)
        cls.log('exit status %s' % status)

    @classmethod
    def log(cls, message: str) -> None:
        if cls.VERBOSE:
            core.print_stdout(message)

    @classmethod
    def save_as(cls, filename: str, title: str) -> str | None:
        if cls.confirm(title, 'Save as %s?' % filename, '', ok_text='Save'):
            return filename
        return None

    @staticmethod
    def async_task(title, cmd, runtask, func) -> None:
        pass

    @classmethod
    def choose_ref(
        cls,
        _context,
        title: str,
        button_text: str,
        default: str | None = None,
        icon=None,
    ) -> str:
        icon = icon or '?'
        cls.information(title, button_text)
        return sys.stdin.readline().strip() or default
