try:
    import networkx as nx
except ModuleNotFoundError:
    print("SKIP: Paper8 tests require 'networkx' (not installed).")
    raise SystemExit(0)

from daqr.core.paper8_testbed import Paper8TestbedConfig, build_paper8_testbed


def main() -> None:
    cfg = Paper8TestbedConfig(num_nodes=12, edge_probability=0.3, num_paths=4, k_paths_per_pair=20, mode=3)
    params = build_paper8_testbed(seed=123, config=cfg)

    topo = params["external_topology"]
    meta = params["metadata"]
    paths = meta["paper8_paths"]
    features = meta["paper8_path_features"]

    assert isinstance(topo, nx.Graph)
    assert nx.is_connected(topo), "Paper8 topology must be connected"

    assert isinstance(paths, list) and len(paths) == 4
    assert isinstance(features, list) and len(features) == 4

    for p in paths:
        assert isinstance(p, list) and len(p) >= 2
        for u, v in zip(p[:-1], p[1:]):
            assert topo.has_edge(u, v), f"Path edge missing: ({u}, {v})"

    required = {
        "hops",
        "min_fidelity",
        "mean_fidelity",
        "min_rate",
        "mean_rate",
        "min_pur_round",
        "swap_success_prod",
    }
    for f in features:
        assert required.issubset(set(f.keys()))

    print("PASS: Paper8 testbed build (topology + paths + features)")


if __name__ == "__main__":
    main()
