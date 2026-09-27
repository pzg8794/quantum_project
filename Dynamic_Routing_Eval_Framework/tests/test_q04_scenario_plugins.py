import inspect
from types import SimpleNamespace

import numpy as np
import pytest

from daqr.core.attack_strategy import AttackStrategy, MarkovAttack
from daqr.core.network_environment import AdversarialQuantumEnvironment
from daqr.core.scenario_execution import ScenarioExecutionComponent
from daqr.evaluation.experiment_runner import QuantumExperimentRunner


class FutureCausalStrategy(AttackStrategy):
    mask_capability = "selection_history"

    def availability_at(self, frame, history, state, rng, num_paths, frames):
        if len(history) != frame:
            raise ValueError("Future strategy requires exact history")
        row = np.ones(num_paths, dtype=np.int8)
        if history:
            row[history[-1]] = 0
        return row


def build_environment(strategy, seed=11, frames=3):
    return AdversarialQuantumEnvironment(
        qubit_capacities=(1, 1),
        frame_length=frames,
        attack=strategy,
        seed=seed,
        allocator=None,
        external_contexts=[np.array([[1]]), np.array([[1]])],
        external_rewards=[np.array([0.5]), np.array([0.5])],
    )


def test_runner_has_no_campaign_import_or_causal_scenario_name_dispatch():
    source = inspect.getsource(QuantumExperimentRunner)
    assert "daqr.campaigns" not in source
    assert "'adaptive'" not in source
    assert '"adaptive"' not in source
    assert "'onlineadaptive'" not in source
    assert '"onlineadaptive"' not in source


def test_future_causal_strategy_uses_typed_component_and_environment_session():
    strategy = FutureCausalStrategy(attack_rate=0.2)
    component = ScenarioExecutionComponent(strategy=strategy, seed=715)
    environment = build_environment(strategy)
    assert environment.scenario_mask_capability == "selection_history"
    assert environment.get_environment_info()["attack_pattern"] is None

    runner = QuantumExperimentRunner.__new__(QuantumExperimentRunner)
    runner.configs = SimpleNamespace(
        scientific_block_id=0,
        attack_type="future-causal",
        scenario_execution_components={
            0: {"future-causal": component},
        },
    )
    runner.environment = environment
    runner.frames_count = 3
    runner.causal_scenario_execution = True
    runner.scenario_execution = runner._resolve_scenario_execution()
    session = runner._new_scenario_session()

    np.testing.assert_array_equal(session.begin(0), [1, 1])
    session.observe(0, 1)
    np.testing.assert_array_equal(session.begin(1), [1, 0])
    session.observe(1, 0)
    np.testing.assert_array_equal(session.begin(2), [0, 1])
    session.observe(2, 1)
    assert session.completed_mask().shape == (3, 2)


def test_injected_scenario_component_rejects_untyped_mapping():
    runner = QuantumExperimentRunner.__new__(QuantumExperimentRunner)
    runner.configs = SimpleNamespace(
        scientific_block_id=0,
        attack_type="future-causal",
        scenario_execution_components={
            0: {"future-causal": {"strategy": FutureCausalStrategy(), "seed": 715}},
        },
    )
    with pytest.raises(TypeError, match="ScenarioExecutionComponent"):
        runner._resolve_scenario_execution()


def test_static_strategy_precomputation_is_unchanged():
    strategy = MarkovAttack(attack_rate=0.2, p_stay=0.7)
    expected = strategy.generate(np.random.default_rng(11), 4, 2)
    environment = build_environment(strategy, seed=11, frames=4)

    assert environment.scenario_mask_capability == "static"
    np.testing.assert_array_equal(
        environment.get_environment_info()["attack_pattern"],
        expected,
    )
    assert environment.open_scenario_session(715) is None
