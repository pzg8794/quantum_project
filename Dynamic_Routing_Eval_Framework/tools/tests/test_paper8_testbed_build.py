try:
    import networkx as nx
except ModuleNotFoundError:
    print("SKIP: Paper8 tests require 'networkx' (not installed).")
    raise SystemExit(0)

try:
    import numpy as np
except ModuleNotFoundError:
    print("SKIP: Paper8 tests require 'numpy' (not installed).")
    raise SystemExit(0)

import sys
from pathlib import Path

DAQR_ROOT = Path(__file__).resolve().parents[2]
if str(DAQR_ROOT) not in sys.path:
    sys.path.insert(0, str(DAQR_ROOT))

from daqr.core.topology_generator import Paper8RandomConnectedTopologyGenerator


def main() -> None:
    topo = Paper8RandomConnectedTopologyGenerator(
        num_nodes=12,
        edge_probability=0.3,  # legacy alias; maps to connection_prob
        seed=123,
        fidelity_range=(0.7, 0.95),
        rate_range=(0.7, 1.0),
        pur_round_range=(0, 4),
        swap_success_range=(0.8, 0.99),
    ).generate()

    assert isinstance(topo, nx.Graph)
    assert nx.is_connected(topo), "Paper8 topology must be connected"

    u, v = next(iter(topo.edges()))
    assert "fidelity" in topo[u][v]
    assert "rate" in topo[u][v]
    assert "pur_round" in topo[u][v]
    assert "distance" in topo[u][v]
    assert "swap_success" in topo.nodes[next(iter(topo.nodes()))]

    # sanity: attributes are within [0,1] ranges
    assert 0.0 <= float(topo[u][v]["fidelity"]) <= 1.0
    assert float(topo[u][v]["rate"]) >= 0.0
    assert int(topo[u][v]["pur_round"]) >= 0
    assert 0.0 <= float(topo.nodes[next(iter(topo.nodes()))]["swap_success"]) <= 1.0

    print("PASS: Paper8 core topology generator (attrs present + sane)")


if __name__ == "__main__":
    main()
