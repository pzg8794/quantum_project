"""Use native frame-by-frame attack history in the Pipeline 155 notebook."""

import numpy as np

from daqr.algorithms.base_bandit import Oracle as NativeOracle
from daqr.algorithms.neural_bandits import EXPNeuralUCB as NativeEXPNeuralUCB
from daqr.algorithms.neural_bandits import GNeuralUCB as NativeGNeuralUCB
from daqr.algorithms.predictive_bandits import CPursuitNeuralUCB as NativeCPursuitNeuralUCB
from daqr.algorithms.predictive_bandits import iCPursuitNeuralUCB as NativeiCPursuitNeuralUCB
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.network_environment import AdversarialQuantumEnvironment as NativeAdversarialEnvironment
from daqr.core.network_environment import QuantumEnvironment


class ScenarioMask:
    def __init__(self, environment):
        self.strategy = environment.attack
        self.seed = environment.scenario_seed
        self.shape = (environment.frame_length, environment.num_paths)

    def open_session(self):
        self.session = self.strategy.open_session(np.random.default_rng(self.seed), *self.shape)
        return self.session

    def setflags(self, *, write):
        if write:
            raise ValueError("Causal availability is read-only")

    def __getitem__(self, frame):
        return self.session.policy_mask[frame]


class AdversarialQuantumEnvironment(NativeAdversarialEnvironment):
    def __init__(self, *, seed, **parameters):
        QuantumEnvironment.__init__(self, seed=seed, **parameters)
        self.scenario_seed = seed

    def generate_attack_pattern(self):
        return ScenarioMask(self)


class Oracle(NativeOracle):
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        self._scenario = attack_list.open_session()
        super().__init__(configs, X_n, reward_list, frame_number,
                         self._scenario.policy_mask, capacity, **kwargs)

    def take_action(self):
        frame = self.current_frame
        self.prepare_scenario_frame(frame, self._scenario.begin(frame))
        return super().take_action()

    def update(self, path, action, reward):
        frame = self.current_frame
        super().update(path, action, reward)
        self._scenario.observe(frame, path)
        if self.current_frame == self.frame_number:
            del self._scenario


class CausalBatch:
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        self._scenario = attack_list.open_session()
        super().__init__(configs, X_n, reward_list, frame_number,
                         self._scenario.policy_mask, capacity, **kwargs)

    def run(self, attack_list, verbose=None):
        try:
            return super().run(self._scenario.policy_mask, verbose=verbose,
                               scenario_session=self._scenario)
        finally:
            del self._scenario


class EXPNeuralUCB(CausalBatch, NativeEXPNeuralUCB):
    pass


class GNeuralUCB(CausalBatch, NativeGNeuralUCB):
    pass


class CPursuitNeuralUCB(CausalBatch, NativeCPursuitNeuralUCB):
    pass


class iCPursuitNeuralUCB(CausalBatch, NativeiCPursuitNeuralUCB):
    def run(self, attack_list, verbose=False):
        try:
            return NativeiCPursuitNeuralUCB.run(self, self._scenario.policy_mask, verbose=verbose)
        finally:
            del self._scenario

    def select_group(self, frame):
        self._scenario.begin(frame)
        return super().select_group(frame)

    def update_group_selection(self, selected_path, observed_reward, advice=None, *, frame=None, **kwargs):
        super().update_group_selection(selected_path, observed_reward, advice, frame=frame, **kwargs)
        self._scenario.observe(frame, selected_path)


class CausalExperimentConfiguration(ExperimentConfiguration):
    causal_scenario_execution = True

    def set_environment(self, qubit_cap, frames_no, seed, attack_intensity,
                        env_type="stochastic", attack_type="stochastic", metadata=None,
                        noise_model=None, fidelity_calculator=None, external_topology=None,
                        external_contexts=None, external_rewards=None):
        self.attack_type = attack_type
        if self.attack_strategy is None:
            self.set_attack_strategy(attack_type=attack_type, attack_intensity=attack_intensity)
        self._env_params = dict(
            attack=None, qubit_capacities=tuple(qubit_cap), frame_length=int(frames_no),
            seed=int(seed), allocator=self.allocator, test_bed=self.testbed_id,
            env_type=env_type, actk_type=attack_type, noise_model=noise_model,
            entanglement_success_factor=self.testbed_config.get("entanglement_success_factor") or 100,
            fidelity_calculator=fidelity_calculator, external_topology=external_topology,
            external_contexts=external_contexts, external_rewards=external_rewards,
        )
        parameters = self._env_params.copy()
        parameters.pop("env_type")
        parameters.pop("actk_type")
        parameters["attack"] = self.attack_strategy
        self.environment = AdversarialQuantumEnvironment(**parameters)

    def bind_causal_models(self):
        for model in (Oracle, GNeuralUCB, EXPNeuralUCB, CPursuitNeuralUCB, iCPursuitNeuralUCB):
            self.algorithm_configs[model.__name__]["model_class"] = model
