from __future__ import annotations
"""
Quantum network environment for entanglement routing.
Attack strategies moved to attack_strategies.py for better organization.
"""
import numpy as np
import networkx as nx

# Import attack strategies from separate module
from daqr.core.attack_strategy import (
    AttackStrategy,
    NoAttack,
    RandomAttack,
    MarkovAttack,
    AdaptiveAttack,
    OnlineAdaptiveAttack,
    create_attack_strategy
)

# Import quantum physics objects (if refactored)
try:
    from daqr.core.quantum_physics import (
        DefaultNoiseModel,
        DefaultFidelityCalculator
    )
    QUANTUM_PHYSICS_AVAILABLE = True
except ImportError:
    QUANTUM_PHYSICS_AVAILABLE = False

import numpy as np, gc, copy
from abc import ABC, abstractmethod
from typing import Dict, Optional, List


# =============================================================================
# BASE ENVIRONMENT
# =============================================================================

class QuantumEnvironment:
    """
    Base Quantum Network Environment.
    Handles network topology, contexts (qubit allocations), and reward calculations.
    This class represents a "no attack" baseline scenario by default.
    """
    def __init__(self, attack, qubit_capacities=(8, 10, 8, 9), 
                allocator=None,
                noise_model=None,              # NEW
                fidelity_calculator=None,      # NEW
                external_contexts=None, 
                external_rewards=None,
                external_topology=None,
                frame_length=1400,
                entanglement_success_factor=100,
                horizon_length=2000,
                num_paths=4,
                num_total_qubits=35,
                seed=42):

        # Store quantum objects
        self.noise_model = noise_model
        self.fidelity_calculator = fidelity_calculator

        # Add allocator support
        self.attack = attack
        self.allocator = allocator
        self.attack_rate = attack.attack_rate
        
        # Existing setup
        self.num_paths = num_paths
        self.frame_length = frame_length
        self.horizon_length = horizon_length
        self.rng = np.random.default_rng(seed)
        self.qubit_capacities = qubit_capacities
        self.num_total_qubits = num_total_qubits
        self.entanglement_success_factor = entanglement_success_factor
        
        # Topology
        self.topology = external_topology
        # Contexts
        if external_contexts is not None:   self.contexts = external_contexts
        else:                               self.contexts = self._generate_contexts()

        # Use allocator for initial allocation if provided
        if self.allocator:
            # Initial call with timestep=0 and empty stats, Reallocating
            initial_stats = {i: {'success_rate': 0.5, 'pulls': 0, 'successes': 0, 'failures': 0} 
                            for i in range(len(qubit_capacities))}
            self.qubit_capacities = self.allocator.allocate(timestep=0, route_stats=initial_stats, verbose=False)
            print(f"🔄 {self.allocator} Dynamic Allocation (Initial): {self.qubit_capacities}")
        else:
            self.qubit_capacities = tuple(qubit_capacities)
            print(f"📌 Static Allocation: {self.qubit_capacities}")

        self.frame_length = int(frame_length)
        self.rng = np.random.default_rng(seed)
        self.num_paths = len(self.qubit_capacities)
        # This new parameter restores the correct reward calculation.
        self.entanglement_success_factor = entanglement_success_factor
        self.route_stats = {i: {'pulls': 0, 'successes': 0, 'failures': 0} for i in range(self.num_paths)}

        # DISPATCHER: Rewards calculation
        if external_rewards is not None:
            # Path 1: User-provided
            self.reward_list = external_rewards
        elif self.noise_model is not None and self.fidelity_calculator is not None:
            # Path 2: Quantum objects (NEW)
            self.reward_list = self._calculate_path_rewards_from_physics()
        else:
            # Path 3: Hardcoded (EXISTING)
            self.reward_list = self._calculate_path_rewards()




    def get_route_stats(self):
        """Calculate current route statistics for allocator"""
        stats = {}
        for route_id in range(self.num_paths):
            pulls = self.route_stats[route_id]['pulls']
            successes = self.route_stats[route_id]['successes']
            
            if pulls > 0:
                success_rate = successes / pulls
            else:
                success_rate = 0.5  # Prior
                
            stats[route_id] = {
                'pulls': pulls,
                'successes': successes,
                'failures': self.route_stats[route_id]['failures'],
                'success_rate': success_rate
            }
        return stats


    def record_outcome(self, route_id, success):
        """Record route selection outcome"""
        self.route_stats[route_id]['pulls'] += 1
        if success:
            self.route_stats[route_id]['successes'] += 1
        else:
            self.route_stats[route_id]['failures'] += 1


    def update_qubit_allocation(self, timestep: int, route_stats: Dict[int, Dict]):
        """
        Update qubit allocation based on route performance.
        
        Args:
            timestep: Current timestep
            route_stats: Performance statistics per route
        """
        if self.allocator:
            new_allocation = self.allocator.allocate(timestep, route_stats)
            self.qubit_capacities = new_allocation
            # Recalculate rewards with new allocation
            self.reward_list = self._calculate_path_rewards()



    def _generate_contexts(self):
        ctxs = []
        for path_idx, capacity in enumerate(self.qubit_capacities):
            if path_idx < 2:  # 2-hop paths
                path_ctx = [np.array([i, capacity - i]) for i in range(capacity + 1)]
            else:  # 3-hop paths
                path_ctx = []
                for i in range(capacity + 1):
                    for j in range(capacity + 1 - i):
                        path_ctx.append(np.array([i, j, capacity - i - j]))
            ctxs.append(np.array(path_ctx))
        return ctxs
    
    def _calculate_path_rewards(self):
        """
        *** CORRECTED REWARD LOGIC ***
        Uses the new 'entanglement_success_factor' constant instead of 'self.frame_length'.
        This ensures base rewards are consistent across all experiments.
        """
        # The 'A' factor is now a fixed hyperparameter of the environment, not the experiment length.
        A = self.entanglement_success_factor

        def p(pe): return 1 - (1 - pe) ** A

        # The rest of your original, correct physics-based calculation remains unchanged.
        # Path 1
        pe1, pe2 = 1.5e-4, 1.5e-4
        p1, p2 = p(pe1), p(pe2)
        r1 = [(1 - (1 - p1) ** c[0]) * (1 - (1 - p2) ** c[1]) for c in self.contexts[0]]
        # Path 2
        pe1, pe2 = 1e-4, 1e-4
        p1, p2 = p(pe1), p(pe2)
        r2 = [(1 - (1 - p1) ** c[0]) * (1 - (1 - p2) ** c[1]) for c in self.contexts[1]]
        # Path 3
        pe1, pe2, pe3 = 2e-4, 2e-4, 2e-4
        p1, p2, p3 = p(pe1), p(pe2), p(pe3)
        r3 = [(1 - (1 - p1) ** c[0]) * (1 - (1 - p2) ** c[1]) * (1 - (1 - p3) ** c[2]) for c in self.contexts[2]]
        # Path 4
        pe1, pe2, pe3 = 1.5e-4, 1.5e-4, 1.5e-4
        p1, p2, p3 = p(pe1), p(pe2), p(pe3)
        r4 = [(1 - (1 - p1) ** c[0]) * (1 - (1 - p2) ** c[1]) * (1 - (1 - p3) ** c[2]) for c in self.contexts[3]]
        
        return [r1, r2, r3, r4]

    def _calculate_path_rewards_from_physics(self):
        """
        NEW: Calculate rewards using pluggable quantum physics objects.
        """
        if self.noise_model is None or self.fidelity_calculator is None:
            raise ValueError("Both noise_model and fidelity_calculator must be provided")
        
        rewards = []
        
        for path_idx in range(self.num_paths):
            path_rewards = []
            
            # Safety: ensure context exists for this path
            if path_idx >= len(self.contexts) or not self.contexts[path_idx]:
                print(f"⚠️ Warning: No contexts for path {path_idx}, using dummy")
                path_rewards = [0.5] * 10  # or skip, or raise error
            else:
                # Get error rates from quantum noise model
                error_rates = self.noise_model.get_error_rates(path_idx)
                
                # Compute fidelity for each context
                for context in self.contexts[path_idx]:
                    fidelity = self.fidelity_calculator.compute_path_fidelity(
                        error_rates=error_rates,
                        context=context,
                        success_factor=self.entanglement_success_factor
                    )
                    path_rewards.append(fidelity)
            rewards.append(path_rewards)
        return rewards

    def generate_attack_pattern(self) -> np.ndarray:
        """Default behavior for the base environment is no attacks."""
        return np.ones((self.frame_length, self.num_paths), dtype=np.int8)

    def get_environment_info(self) -> dict:
        """
        Provides a standardized payload of environment details for runners and algorithms.
        Makes data read-only to prevent downstream mutation.
        """
        attack_pattern = self.generate_attack_pattern()
        attack_pattern.setflags(write=False)

        return {
            'contexts': self.contexts,
            'reward_functions': self.reward_list,
            'attack_pattern': attack_pattern,
            'num_paths': self.num_paths,
            'frame_length': self.frame_length,
            'qubit_capacities': self.qubit_capacities,
            'attack_strategy': 'NoAttack',
            'environment_type': self.__class__.__name__,
            'config': {
                'qubit_capacities': self.qubit_capacities,
                'frame_length': self.frame_length,
                'attack_strategy': 'NoAttack',
            },
        }

    def oracle(self, attack_pattern: np.ndarray | None = None) -> dict:
        """
        Computes the optimal policy (oracle) given a full attack pattern,
        assuming a single best action is chosen for the entire duration.
        """
        if attack_pattern is None:
            attack_pattern = self.generate_attack_pattern()

        # Sum of available (not attacked) frames per path
        frames_not_attacked = attack_pattern.sum(axis=0)

        best_total_reward = -1.0
        best_path = -1
        best_action = -1

        for p_idx in range(self.num_paths):
            path_rewards = np.asarray(self.reward_list[p_idx])
            # Total reward for each action on this path is reward * available_frames
            total_rewards_for_path = path_rewards * frames_not_attacked[p_idx]
            best_action_for_path = int(np.argmax(total_rewards_for_path))
            max_reward_for_path = total_rewards_for_path[best_action_for_path]

            if max_reward_for_path > best_total_reward:
                best_total_reward = max_reward_for_path
                best_path = p_idx
                best_action = best_action_for_path

        return {
            "oracle_path": best_path,
            "oracle_action": best_action,
            "oracle_total_reward": best_total_reward,
        }

    def cleanup(self, verbose=False):
        """Clean up large memory objects to prevent leaks."""
        attrs_to_clean = ['contexts', 'reward_list', 'rng']
        cleaned = []
        try:
            for attr in attrs_to_clean:
                if hasattr(self, attr):
                    delattr(self, attr)
                    cleaned.append(attr)
            if verbose: print(f"Cleaned up in {self.__class__.__name__}: {', '.join(cleaned)}")
            gc.collect()
        except: pass

    def __del__(self):
        """Ensure cleanup is called when the object is destroyed."""
        self.cleanup()

    def __repr__(self):
        env = self.__class__.__name__.replace("QuantumEnvironment", "")
        return env if env else "Baseline (None)"

    def set_fusion_routing(self, fusion_prob=0.9, enable_secondary_fusions=True):
        """
        Configure environment for fusion-based routing (QuARC-style)
        
        Args:
            fusion_prob: q (fusion success probability)
            enable_secondary_fusions: Whether to attempt multiple fusion rounds
        """
        self.fusion_mode = True
        self.fusion_prob = fusion_prob
        self.enable_secondary_fusions = enable_secondary_fusions
        
        print(f"Fusion routing enabled: q={fusion_prob}, "
            f"secondary_fusions={enable_secondary_fusions}")

    def simulate_fusion_routing(self, path, qubits_allocated):
        """
        Simulate fusion-based entanglement distribution along a path
        
        This is analogous to your existing path simulation but uses fusion
        instead of swapping.
        
        Args:
            path: List of node indices
            qubits_allocated: Number of qubits assigned to this path
            
        Returns:
            success (bool), aggregate_throughput (int)
        """
        if not hasattr(self, 'fusion_mode') or not self.fusion_mode:
            raise RuntimeError("Fusion routing not enabled. Call set_fusion_routing() first")
        
        # Step 1: Simulate link generation
        successful_links = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            p_link = self.noise_model.edge_probs.get((u, v), self.noise_model.p_avg)
            
            # Attempt link generation
            if np.random.rand() < p_link:
                successful_links.append((u, v))
        
        # Step 2: Check if there's a connected path of successful links
        # (simplified - in real QuARC, this involves complex fusion logic)
        if len(successful_links) == len(path) - 1:
            # All links succeeded, now attempt fusions
            num_fusions = len(path) - 2  # Internal nodes perform fusions
            
            # Each fusion succeeds with prob q
            all_fusions_succeed = np.random.rand() < (self.fusion_prob ** num_fusions)
            
            if all_fusions_succeed:
                # Success! Could be multiple parallel entanglements
                aggregate = 1  # Simplified - QuARC can generate multiple
                return True, aggregate
        
        return False, 0



