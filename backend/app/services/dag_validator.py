"""Pure-Python DFS validation for the curriculum prerequisite DAG (FR11)."""

from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID


class DAGCycleError(ValueError):
    """Raised when adding prerequisite edges would create a self-loop or cycle."""


def validate_prerequisite_dag(
    existing_edges: Iterable[tuple[UUID, UUID]],
    target_topic_id: UUID,
    new_prerequisite_ids: Iterable[UUID],
) -> None:
    """Validates that assigning `new_prerequisite_ids` to `target_topic_id` keeps the graph acyclic.

    Each edge in `existing_edges` is `(topic_id, prerequisite_topic_id)`, meaning
    `prerequisite_topic_id` must be mastered BEFORE `topic_id`.
    """
    prereq_set = set(new_prerequisite_ids)
    if target_topic_id in prereq_set:
        raise DAGCycleError("A topic cannot list itself as a prerequisite.")

    # Build adjacency map: topic -> set of prerequisites, replacing target_topic_id's edges
    prereqs_by_topic: dict[UUID, set[UUID]] = defaultdict(set)
    nodes: set[UUID] = {target_topic_id} | prereq_set

    for topic_id, prereq_id in existing_edges:
        nodes.add(topic_id)
        nodes.add(prereq_id)
        if topic_id != target_topic_id:
            prereqs_by_topic[topic_id].add(prereq_id)

    prereqs_by_topic[target_topic_id] = set(prereq_set)

    # Standard 3-color DFS cycle check (0 = unvisited, 1 = visiting, 2 = visited)
    state: dict[UUID, int] = {node: 0 for node in nodes}

    def dfs(node: UUID) -> None:
        state[node] = 1
        for neighbor in prereqs_by_topic.get(node, ()):
            neighbor_state = state.get(neighbor, 0)
            if neighbor_state == 1:
                raise DAGCycleError(
                    f"Circular prerequisite dependency detected involving topic {neighbor}."
                )
            if neighbor_state == 0:
                dfs(neighbor)
        state[node] = 2

    for node in list(nodes):
        if state.get(node, 0) == 0:
            dfs(node)
