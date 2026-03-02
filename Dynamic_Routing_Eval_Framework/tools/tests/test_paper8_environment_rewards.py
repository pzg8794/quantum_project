try:
    import networkx  # noqa: F401
except ModuleNotFoundError:
    print("SKIP: Paper8 tests require 'networkx' (not installed).")
    raise SystemExit(0)

from daqr.core.attack_strategy import NoAttack
from daqr.core.network_environment import QuantumEnvironment
from daqr.core.paper8_testbed import Paper8TestbedConfig, build_paper8_testbed


def main() -> None:
    cfg = Paper8TestbedConfig(num_nodes=12, edge_probability=0.3, num_paths=4, k_paths_per_pair=20, mode=3)
    params = build_paper8_testbed(seed=123, config=cfg)

    env_low = QuantumEnvironment(
        attack=NoAttack(),
        qubit_capacities=(4, 4, 4, 4),
        allocator=None,
        external_topology=params["external_topology"],
        metadata=params["metadata"],
        test_bed="paper8",
        frame_length=50,
        seed=123,
    )

    assert len(env_low.contexts) == 4
    assert len(env_low.reward_list) == 4
    for i in range(4):
        assert len(env_low.contexts[i]) == 1
        assert float(env_low.contexts[i][0][0]) == 4.0  # capacity as first feature
        assert len(env_low.reward_list[i]) == 1

    low_rewards = [float(r[0]) for r in env_low.reward_list]

    env_high = QuantumEnvironment(
        attack=NoAttack(),
        qubit_capacities=(32, 32, 32, 32),
        allocator=None,
        external_topology=params["external_topology"],
        metadata=params["metadata"],
        test_bed="paper8",
        frame_length=50,
        seed=123,
    )
    high_rewards = [float(r[0]) for r in env_high.reward_list]

    # With mode=3 (fidelity-only) and our purification-budget mapping, increasing capacity
    # should not reduce reward (more purification rounds possible or unchanged).
    for lo, hi in zip(low_rewards, high_rewards):
        assert hi >= lo

    print("PASS: Paper8 environment rewards + contexts")


if __name__ == "__main__":
    main()
