"""Tests for the git-fanta command-line parser."""

from cola import main
from cola.models import dag


def test_dag_parser_preserves_absent_count():
    assert main.parse_args(['dag']).count is None


def test_dag_parser_preserves_explicit_product_default_count():
    assert main.parse_args(['dag', '--count', '1000']).count == 1000


def test_dag_namespace_without_cli_values_preserves_product_defaults():
    params = dag.DAG('main --', 1000)

    params.set_arguments(main.parse_args(['dag']))

    assert params.count == 1000
    assert not params.overridden('count')
    assert not params.overridden('ref')


def test_dag_namespace_marks_explicit_default_equal_count_override():
    params = dag.DAG('main --', 1000)

    params.set_arguments(main.parse_args(['dag', '--count', '1000']))

    assert params.count == 1000
    assert params.overridden('count')


def test_dag_namespace_marks_explicit_default_equal_ref_override():
    params = dag.DAG('main --', 1000)

    params.set_arguments(main.parse_args(['dag', 'main', '--']))

    assert params.ref == 'main --'
    assert params.overridden('ref')
