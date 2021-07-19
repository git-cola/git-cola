"""build_pot command for setup.py"""
# pylint: disable=attribute-defined-outside-init,import-error,no-name-in-module
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import glob
from distutils import log
from distutils.core import Command
from distutils.errors import DistutilsOptionError

from . import build_util


class build_pot(Command):
    """Distutils command build_pot"""

    description = 'extract strings from python sources for translation'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [
        ('build-dir=', 'd', 'Directory to put POT file'),
        ('output=', 'o', 'POT filename'),
        ('lang=', None, 'Comma-separated list of languages to update po-files'),
        ('no-lang', 'N', "Don't update po-files"),
        ('english', 'E', 'Regenerate English PO file'),
    ]
    user_options = build_util.stringify_options(user_options)
    boolean_options = build_util.stringify_list(['no-lang', 'english'])

    def initialize_options(self):
        self.build_dir = None
        self.output = None
        self.lang = None
        self.no_lang = False
        self.english = False

    def finalize_options(self):
        if self.build_dir is None:
            self.build_dir = 'po'
        if not self.output:
            self.output = (self.distribution.get_name() or 'messages') + '.pot'
        if self.lang is not None:
            self.lang = [i.strip() for i in self.lang.split(',') if i.strip()]
        if self.lang and self.no_lang:
            raise DistutilsOptionError(
                "You can't use options " "--lang=XXX and --no-lang in the same time."
            )

    def run(self):
        """Run xgettext for project sources"""
        # project name based on `name` argument in setup() call
        prj_name = self.distribution.get_name()
        # output file
        if self.build_dir != '.':
            fullname = os.path.join(self.build_dir, self.output)
        else:
            fullname = self.output
        log.info('Generate POT file: ' + fullname)
        if not os.path.isdir(self.build_dir):
            log.info('Make directory: ' + self.build_dir)
            os.makedirs(self.build_dir)

        cmd = [
            'xgettext',
            '--language=Python',
            '--keyword=N_',
            '--no-wrap',
            '--no-location',
            '--omit-header',
            '--sort-output',
            '--output-dir',
            self.build_dir,
            '--output',
            self.output,
        ]
        cmd.extend(glob.glob('bin/git-*'))
        cmd.extend(glob.glob('share/git-cola/bin/git-*'))
        cmd.extend(glob.glob('cola/*.py'))
        cmd.extend(glob.glob('cola/*/*.py'))
        self.spawn(cmd)

        _force_LF(fullname)
        # regenerate english PO
        if self.english:
            log.info('Regenerating English PO file...')
            if prj_name:
                en_po = prj_name + '-' + 'en.po'
            else:
                en_po = 'en.po'
            self.spawn(
                [
                    'msginit',
                    '--no-translator',
                    '--locale',
                    'en',
                    '--input',
                    os.path.join(self.build_dir, self.output),
                    '--output-file',
                    os.path.join(self.build_dir, en_po),
                ]
            )
        # search and update all po-files
        if self.no_lang:
            return
        for po in glob.glob(os.path.join(self.build_dir, '*.po')):
            if self.lang is not None:
                po_lang = os.path.splitext(os.path.basename(po))[0]
                if prj_name and po_lang.startswith(prj_name + '-'):
                    po_lang = po_lang[5:]
                if po_lang not in self.lang:
                    continue
            new_po = po + '.new'
            self.spawn(
                [
                    'msgmerge',
                    '--no-location',
                    '--no-wrap',
                    '--no-fuzzy-matching',
                    '--sort-output',
                    '--output-file',
                    new_po,
                    po,
                    fullname,
                ]
            )
            # force LF line-endings
            log.info('%s --> %s' % (new_po, po))
            _force_LF(new_po, po)
            os.unlink(new_po)


def _force_LF(src, dst=None):
    with open(src, 'rb') as f:
        content = f.read().decode('utf-8')
    if dst is None:
        dst = src
    f = open(dst, 'wb')
    try:
        f.write(build_util.encode(content))
    finally:
        f.close()
