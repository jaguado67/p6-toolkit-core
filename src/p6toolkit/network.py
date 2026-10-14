"""Structural graph diagnostics only. No P6 CPM equivalence is asserted."""
from __future__ import annotations
from dataclasses import dataclass
import networkx as nx
from .snapshot import ProjectSnapshot


@dataclass(frozen=True)
class NetworkReport:
    activity_count: int
    relationship_count: int
    start_activities: tuple[str, ...]
    finish_activities: tuple[str, ...]
    isolated_activities: tuple[str, ...]
    weak_components: tuple[tuple[str, ...], ...]
    cyclic_sccs: tuple[tuple[str, ...], ...]
    duplicate_pairs: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...]


def inspect_network(snapshot: ProjectSnapshot) -> NetworkReport:
    g = nx.DiGraph()
    ids = snapshot.by_id()
    g.add_nodes_from(ids)
    edge_counts: dict[tuple[str, str], int] = {}
    for rel in snapshot.relationships:
        key = (rel.predecessor_id, rel.successor_id)
        edge_counts[key] = edge_counts.get(key, 0) + 1
        g.add_edge(*key)
    code = lambda task_id: ids[task_id].code
    start = tuple(sorted(code(n) for n in g.nodes if g.in_degree(n) == 0))
    finish = tuple(sorted(code(n) for n in g.nodes if g.out_degree(n) == 0))
    isolated = tuple(sorted(code(n) for n in nx.isolates(g)))
    components = tuple(sorted(
        (tuple(sorted(code(n) for n in component)) for component in
         nx.weakly_connected_components(g)), key=lambda c: (len(c), c)
    ))
    cyclic = tuple(sorted(
        (tuple(sorted(code(n) for n in component)) for component in
         nx.strongly_connected_components(g)
         if len(component) > 1 or any(g.has_edge(n, n) for n in component)),
        key=lambda c: (len(c), c)
    ))
    duplicates = tuple(sorted((code(pred), code(succ))
                              for (pred, succ), count in edge_counts.items() if count > 1))
    warnings = list(snapshot.warnings)
    if cyclic:
        warnings.append("Cyclic SCCs found: temporal feasibility not validated yet")
    if len(components) > 1:
        warnings.append("The network has disconnected components")
    if snapshot.external_links:
        warnings.append("External links excluded from the in-project graph")
    return NetworkReport(len(ids), len(snapshot.relationships), start, finish,
                         isolated, components, cyclic, duplicates, tuple(warnings))
