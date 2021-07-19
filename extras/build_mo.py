"""build_mo command for setup.py"""
# pylint: disable=attribute-defined-outside-init,import-error,no-name-in-module
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import re
from distutils.core import Command
from distutils.dep_util import newer
from distutils.spawn import find_executable
from distutils import log

from . import build_util


class build_mo(Command):
    """Subcommand of build command: build_mo"""

    description = 'compile po files to mo files'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [
        ('build-dir=', 'd', 'Directory to build locale files'),
        ('output-base=', 'o', 'mo-files base name'),
        ('source-dir=', None, 'Directory with sources po files'),
        ('force', 'f', 'Force creation of mo files'),
        ('lang=', None, 'Comma-separated list of languages to process'),
    ]
    user_options = build_util.stringify_options(user_options)
    boolean_options = build_util.stringify_list(['force'])

    def initialize_options(self):
        self.build_dir = None
        self.output_base = None
        self.source_dir = None
        self.force = None
        self.lang = None

    def finalize_options(self):
        self.set_undefined_options('build', ('force', 'force'))
        self.prj_name = self.distribution.get_name()
        if self.build_dir is None:
            self.build_dir = os.path.join('share', 'locale')
        if not self.output_base:
            self.output_base = self.prj_name or 'messages'
        if self.source_dir is None:
            self.source_dir = 'po'
        if self.lang is None:
            if self.prj_name:
                re_po = re.compile(r'^(?:%s-)?([a-zA-Z_]+)\.po$' % self.prj_name)
            else:
                re_po = re.compile(r'^([a-zA-Z_]+)\.po$')
            self.lang = []
            for i in os.listdir(self.source_dir):
                mo = re_po.match(i)
                if mo:
                    self.lang.append(mo.group(1))
        else:
            self.lang = [i.strip() for i in self.lang.split(',') if i.strip()]

    def run(self):
        """Run msgfmt for each language"""
        if not self.lang:
            return

        if find_executable('msgfmt') is None:
            log.warn('GNU gettext msgfmt utility not found!')
            log.warn('Skip compiling po files.')
            return

        if 'en' in self.lang:
            if find_executable('msginit') is None:
                log.warn('GNU gettext msginit utility not found!')
                log.warn('Skip creating English PO file.')
            else:
                log.info('Creating English PO file...')
                pot = (self.prj_name or 'messages') + '.pot'
                if self.prj_name:
                    en_po = '%s-en.po' % self.prj_name
                else:
                    en_po = 'en.po'
                self.spawn(
                    [
                        'msginit',
                        '--no-translator',
                        '--no-wrap',
                        '--locale',
                        'en',
                        '--input',
                        os.path.join(self.source_dir, pot),
                        '--output-file',
                        os.path.join(self.source_dir, en_po),
                    ]
                )

        basename = self.output_base
        if not basename.endswith('.mo'):
            basename += '.mo'

        po_prefix = ''
        if self.prj_name:
            po_prefix = self.prj_name + '-'
        for lang in self.lang:
            po = os.path.join(self.source_dir, lang + '.po')
            if not os.path.isfile(po):
                po = os.path.join(self.source_dir, po_prefix + lang + '.po')
            dir_ = os.path.join(self.build_dir, lang, 'LC_MESSAGES')
            self.mkpath(dir_)
            mo = os.path.join(dir_, basename)
            if self.force or newer(po, mo):
                log.info('Compile: %s -> %s' % (po, mo))
                self.spawn(['msgfmt', '--output-file', mo, po])
