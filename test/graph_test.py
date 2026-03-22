from __future__ import annotations

from cola.models.graph import GraphResult, build_graph


def assert_rows(result: GraphResult, expected: list[tuple[str, int]]) -> None:
    actual = [(r.commit_oid, r.commit_column) for r in result.rows]
    assert actual == expected


def assert_edges(result: GraphResult, expected: list[list[tuple[int, int]]]) -> None:
    actual = [
        [(e.from_column, e.to_column) for e in r.edges_to_parent] for r in result.rows
    ]
    assert actual == expected


def test_empty_input():
    result = build_graph([])
    assert result.rows == []
    assert result.max_columns == 0


def test_single_commit():
    result = build_graph([('aaa', [])])
    assert_rows(result, [('aaa', 0)])
    assert_edges(result, [[]])
    assert result.max_columns == 1


def test_linear_chain():
    # C-B-A
    commits = [
        ('A', []),
        ('B', ['A']),
        ('C', ['B']),
    ]
    result = build_graph(commits)
    assert_rows(result, [('C', 0), ('B', 0), ('A', 0)])
    assert_edges(result, [[(0, 0)], [(0, 0)], []])
    assert result.max_columns == 1
    colors = [r.edges_to_parent[0].color_index for r in result.rows[:-1]]
    assert colors[0] == colors[1]


def test_two_way_fork():
    # C B
    # |/
    # A
    commits = [
        ('A', []),
        ('B', ['A']),
        ('C', ['A']),
    ]
    result = build_graph(commits)
    # C
    #  B
    # A
    assert_rows(result, [('C', 0), ('B', 1), ('A', 0)])
    assert_edges(result, [[(0, 0)], [(0, 0), (1, 0)], []])


def test_three_way_fork():
    # D C B
    # |/╱
    # A
    commits = [
        ('A', []),
        ('B', ['A']),
        ('C', ['A']),
        ('D', ['A']),
    ]
    result = build_graph(commits)
    # D
    #  C
    #  B
    # A
    assert_rows(result, [('D', 0), ('C', 1), ('B', 1), ('A', 0)])
    assert_edges(result, [[(0, 0)], [(0, 0), (1, 0)], [(0, 0), (1, 0)], []])


def test_two_way_merge():
    # C
    # |\
    # A B
    commits = [
        ('A', []),
        ('B', []),
        ('C', ['A', 'B']),
    ]
    result = build_graph(commits)
    # C
    #  B
    # A
    assert_rows(result, [('C', 0), ('B', 1), ('A', 0)])
    assert_edges(result, [[(0, 0), (0, 1)], [(0, 0)], []])
    assert result.max_columns == 2
    edges = result.rows[0].edges_to_parent
    assert edges[0].color_index != edges[1].color_index


def test_three_way_merge():
    # D
    # |\╲
    # A B C
    commits = [
        ('A', []),
        ('B', []),
        ('C', []),
        ('D', ['A', 'B', 'C']),
    ]
    result = build_graph(commits)
    # D
    #   C
    #  B
    # A
    assert_rows(result, [('D', 0), ('C', 2), ('B', 1), ('A', 0)])
    assert_edges(
        result,
        [
            [(0, 0), (0, 1), (0, 2)],
            [(0, 0), (1, 1)],
            [(0, 0)],
            [],
        ],
    )
    assert result.max_columns == 3


def test_fork_and_merge_diamond():
    # D
    # |\
    # B C
    # |/
    # A
    commits = [
        ('A', []),
        ('B', ['A']),
        ('C', ['A']),
        ('D', ['B', 'C']),
    ]
    result = build_graph(commits)
    # D
    #  C
    # B
    #  A
    assert_rows(result, [('D', 0), ('C', 1), ('B', 0), ('A', 1)])
    assert_edges(
        result,
        [
            [(0, 0), (0, 1)],
            [(0, 0), (1, 1)],
            [(1, 1), (0, 1)],
            [],
        ],
    )
    assert result.max_columns == 2


