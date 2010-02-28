"""build_qm command for setup.py"""

from distutils import log
from distutils.command.build import build
from distutils.core import Command
from distutils.dep_util import newer
from distutils.spawn import find_executable
import os
import re


class build_qm(Command):
    """Subcommand of build command: build_qm"""

    description = 'compile po files to qm files'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [('build-dir=', 'd', 'Directory to build locale files'),
                    ('source-dir=', None, 'Directory with sources po files'),
                    ('force', 'f', 'Force creation of qm files'),
                    ('lang=', None, 'Comma-separated list of languages '
                                    'to process')]

    boolean_options = ['force']

    def initialize_options(self):
        self.build_dir = None
        self.source_dir = None
        self.force = None
        self.lang = None

    def finalize_options(self):
        self.set_undefined_options('build', ('force', 'force'))
        self.prj_name = self.distribution.get_name()
        if self.build_dir is None:
            self.build_dir = os.path.join('share', 'git-cola', 'qm')
        if self.source_dir is None:
            self.source_dir = os.path.join('share', 'git-cola', 'po')
        if self.lang is None:
            if self.prj_name:
                re_po = re.compile(r'^(?:%s-)?([a-zA-Z_]+)\.po$' % self.prj_name)
            else:
                re_po = re.compile(r'^([a-zA-Z_]+)\.po$')
            self.lang = []
            for i in os.listdir(self.source_dir):
                qm = re_po.match(i)
                if qm:
                    self.lang.append(qm.group(1))
        else:
            self.lang = [i.strip() for i in self.lang.split(',') if i.strip()]

    def run(self):
        """Run msgfmt for each language"""
        if not self.lang:
            return

        if find_executable('msgfmt') is None:
            log.warn("GNU gettext msgfmt utility not found!")
            log.warn("Skip compiling po files.")
            return

        if 'en' in self.lang:
            if find_executable('msginit') is None:
                log.warn("GNU gettext msginit utility not found!")
                log.warn("Skip creating English PO file.")
            else:
                log.info('Creating English PO file...')
                pot = (self.prj_name or 'messages') + '.pot'
                if self.prj_name:
                    en_po = '%s-en.po' % self.prj_name
                else:
                    en_po = 'en.po'
                self.spawn(['msginit',
                    '--no-translator',
                    '-l', 'en',
                    '-i', os.path.join(self.source_dir, pot),
                    '-o', os.path.join(self.source_dir, en_po),
                    ])

        po_prefix = ''
        if self.prj_name:
            po_prefix = self.prj_name + '-'
        for lang in self.lang:
            po = os.path.join(self.source_dir, lang + '.po')
            if not os.path.isfile(po):
                po = os.path.join(self.source_dir, po_prefix + lang + '.po')
            dir_ = self.build_dir
            self.mkpath(dir_)
            qm = os.path.join(dir_, lang + '.qm')
            if self.force or newer(po, qm):
                log.info('Compile: %s -> %s' % (po, qm))
                self.spawn(['msgfmt', '--qt', po, '-o', qm])


build.sub_commands.insert(0, ('build_qm', None))