# =============================================================================
# STOCHASTIC ENVIRONMENT
# =============================================================================

class StochasticQuantumEnvironment(QuantumEnvironment):
    """
    An environment with a pre-generated, fixed random attack mask.
    This represents a non-adaptive, memoryless (stochastic) adversary.
    It inherits all properties from QuantumEnvironment and overrides the
    attack generation logic.
    """
    def __init__(self, attack, qubit_capacities=(8, 10, 8, 9), frame_length=4000, 
                    seed: int | None = None, allocator=None, **kwargs):  
        
        super().__init__(attack, qubit_capacities=qubit_capacities, 
                            frame_length=frame_length, seed=seed, allocator=allocator, **kwargs)

        # Generate the stochastic attack mask once upon initialization
        self._attack_mask = self.attack.generate(self.rng, self.frame_length, self.num_paths)
        self._attack_mask.setflags(write=False) # Make it read-only

    def generate_attack_pattern(self) -> np.ndarray:
        """Overrides the base method to return the pre-generated stochastic mask."""
        return self._attack_mask

    def reset_environment(self, *, frame_length: int | None = None, seed: int | None = None,
                          attack_rate: float | None = None):
        """
        Resets the environment for a new run. This allows re-use of the object
        with new parameters, which is useful for iterative experiments.
        """
        if frame_length is not None and int(frame_length) != self.frame_length:
            self.frame_length = int(frame_length)
            # Reward calculations depend on frame_length, so they must be recomputed
            self.reward_list = self._calculate_path_rewards()

        if seed is not None:
            self.rng = np.random.default_rng(seed)

        if attack_rate is not None:
            self.attack_rate = float(attack_rate)

        # Re-roll the stochastic mask if any relevant parameter changed
        if any([frame_length, seed, attack_rate]):
            self._attack_mask = RandomAttack(attack_rate=self.attack_rate).generate(
                self.rng, self.frame_length, self.num_paths
            )
            self._attack_mask.setflags(write=False)

        return self.get_environment_info()

    def get_environment_info(self) -> dict:
        """
        Overrides the base method to report the correct attack strategy ('RandomAttack')
        and environment type.
        """
        info = super().get_environment_info()
        info['attack_strategy'] = 'RandomAttack'
        info['environment_type'] = self.__class__.__name__
        info['config']['attack_strategy'] = 'RandomAttack'
        return info

