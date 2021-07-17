"""Tests DAG functionality"""
from __future__ import absolute_import, division, unicode_literals

import mock
from cola.models import dag

from . import helper


LOG_LINES = """
ad454b189fe5785af397fd6067cf103268b6626e^A^A (tag: refs/tags/v0.0)^ADavid Aguilar^AFri Nov 30 00:03:28 2007 -0800^Adavvid@gmail.com^Afirst cut of ugit
1ba04ad185cf9f04c56c8482e9a73ef1bd35c695^Aad454b189fe5785af397fd6067cf103268b6626e^A^ADavid Aguilar^AFri Nov 30 05:07:47 2007 -0800^Adavvid@gmail.com^Aupdated model/view/controller api
fa5ad6c38be603e2ffd1f9b722a3a5c675f63de2^A1ba04ad185cf9f04c56c8482e9a73ef1bd35c695^A^ADavid Aguilar^AFri Nov 30 05:19:05 2007 -0800^Adavvid@gmail.com^AAvoid multiple signoffs
103766573cd4e6799d3ee792bcd632b92cf7c6c0^Afa5ad6c38be603e2ffd1f9b722a3a5c675f63de2^A^ADavid Aguilar^ATue Dec 11 05:13:21 2007 -0800^Adavvid@gmail.com^AAdded TODO
e3f5a2d0248de6197d6e0e63c901810b8a9af2f8^Afa5ad6c38be603e2ffd1f9b722a3a5c675f63de2^A^ADavid Aguilar^AMon Dec 3 02:36:06 2007 -0800^Adavvid@gmail.com^AMerged qlistwidgets into main.
f4fb8fd5baaa55d9b41faca79be289bb4407281e^Ae3f5a2d0248de6197d6e0e63c901810b8a9af2f8^A^ADavid Aguilar^ATue Dec 4 03:14:56 2007 -0800^Adavvid@gmail.com^ASquashed commit of the following:
23e7eab4ba2c94e3155f5d261c693ccac1342eb9^Af4fb8fd5baaa55d9b41faca79be289bb4407281e^A^ADavid Aguilar^AThu Dec 6 18:59:20 2007 -0800^Adavvid@gmail.com^AMerged diffdisplay into main
""".strip().replace(  # noqa
    '^A', chr(0x01)
).split(
    '\n'
) + [
    ''
]  # noqa


class DAGTestCase(helper.GitRepositoryTestCase):

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)
        self.params = dag.DAG('HEAD', 1000)
        self.reader = dag.RepoReader(self.context, self.params)

    @mock.patch('cola.models.dag.core')
    def test_repo_reader(self, core):
        expect = len(LOG_LINES) - 1
        actual = 0

        core.readline.return_value = LOG_LINES[0]
        for idx, _ in enumerate(self.reader.get()):
            core.readline.return_value = LOG_LINES[idx + 1]
            actual += 1

        self.assertEqual(expect, actual)

    @mock.patch('cola.models.dag.core')
    def test_repo_reader_order(self, core):
        commits = [
            'ad454b189fe5785af397fd6067cf103268b6626e',
            '1ba04ad185cf9f04c56c8482e9a73ef1bd35c695',
            'fa5ad6c38be603e2ffd1f9b722a3a5c675f63de2',
            '103766573cd4e6799d3ee792bcd632b92cf7c6c0',
            'e3f5a2d0248de6197d6e0e63c901810b8a9af2f8',
            'f4fb8fd5baaa55d9b41faca79be289bb4407281e',
            '23e7eab4ba2c94e3155f5d261c693ccac1342eb9',
        ]
        core.readline.return_value = LOG_LINES[0]
        for idx, commit in enumerate(self.reader.get()):
            core.readline.return_value = LOG_LINES[idx + 1]

            self.assertEqual(commits[idx], commit.oid)

    @mock.patch('cola.models.dag.core')
    def test_repo_reader_parents(self, core):
        parents = [
            [],
            ['ad454b189fe5785af397fd6067cf103268b6626e'],
            ['1ba04ad185cf9f04c56c8482e9a73ef1bd35c695'],
            ['fa5ad6c38be603e2ffd1f9b722a3a5c675f63de2'],
            ['fa5ad6c38be603e2ffd1f9b722a3a5c675f63de2'],
            ['e3f5a2d0248de6197d6e0e63c901810b8a9af2f8'],
            ['f4fb8fd5baaa55d9b41faca79be289bb4407281e'],
        ]
        core.readline.return_value = LOG_LINES[0]
        for idx, commit in enumerate(self.reader.get()):
            core.readline.return_value = LOG_LINES[idx + 1]

            self.assertEqual(parents[idx], [p.oid for p in commit.parents])

    @mock.patch('cola.models.dag.core')
    def test_repo_reader_contract(self, core):
        core.exists.return_value = True
        core.readline.return_value = LOG_LINES[0]

        for idx, _ in enumerate(self.reader.get()):
            core.readline.return_value = LOG_LINES[idx + 1]

        core.start_command.assert_called()
        call_args = core.start_command.call_args
        self.assertTrue('log.abbrevCommit=false' in call_args[0][0])
        self.assertTrue('log.showSignature=false' in call_args[0][0])
