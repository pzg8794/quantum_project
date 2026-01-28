"""
Paper 12 (Wang et al. 2024 - QuARC) Runner
Run: python run_paper12.py
"""
from paper_runner_base import PaperRunner
import networkx as nx
import numpy as np


class Paper12Runner(PaperRunner):
    """Runner for Paper 12 testbed"""

    def __init__(self, test_mode=True):
        super().__init__(testbed_name="paper12", test_mode=test_mode)

    def configure(self):
        """Configure Paper 12 specific parameters"""
        self.config = {
            'n_nodes': 100,
            'avg_degree': 6,
            'waxman_beta': 0.2,
            'waxman_alpha': 0.4,
            'topology_type': 'waxman',
            'channel_width': 3,
            'fusion_prob': 0.9,
            'qubits_per_node': 12,
            'entanglement_prob': 0.6,
            'num_sd_pairs': 10,
            'epoch_length': 500,
            'total_timeslots': 7000,
            'split_constant': 4,
            'enable_clustering': True,
            'enable_secondary_fusions': True,
            'num_paths': 4,  # Actual routing paths
            'total_qubits': 120,
            'exploration_bonus': 1.5,
            'min_qubits_per_route': 3,
            'use_fusion_rewards': True,
            'retry_threshold': 0.7,
            'max_retry_attempts': 3,
            'retry_decay_rate': 0.95,
            'seed': 42,
            'epsilon': 1.0
        }

        # Framework settings
        self.base_seed = 12345
        self.attack_intensity = 0.25
        self.frame_step = 1000
        self.current_frames = 5000 if self.test_mode else 4000
        self.current_experiments = 3 if self.test_mode else 10

        # Models and scenarios
        base_config = self.ExperimentConfiguration()
        self.models = base_config.NEURAL_MODELS
        self.test_scenarios = {'stochastic': 'Stochastic Random Failures'}

    def get_physics_params(self, seed, qubit_cap):
        """Get Paper 12 physics parameters"""
        p12_config = self.config

        # Generate Waxman topology
        topology = self.Paper12WaxmanTopologyGenerator.generate(
            n=p12_config['n_nodes'],
            alpha=p12_config['waxman_alpha'],
            beta=p12_config['waxman_beta'],
            seed=seed
        )

        # Generate paths
        num_paths = p12_config['num_paths']
        nodes = list(topology.nodes())
        rng = np.random.default_rng(seed)
        paths = []
        attempts = 0
        max_attempts = 10 * num_paths

        while len(paths) < num_paths and attempts < max_attempts:
            attempts += 1
            src, dst = rng.choice(nodes, 2, replace=False)
            try:
                path = nx.shortest_path(topology, src, dst)
                if path not in paths:
                    paths.append(path)
            except nx.NetworkXNoPath:
                continue

        if len(paths) < num_paths:
            raise RuntimeError(f"Could not find {num_paths} valid paths in Waxman topology.")

        # Create noise and fidelity models
        fusion_prob = float(p12_config.get('fusion_prob', 0.9))
        entanglement_prob = float(p12_config.get('entanglement_prob', 0.6))

        noise_model = self.FusionNoiseModel(
            topology=topology,
            paths=paths,
            fusion_prob=fusion_prob,
            entanglement_prob=entanglement_prob
        )

        fidelity_calc = self.FusionFidelityCalculator()
        reward_func = self.QuARCRewardFunction()

        # Generate contexts (arms per path)
        arms_per_path = [8, 10, 8, 9]  # DO NOT CHANGE - framework assumption

        degrees = dict(topology.degree())
        max_degree = max(degrees.values()) if degrees else 1.0

        contexts = []
        for pidx, K in enumerate(arms_per_path):
            path = paths[pidx]
            hop_count = len(path) - 1

            # Feature 1: hop count
            f1_hops = float(hop_count)

            # Feature 2: normalized average node degree
            path_degrees = [degrees[n] for n in path]
            avg_degree = float(sum(path_degrees) / len(path_degrees))
            f2_deg_norm = avg_degree / max_degree if max_degree > 0 else 0.0

            # Feature 3: fusion success prob
            f3_fusion = fusion_prob

            # Create K arms for this path
            path_contexts = []
            for k in range(K):
                # Each arm has same context (different allocation strategies)
                context_vector = np.array([f1_hops, f2_deg_norm, f3_fusion])
                path_contexts.append(context_vector)

            contexts.append(path_contexts)

        # Rewards (throughput-based)
        external_rewards = []
        for pidx in range(len(paths)):
            path_rewards = []
            error_rates = noise_model.get_error_rates(pidx)

            for context in contexts[pidx]:
                fidelity = fidelity_calc.compute_path_fidelity(
                    error_rates=error_rates,
                    context={'hop_count': len(paths[pidx]) - 1},
                    fusion_prob=fusion_prob
                )
                reward = reward_func.compute(success=fidelity > 0.5)
                path_rewards.append(reward)

            external_rewards.append(path_rewards)

        print(f"Paper12 QuARC physics: {len(paths)} paths, fusion_prob={fusion_prob}")

        return {
            'noise_model': noise_model,
            'fidelity_calculator': fidelity_calc,
            'external_topology': topology,
            'external_contexts': contexts,
            'external_rewards': external_rewards
        }


if __name__ == "__main__":
    runner = Paper12Runner(test_mode=True)
    runner.run(
        allocators=['Default', 'Random', 'Dynamic', 'ThompsonSampling'],
        scales=[1.0],
        runs=[3]
    )