# =============================================================================
# ADVERSARIAL ENVIRONMENT
# =============================================================================

class AdversarialQuantumEnvironment(QuantumEnvironment):
    """
    An environment that uses a pluggable 'AttackStrategy'. This allows for
    testing against various adversaries, from simple to adaptive.
    """
    def __init__(self,
                 qubit_capacities=(8, 10, 8, 9),
                 frame_length=4000,
                 attack: AttackStrategy | None = None,
                 seed: int | None = None, allocator=None, **kwargs):
        super().__init__(attack, qubit_capacities=qubit_capacities, frame_length=frame_length, 
                seed=seed, allocator=allocator, **kwargs)
        self.attack: AttackStrategy = self.attack or NoAttack()

        # Generate the attack pattern once using the provided strategy
        self.attack_pattern = self.attack.generate(
            self.rng, self.frame_length, self.num_paths
        ).astype(np.int8, copy=False)
        self.attack_pattern.setflags(write=False)

    def generate_attack_pattern(self) -> np.ndarray:
        """Overrides the base method to return the pattern from the attack strategy."""
        return self.attack_pattern

    def reset_environment(self, *, frame_length: int | None = None, seed: int | None = None,
                         attack: AttackStrategy | None = None, selection_trace: list[int] | None = None):
        """
        Resets and regenerates the environment with new parameters, including support
        for adaptive attacks that require a `selection_trace`.
        """
        if frame_length is not None and int(frame_length) != self.frame_length:
            self.frame_length = int(frame_length)
            self.reward_list = self._calculate_path_rewards() # Recompute rewards

        if seed is not None:
            self.rng = np.random.default_rng(seed)

        if attack is not None:
            self.attack = attack

        # Regenerate the attack pattern if anything has changed
        self.attack_pattern = self.attack.generate(
            self.rng, self.frame_length, self.num_paths, selection_trace=selection_trace
        ).astype(np.int8, copy=False)
        self.attack_pattern.setflags(write=False)

        return self.get_environment_info()

    def get_environment_info(self) -> dict:
        """
        Overrides the base method to report the specific attack strategy being used.
        """
        info = super().get_environment_info()
        attack_strategy_name = self.attack.__class__.__name__
        info['attack_strategy'] = attack_strategy_name
        info['environment_type'] = self.__class__.__name__
        info['config']['attack_strategy'] = attack_strategy_name
        info['config']['has_adaptive_attacks'] = hasattr(self.attack, 'observe') # For logging
        return info