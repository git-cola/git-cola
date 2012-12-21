import os
import subprocess
from cola import utils


class Interaction(object):
    """Prompts the user and answers questions"""

    VERBOSE = bool(os.getenv('GIT_COLA_VERBOSE'))

    @staticmethod
    def information(title,
                    message=None, details=None, informative_text=None):
        if message is None:
            message = title
        scope = dict(locals())
        scope['title_dashes'] = '-' * len(title)
        scope['details'] = details and '\n'+details or ''
        scope['informative_text'] = (informative_text and
                '\n'+informative_text or '')
        print("""
%(title)s
%(title_dashes)s
%(message)s%(details)s%(informative_text)s""" % scope)

    @classmethod
    def critical(cls, title, message=None, details=None):
        """Show a warning with the provided title and message."""
        cls.information(title, message=message, details=details)

    @classmethod
    def confirm(cls, title, text, informative_text, ok_text,
                icon=None, default=True):

        cls.information(title, message=text,
                        informative_text=informative_text)
        if default:
            prompt = '%s? [Y/n]:' % ok_text
        else:
            prompt = '%s? [y/N]: ' % ok_text
        answer = raw_input(prompt)
        if answer == '':
            return default
        return answer.lower().startswith('y')

    @classmethod
    def question(cls, title, message, default=True):
        return cls.confirm(title, message, '',
                           ok_text='Continue', default=default)

    @classmethod
    def run_command(cls, title, cmd):
        cls.log('$ ' + subprocess.list2cmdline(cmd))
        status, out, err = utils.run_command(cmd)
        cls.log_status(status, out, err)

    @classmethod
    def confirm_config_action(cls, name, opts):
        return cls.confirm('Run %s' % name,
                           'You are about to run "%s".' % name,
                           ok_text='Run')

    @classmethod
    def log_status(cls, status, out, err=None):
        msg = ('%s%sexit code %s' %
                ((out and (out+'\n') or ''),
                 (err and (err+'\n') or ''),
                 status))
        cls.log(msg)

    @classmethod
    def log(cls, message):
        if cls.VERBOSE:
            print(message)