def test_branch_and_merge_back():
    # F
    # |
    # E
    # |\
    # C D
    # |/
    # B
    # |
    # A
    commits = [
        ('A', []),
        ('B', ['A']),
        ('C', ['B']),
        ('D', ['B']),
        ('E', ['C', 'D']),
        ('F', ['E']),
    ]
    result = build_graph(commits)
    # F
    # E
    #  D
    # C
    #  B
    #  A
    assert_rows(result, [('F', 0), ('E', 0), ('D', 1), ('C', 0), ('B', 1), ('A', 1)])
    assert_edges(
        result,
        [
            [(0, 0)],
            [(0, 0), (0, 1)],
            [(0, 0), (1, 1)],
            [(1, 1), (0, 1)],
            [(1, 1)],
            [],
        ],
    )
    assert result.max_columns == 2


def test_two_independent_histories():
    # D-C  B-A
    commits = [
        ('A', []),
        ('B', ['A']),
        ('C', []),
        ('D', ['C']),
    ]
    result = build_graph(commits)
    assert_rows(result, [('D', 0), ('C', 0), ('B', 0), ('A', 0)])
    assert_edges(result, [[(0, 0)], [], [(0, 0)], []])
    assert result.max_columns == 1


def test_ten_commit_chain():
    # J-I-H-G-F-E-D-C-B-A
    oids = [chr(ord('A') + i) for i in range(10)]
    commits: list[tuple[str, list[str]]] = [(oids[0], [])]
    for i in range(1, 10):
        commits.append((oids[i], [oids[i - 1]]))
    result = build_graph(commits)
    assert_rows(result, [(oid, 0) for oid in reversed(oids)])
    assert_edges(result, [[(0, 0)]] * 9 + [[]])
    assert result.max_columns == 1


def test_three_way_merge_then_continue():
    #   E
    #   |
    #   D
    #  /|\
    # A B C
    commits = [
        ('A', []),
        ('B', []),
        ('C', []),
        ('D', ['A', 'B', 'C']),
        ('E', ['D']),
    ]
    result = build_graph(commits)
    # E
    # D
    #   C
    #  B
    # A
    assert_rows(result, [('E', 0), ('D', 0), ('C', 2), ('B', 1), ('A', 0)])
    assert_edges(
        result,
        [
            [(0, 0)],
            [(0, 0), (0, 1), (0, 2)],
            [(0, 0), (1, 1)],
            [(0, 0)],
            [],
        ],
    )
    assert result.max_columns == 3


def test_nested_merge_with_shared_ancestor():
    #   F
    #  / \
    # D   E
    # |\  |
    # B C |
    # |/ /
    # A-+
    commits = [
        ('A', []),
        ('B', ['A']),
        ('C', ['A']),
        ('D', ['B', 'C']),
        ('E', ['A']),
        ('F', ['D', 'E']),
    ]
    result = build_graph(commits)
    # F
    #  E
    # D
    #   C
    # B
    #  A
    assert_rows(result, [('F', 0), ('E', 1), ('D', 0), ('C', 2), ('B', 0), ('A', 1)])
    assert_edges(
        result,
        [
            [(0, 0), (0, 1)],
            [(0, 0), (1, 1)],
            [(1, 1), (0, 0), (0, 2)],
            [(0, 0), (1, 1), (2, 1)],
            [(1, 1), (0, 1)],
            [],
        ],
    )


def test_shifted_double_diamond():
    # F
    # |\
    # D E
    # |\|
    # C B
    # |/
    # A
    commits = [
        ('A', []),
        ('B', ['A']),
        ('C', ['A']),
        ('D', ['B', 'C']),
        ('E', ['B']),
        ('F', ['D', 'E']),
    ]
    result = build_graph(commits)
    """
    F
     E
    D
    C
     B
    A
    """
    assert_rows(result, [('F', 0), ('E', 1), ('D', 0), ('C', 0), ('B', 1), ('A', 0)])
    assert_edges(
        result,
        [
            [(0, 0), (0, 1)],
            [(0, 0), (1, 1)],
            [(1, 1), (0, 1), (0, 0)],
            [(1, 1), (0, 0)],
            [(0, 0), (1, 0)],
            [],
        ],
    )
