from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import itertools
import networkx as nx
import numpy as np

from daqr.core.topology_generator import Paper8RandomConnectedTopologyGenerator


@dataclass(frozen=True)
class Paper8TestbedConfig:
    """
    Minimal config to reproduce the Paper 8 random-graph testbed attributes.

    Ranges match the upstream repo defaults in spirit; exact values should be
    set from your run configuration.
    """

    num_nodes: int = 15
    edge_probability: float = 0.25
    num_paths: int = 4
    k_paths_per_pair: int = 25

    fidelity_range: tuple[float, float] = (0.6, 0.99)
    rate_range: tuple[float, float] = (0.7, 1.0)
    pur_round_range: tuple[int, int] = (0, 3)  # high is exclusive
    swap_success_range: tuple[float, float] = (0.8, 1.0)

    mode: int = 3  # 1=rate, 2=balanced, 3=fidelity-only (recommended)


def _path_features(topology: nx.Graph, path: list[int]) -> dict[str, float]:
    edges = list(zip(path[:-1], path[1:]))
    fidelities = [float((topology.get_edge_data(u, v) or {}).get("fidelity", 0.5)) for u, v in edges]
    rates = [float((topology.get_edge_data(u, v) or {}).get("rate", 0.0)) for u, v in edges]
    pur_rounds = [float((topology.get_edge_data(u, v) or {}).get("pur_round", 0)) for u, v in edges]
    swap_probs = [float(topology.nodes[n].get("swap_success", 1.0)) for n in path[1:-1]]

    return {
        "hops": float(max(len(path) - 1, 0)),
        "min_fidelity": float(min(fidelities) if fidelities else 0.0),
        "mean_fidelity": float(np.mean(fidelities) if fidelities else 0.0),
        "min_rate": float(min(rates) if rates else 0.0),
        "mean_rate": float(np.mean(rates) if rates else 0.0),
        "min_pur_round": float(min(pur_rounds) if pur_rounds else 0.0),
        "swap_success_prod": float(np.prod(swap_probs) if swap_probs else 1.0),
    }


def generate_paper8_paths(
    topology: nx.Graph,
    *,
    num_paths: int,
    k_paths_per_pair: int,
    seed: int,
) -> list[list[int]]:
    """
    Generate a stable list of candidate paths ("arms") for Paper 8 by sampling
    random (src, dst) pairs and taking k shortest simple paths per pair.
    """
    rng = np.random.default_rng(seed)
    nodes = list(topology.nodes())
    if len(nodes) < 2:
        raise ValueError("Paper8 topology must have at least 2 nodes.")

    paths: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()

    # Keep sampling endpoint pairs until we have enough unique paths.
    # Cap attempts to avoid infinite loops on tiny graphs.
    max_pairs = max(50, num_paths * 25)
    for _ in range(max_pairs):
        if len(paths) >= num_paths:
            break
        src, dst = rng.choice(nodes, size=2, replace=False)
        try:
            gen = nx.shortest_simple_paths(topology, int(src), int(dst), weight="distance")
            for p in itertools.islice(gen, int(k_paths_per_pair)):
                key = tuple(int(x) for x in p)
                if key in seen:
                    continue
                seen.add(key)
                paths.append([int(x) for x in p])
                if len(paths) >= num_paths:
                    break
        except nx.NetworkXNoPath:
            continue

    if len(paths) < num_paths:
        # Last resort: pick one connected pair and duplicate the shortest path.
        src, dst = nodes[0], nodes[-1]
        try:
            p = nx.shortest_path(topology, int(src), int(dst))
        except nx.NetworkXNoPath:
            p = [int(src), int(dst)]
        while len(paths) < num_paths:
            paths.append([int(x) for x in p])

    return paths[:num_paths]


def build_paper8_testbed(
    *,
    seed: int,
    config: Paper8TestbedConfig | None = None,
) -> dict[str, Any]:
    """
    Returns a dict suitable for feeding into ExperimentConfiguration.set_environment via **kwargs.

    Keys:
      - external_topology
      - metadata (includes paper8_paths, paper8_mode, paper8_path_features)
    """
    cfg = config or Paper8TestbedConfig()

    topo_gen = Paper8RandomConnectedTopologyGenerator(
        num_nodes=cfg.num_nodes,
        edge_probability=cfg.edge_probability,
        fidelity_range=cfg.fidelity_range,
        rate_range=cfg.rate_range,
        pur_round_range=cfg.pur_round_range,
        swap_success_range=cfg.swap_success_range,
        seed=seed,
        testbed="paper8",
    )
    topology = topo_gen.generate()
    paths = generate_paper8_paths(
        topology,
        num_paths=cfg.num_paths,
        k_paths_per_pair=cfg.k_paths_per_pair,
        seed=seed,
    )

    features = [_path_features(topology, p) for p in paths]

    return {
        "external_topology": topology,
        "metadata": {
            "paper8_paths": paths,
            "paper8_mode": int(cfg.mode),
            "paper8_path_features": features,
        },
    }

