try:
    import networkx  # noqa: F401
except ModuleNotFoundError:
    print("SKIP: Paper8 tests require 'networkx' (not installed).")
    raise SystemExit(0)

try:
    import numpy as np
except ModuleNotFoundError:
    print("SKIP: Paper8 tests require 'numpy' (not installed).")
    raise SystemExit(0)

from daqr.core.attack_strategy import NoAttack
from daqr.core.network_environment import QuantumEnvironment
from daqr.core.quantum_physics import Paper8NoiseModel, Paper8FidelityCalculator
from daqr.core.topology_generator import Paper8RandomConnectedTopologyGenerator


def main() -> None:
    import networkx as nx
    rng = np.random.default_rng(123)

    topo = Paper8RandomConnectedTopologyGenerator(
        num_nodes=12,
        edge_probability=0.3,
        seed=123,
        fidelity_range=(0.7, 0.95),
        rate_range=(0.7, 1.0),
        pur_round_range=(0, 4),
        swap_success_range=(0.8, 0.99),
    ).generate()

    # 4 unique shortest paths from random pairs
    nodes = list(topo.nodes())
    paths = []
    attempts = 0
    while len(paths) < 4 and attempts < 200:
        attempts += 1
        src, dst = rng.choice(nodes, 2, replace=False)
        try:
            p = nx.shortest_path(topo, int(src), int(dst), weight="distance")
        except nx.NetworkXNoPath:
            continue
        if p not in paths and len(p) >= 2:
            paths.append([int(x) for x in p])
    assert len(paths) == 4

    # contexts: per-path integer allocations over edges (compositions of cap)
    def compositions(total: int, parts: int, limit: int = 2000):
        out = []

        def rec(remaining: int, k: int, prefix):
            if len(out) >= limit:
                return
            if k == 1:
                out.append(prefix + [remaining])
                return
            for x in range(remaining + 1):
                if len(out) >= limit:
                    return
                rec(remaining - x, k - 1, prefix + [x])

        rec(int(total), int(parts), [])
        return out

    def make_contexts(qubit_cap):
        ctxs = []
        for cap, p in zip(qubit_cap, paths):
            hops = max(1, len(p) - 1)
            ctxs.append(np.array(compositions(int(cap), hops), dtype=int))
        return ctxs

    env_low = QuantumEnvironment(
        attack=NoAttack(),
        qubit_capacities=(4, 4, 4, 4),
        allocator=None,
        noise_model=Paper8NoiseModel(topology=topo, paths=paths),
        fidelity_calculator=Paper8FidelityCalculator(min_fidelity=0.0),
        external_topology=topo,
        external_contexts=make_contexts((4, 4, 4, 4)),
        external_rewards=None,
        frame_length=50,
        seed=123,
    )

    assert len(env_low.contexts) == 4
    assert len(env_low.reward_list) == 4
    low_best = [float(np.max(r)) for r in env_low.reward_list]

    env_high = QuantumEnvironment(
        attack=NoAttack(),
        qubit_capacities=(32, 32, 32, 32),
        allocator=None,
        noise_model=Paper8NoiseModel(topology=topo, paths=paths),
        fidelity_calculator=Paper8FidelityCalculator(min_fidelity=0.0),
        external_topology=topo,
        external_contexts=make_contexts((32, 32, 32, 32)),
        external_rewards=None,
        frame_length=50,
        seed=123,
    )
    high_best = [float(np.max(r)) for r in env_high.reward_list]

    # Increasing capacity should not reduce the best achievable fidelity score.
    for lo, hi in zip(low_best, high_best):
        assert hi >= lo

    print("PASS: Paper8 environment rewards via pluggable physics")


if __name__ == "__main__":
    main()
