"""Tests DAG functionality"""
# pylint: disable=redefined-outer-name
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from cola.models import dag

from .helper import app_context
from .helper import patch


assert app_context is not None


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


class DAGTestData(object):
    """Test data provided by the dag_context fixture"""
    def __init__(self, app_context, head='HEAD', count=1000):
        self.context = app_context
        self.params = dag.DAG(head, count)
        self.reader = dag.RepoReader(app_context, self.params)


@pytest.fixture
def dag_context(app_context):
    """Provide DAGTestData for use by tests"""
    return DAGTestData(app_context)


@patch('cola.models.dag.core')
def test_repo_reader(core, dag_context):
    expect = len(LOG_LINES) - 1

    actual = 0
    core.readline.return_value = LOG_LINES[0]
    for idx, _ in enumerate(dag_context.reader.get()):
        core.readline.return_value = LOG_LINES[idx + 1]
        actual += 1

    assert expect == actual


@patch('cola.models.dag.core')
def test_repo_reader_order(core, dag_context):
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
    for idx, commit in enumerate(dag_context.reader.get()):
        assert commits[idx] == commit.oid
        core.readline.return_value = LOG_LINES[idx + 1]


@patch('cola.models.dag.core')
def test_repo_reader_parents(core, dag_context):
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
    for idx, commit in enumerate(dag_context.reader.get()):
        assert parents[idx] == [p.oid for p in commit.parents]
        core.readline.return_value = LOG_LINES[idx + 1]


@patch('cola.models.dag.core')
def test_repo_reader_contract(core, dag_context):
    core.exists.return_value = True
    core.readline.return_value = LOG_LINES[0]

    for idx, _ in enumerate(dag_context.reader.get()):
        core.readline.return_value = LOG_LINES[idx + 1]

    core.start_command.assert_called()
    call_args = core.start_command.call_args

    assert 'log.abbrevCommit=false' in call_args[0][0]
    assert 'log.showSignature=false' in call_args[0][0]
