"""Graph algorithms used by the gate and the planners.

Working implementations, not sketches:
  * Edmonds-Karp maximum flow with a minimum cut certificate (damage pattern D5);
  * successive shortest path minimum cost flow with node potentials, which also
    yields the dual prices used to price congestion (BHR-RS-02 section 5);
  * deterministic shortest path, used by both planners.

Every routine sorts its inputs, so equal inputs produce equal outputs.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Sequence, Tuple

Cap = Dict[Tuple[str, str], float]
Edge = Tuple[str, str, float, float]  # src, dst, capacity, cost

INF = float("inf")


def _residual(edges: Sequence[Edge]) -> Tuple[Cap, Dict[Tuple[str, str], float]]:
    cap: Cap = {}
    cost: Dict[Tuple[str, str], float] = {}
    for src, dst, capacity, unit_cost in sorted(edges):
        key = (src, dst)
        cap[key] = cap.get(key, 0.0) + float(capacity)
        cost[key] = float(unit_cost)
        cap.setdefault((dst, src), 0.0)
        cost.setdefault((dst, src), -float(unit_cost))
    return cap, cost


def _reachable(cap: Cap, source: str) -> set:
    seen = {source}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        for (src, dst), capacity in sorted(cap.items()):
            if src == node and capacity > 1e-9 and dst not in seen:
                seen.add(dst)
                queue.append(dst)
    return seen


def max_flow(edges: Sequence[Edge], source: str, sink: str) -> Tuple[float, List[Tuple[str, str]]]:
    """Edmonds-Karp. Returns (flow value, minimum cut edge set)."""
    cap, _ = _residual(edges)
    flow = 0.0
    while True:
        parent: Dict[str, Optional[str]] = {source: None}
        queue = deque([source])
        while queue and sink not in parent:
            node = queue.popleft()
            for (src, dst), capacity in sorted(cap.items()):
                if src == node and capacity > 1e-9 and dst not in parent:
                    parent[dst] = node
                    queue.append(dst)
        if sink not in parent:
            break
        bottleneck = INF
        node = sink
        while parent[node] is not None:
            prev = parent[node]
            bottleneck = min(bottleneck, cap[(prev, node)])
            node = prev
        node = sink
        while parent[node] is not None:
            prev = parent[node]
            cap[(prev, node)] -= bottleneck
            cap[(node, prev)] = cap.get((node, prev), 0.0) + bottleneck
            node = prev
        flow += bottleneck
    reachable = _reachable(cap, source)
    cut = sorted(
        (u, v) for (u, v) in cap if u in reachable and v not in reachable and cap[(u, v)] <= 1e-9
    )
    return flow, cut


def min_cost_flow(
    edges: Sequence[Edge], source: str, sink: str, demand: float
) -> Tuple[float, float, Dict[Tuple[str, str], float], Dict[str, float]]:
    """Successive shortest paths with potentials.

    Returns (cost, shipped, flow per original edge, node potentials). Potentials
    are the dual prices of the capacity constraints and are the only principled
    way to price congestion without inventing a formula.
    """
    cap, cost = _residual(edges)
    nodes = sorted({u for pair in cap for u in pair})
    potential: Dict[str, float] = {node: 0.0 for node in nodes}
    shipped = 0.0
    total = 0.0
    for _ in range(4 * len(edges) + 8):
        if shipped >= demand - 1e-9:
            break
        dist: Dict[str, float] = {node: INF for node in nodes}
        parent: Dict[str, Optional[str]] = {node: None for node in nodes}
        dist[source] = 0.0
        for _ in range(len(nodes)):
            changed = False
            for (src, dst), capacity in sorted(cap.items()):
                if capacity <= 1e-9 or dist[src] == INF:
                    continue
                reduced = cost[(src, dst)] + potential[src] - potential[dst]
                if dist[src] + reduced < dist[dst] - 1e-12:
                    dist[dst] = dist[src] + reduced
                    parent[dst] = src
                    changed = True
            if not changed:
                break
        if dist[sink] == INF:
            break
        for node in nodes:
            if dist[node] < INF:
                potential[node] += dist[node]
        bottleneck = demand - shipped
        node = sink
        while parent[node] is not None:
            prev = parent[node]
            bottleneck = min(bottleneck, cap[(prev, node)])
            node = prev
        node = sink
        while parent[node] is not None:
            prev = parent[node]
            cap[(prev, node)] -= bottleneck
            cap[(node, prev)] = cap.get((node, prev), 0.0) + bottleneck
            node = prev
        shipped += bottleneck
        total += bottleneck * (potential[sink] - potential[source])
    used = {
        (src, dst): cap.get((dst, src), 0.0) for (src, dst, _, _) in sorted(edges)
    }
    return total, shipped, used, potential


def shortest_path(
    edges: Sequence[Edge], source: str, sink: str, penalty: Optional[Dict[Tuple[str, str], float]] = None
) -> Tuple[List[str], float]:
    """Dijkstra over strictly positive capacity, with an optional additive penalty."""
    adjacency: Dict[str, List[Tuple[str, float]]] = {}
    for src, dst, capacity, unit_cost in sorted(edges):
        if capacity <= 1e-9:
            continue
        weight = unit_cost + (penalty or {}).get((src, dst), 0.0)
        adjacency.setdefault(src, []).append((dst, max(weight, 0.0)))
    dist: Dict[str, float] = {source: 0.0}
    parent: Dict[str, str] = {}
    frontier = [source]
    while frontier:
        frontier.sort(key=lambda n: (dist[n], n))
        node = frontier.pop(0)
        for dst, weight in adjacency.get(node, []):
            candidate = dist[node] + weight
            if candidate < dist.get(dst, INF) - 1e-12:
                dist[dst] = candidate
                parent[dst] = node
                if dst not in frontier:
                    frontier.append(dst)
    if sink not in dist:
        return [], INF
    path = [sink]
    while path[-1] != source:
        path.append(parent[path[-1]])
    return list(reversed(path)), dist[sink]

