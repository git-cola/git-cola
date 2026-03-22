from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EdgeSegment:
    from_column: int
    to_column: int
    color_index: int


@dataclass
class GraphRow:
    commit_oid: str
    commit_column: int
    edges_to_parent: list[EdgeSegment] = field(default_factory=list)


@dataclass
class GraphResult:
    rows: list[GraphRow]
    max_columns: int


def build_graph(commits: list[tuple[str, list[str]]]) -> GraphResult:
    """Build a row-based graph representation from a list of commits.

    Commits are received in topo order from RepoReader (oldest first).
    """
    active_lanes: list[str | None] = []
    color_map: dict[str, int] = {}
    next_color = 0
    rows: list[GraphRow] = []
    max_columns = 0

    # The graph is built top-to-bottom (newest first), so the input is reversed.
    for oid, parent_oids in reversed(commits):
        # Find the commit in active_lanes or allocate a new lane.
        if oid in active_lanes:
            commit_column = active_lanes.index(oid)
        else:
            commit_column = len(active_lanes)
            active_lanes.append(oid)

        # Assign a color for this commit's lane.
        commit_color = color_map.get(oid, None)
        if commit_color is None:
            commit_color = next_color
            next_color += 1
        else:
            # This is the last time we see this commit, remove it from color_map to reduce
            # max memory consumption
            color_map.pop(oid)

        edges: list[EdgeSegment] = []

        # Pass through lanes
        for i, lane_oid in enumerate(active_lanes):
            if lane_oid is not None and lane_oid != oid:
                edges.append(
                    EdgeSegment(
                        from_column=i,
                        to_column=i,
                        color_index=color_map[lane_oid],
                    )
                )

        if parent_oids:
            for i, parent_oid in enumerate(parent_oids):
                # Select color if not selected: first parent gets commit color,
                # others get next color
                parent_color = color_map.get(parent_oid, None)
                if parent_color is None:
                    if i == 0:
                        parent_color = commit_color
                    else:
                        parent_color = next_color
                        next_color += 1
                    color_map[parent_oid] = parent_color

                if parent_oid in active_lanes:
                    parent_col = active_lanes.index(parent_oid)
                    if i == 0:
                        # First parent means commit no longer uses its column
                        active_lanes[commit_column] = None
                else:
                    if i == 0:
                        # First parent takes the commit's lane.
                        active_lanes[commit_column] = parent_oid
                        parent_col = commit_column
                    elif None in active_lanes:
                        # Try to reuse a None slot
                        parent_col = active_lanes.index(None)
                        active_lanes[parent_col] = parent_oid
                    else:
                        # Append new
                        parent_col = len(active_lanes)
                        active_lanes.append(parent_oid)

                edges.append(
                    EdgeSegment(
                        from_column=commit_column,
                        to_column=parent_col,
                        color_index=parent_color,
                    )
                )
        else:
            # Root commit - remove its lane.
            active_lanes[commit_column] = None

        max_columns = max(max_columns, len(active_lanes))

        # Trim trailing None slots.
        while active_lanes and active_lanes[-1] is None:
            active_lanes.pop()

        row = GraphRow(
            commit_oid=oid,
            commit_column=commit_column,
            edges_to_parent=edges,
        )
        rows.append(row)

    return GraphResult(rows=rows, max_columns=max_columns)
