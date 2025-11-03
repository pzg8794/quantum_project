from __future__ import annotations
import numpy as np, gc, copy
from typing import Dict, Optional, List
from abc import ABC, abstractmethod

# ---------------------------------------------------------------------
# Strategy base
# ---------------------------------------------------------------------
class AttackStrategy(ABC):
    """Contract: produce an (T x P) attack mask; 1 = no-attack, 0 = attack."""
    @abstractmethod
    def generate(self,
                 rng: np.random.Generator,
                 frame_length: int,
                 num_paths: int,
                 selection_trace: list[int] | None = None) -> np.ndarray:
        """
        Offline (batch) attack generation.

        Args:
            rng: np.random.Generator
            frame_length: T
            num_paths: P
            selection_trace: optional list of chosen paths length T;
                             if provided, the attack adapts to *actual* usage.
        Returns:
            (T x P) np.ndarray[int] with 1=no-attack, 0=attack
        """

    def __repr__(self):
        return self.__class__.__name__

class NoAttack(AttackStrategy):
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        return np.ones((frame_length, num_paths), dtype=int)

class RandomAttack(AttackStrategy):
    def __init__(self, attack_rate: float = 0.25):
        self.attack_rate = float(attack_rate)
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        mask = rng.random((frame_length, num_paths)) >= self.attack_rate
        return mask.astype(int)

class MarkovAttack(AttackStrategy):
    def __init__(self, transition=None, init=None, k_attacks: int = 1, attack_rate: float = 1.0):
        self.transition = transition  # (P x P) row-stochastic
        self.init = init              # (P,) distribution
        self.k_attacks = int(k_attacks)
        self.attack_rate = float(attack_rate)

    def _default_T(self, P):
        if P == 4:
            T = np.array([
                [0.35, 0.15, 0.35, 0.15],
                [0.30, 0.20, 0.30, 0.20],
                [0.35, 0.15, 0.35, 0.15],
                [0.30, 0.20, 0.30, 0.20],
            ], dtype=float)
        else:
            T = np.full((P, P), 1.0 / P, dtype=float)
        return T / T.sum(axis=1, keepdims=True)

    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        T = self._default_T(num_paths) if self.transition is None else self.transition
        T = T / T.sum(axis=1, keepdims=True)
        pi0 = np.full(num_paths, 1.0 / num_paths) if self.init is None else self.init
        pi0 = pi0 / pi0.sum()

        out = np.ones((frame_length, num_paths), dtype=int)
        state = rng.choice(num_paths, p=pi0)
        k = max(0, min(self.k_attacks, num_paths))

        for t in range(frame_length):
            if k > 0 and (rng.random() <= self.attack_rate):
                probs = T[state].copy()
                idxs = (rng.choice(num_paths, size=k, replace=False, p=probs / probs.sum())
                        if k < num_paths else np.arange(num_paths))
                out[t, idxs] = 0
            state = rng.choice(num_paths, p=T[state])
        return out
    
    def cleanup(self, verbose=False):
        """
        Clean up attack strategy resources.
        Safe for all subclasses - only deletes if attributes exist.
        """
        cleanup_items = []
        
        # Clear any cached data
        for attr in ['_cached_mask', 'history', 'state', 'counts', 
                     'transition', 'init', 'arima_models']:
            if hasattr(self, attr):
                delattr(self, attr)
                cleanup_items.append(attr)
        
        # Force garbage collection
        collected = gc.collect()
        
        if verbose and cleanup_items:
            print(f"✓ {self.__class__.__name__} cleaned: {', '.join(cleanup_items)}, GC:{collected}")



# ---------------------------------------------------------------------
# AdaptiveAttack (offline-first; single target per frame)
# ---------------------------------------------------------------------
class AdaptiveAttack(AttackStrategy):
    """
    Adaptive attacker driven by *observed usage* (selection_trace).
    Attacks the most-used path in the recent memory_window (single target).

    If selection_trace is not provided, it synthesizes a sticky usage process
    (for smoke tests). For real evaluation, pass the true selection_trace.
    """

    def __init__(self, memory_window: int = 50, attack_rate: float = 1.0, sticky_p: float = 0.7):
        self.memory_window = int(max(1, memory_window))
        self.attack_rate = float(np.clip(attack_rate, 0.0, 1.0))
        self.sticky_p = float(np.clip(sticky_p, 0.0, 1.0))

    def generate(
        self,
        rng: np.random.Generator,
        frame_length: int,
        num_paths: int,
        selection_trace: list[int] | None = None,
    ) -> np.ndarray:
        """
        Build a (T x P) attack mask (1 = no-attack, 0 = attack) driven by recent usage.
        Falls back to a sticky synthetic usage process when no selection_trace is provided.
        """
        attack = np.ones((frame_length, num_paths), dtype=int)

        # Prepare a usage sequence to "observe"
        if not selection_trace:  # handles None or []
            trace: list[int] = []
            prev = int(rng.integers(num_paths))
            for _ in range(frame_length):
                choice = prev if rng.random() < self.sticky_p else int(rng.integers(num_paths))
                trace.append(choice)
                prev = choice
        else:
            trace = list(selection_trace[:frame_length])
            if len(trace) < frame_length:
                # pad safely (repeat the last choice) to match frame_length
                trace += [int(trace[-1])] * (frame_length - len(trace))

        # Frame-by-frame attacks
        for t in range(frame_length):
            # skip this frame with probability (1 - attack_rate)
            if rng.random() > self.attack_rate:
                continue

            # recent history (exclude current index)
            start = max(0, t - self.memory_window)
            recent = trace[start:t]

            if len(recent) == 0:
                target = int(trace[t])  # best guess: current pick
            else:
                counts = np.bincount(recent, minlength=num_paths)
                target = int(np.argmax(counts))

            attack[t, target] = 0

        return attack

# ---------------------------------------------------------------------
# OnlineAdaptiveAttack (inherits AdaptiveAttack; online + richer control)
# ---------------------------------------------------------------------
class OnlineAdaptiveAttack(AdaptiveAttack):
    """
    Online variant:
      - same offline `generate(...)` API as parent (batch),
      - plus online hooks:
          * reset(num_paths)
          * observe(selected_path)
          * attack_mask(rng, num_paths) -> (P,) mask for the current frame
      - supports multi-target (k), exponential decay, and softmax selection.

    Use this for realistic closed-loop experiments where the attacker reacts
    to the algorithm's *actual* selections as they happen.
    """

    def __init__(self,
                 memory_window: int = 50,
                 attack_rate: float = 1.0,
                 sticky_p: float = 0.7,
                 k: int = 1,
                 decay: float | None = None,
                 temperature: float | None = None):
        super().__init__(memory_window=memory_window, attack_rate=attack_rate, sticky_p=sticky_p)
        self.k = int(max(1, k))              # up to k attacked paths per frame
        self.decay = decay                   # e.g., 0.97 for exponential forgetting
        self.temperature = temperature       # softmax temp; None => greedy
        self._history: list[int] = []
        self._counts: np.ndarray | None = None
        self._num_paths: int | None = None

    # ---- Online hooks ------------------------------------------------
    def reset(self, num_paths: int):
        self._num_paths = int(num_paths)
        self._history = []
        self._counts = np.zeros(self._num_paths, dtype=float)

    def observe(self, selected_path: int):
        """Record the algorithm's chosen path; updates rolling window and decayed counts."""
        sp = int(selected_path)
        self._history.append(sp)
        if self._counts is not None:
            if self.decay is not None:
                self._counts *= float(self.decay)
            self._counts[sp] += 1.0

        # Trim rolling memory if it grows too large (optional safety)
        if len(self._history) > max(4 * self.memory_window, 10000):
            self._history = self._history[-2 * self.memory_window:]

    def attack_mask(self, rng: np.random.Generator, num_paths: int | None = None) -> np.ndarray:
        """
        Produce a (P,) mask for the current frame. Call once per time step.
        Returns 1=no-attack, 0=attack. May attack up to k paths.
        """
        P = self._num_paths if (self._num_paths is not None) else int(num_paths)
        assert P is not None, "Call reset(num_paths) before using attack_mask()"
        mask = np.ones(P, dtype=int)

        if rng.random() > self.attack_rate:
            return mask  # skip this frame

        # Scoring: prefer decayed counts if available, else windowed frequency
        if self._counts is not None and self._counts.sum() > 0:
            scores = self._counts.copy()
        else:
            recent = self._history[-self.memory_window:] if self._history else []
            scores = np.bincount(recent, minlength=P).astype(float)

        if self.temperature is not None and self.temperature > 0:
            # Softmax sampling without replacement (top-k)
            logits = scores / float(self.temperature)
            logits -= logits.max()  # numerical stability
            probs = np.exp(logits)
            total = probs.sum()
            probs = probs / total if total > 0 else np.ones(P) / P
            k = min(self.k, P)
            targets = list(rng.choice(P, size=k, replace=False, p=probs))
        else:
            # Greedy top-k
            k = min(self.k, P)
            targets = list(np.argsort(-scores)[:k])

        for t in targets:
            mask[int(t)] = 0
        return mask

    # ---- Offline (batch) - consistent with parent -------------------
    def generate(self,
                 rng: np.random.Generator,
                 frame_length: int,
                 num_paths: int,
                 selection_trace: list[int] | None = None) -> np.ndarray:
        """
        Simulate the same online policy to build a (T x P) mask matrix.
        If `selection_trace` is provided, adapts to the true usage;
        otherwise synthesizes a sticky usage as a fallback.
        """
        self.reset(num_paths)
        attack = np.ones((frame_length, num_paths), dtype=int)

        # Prepare a usage sequence to "observe"
        if not selection_trace:  # handles None or []
            # Fallback sticky usage (smoke tests only)
            trace = []
            prev = int(rng.integers(num_paths))
            for _ in range(frame_length):
                choice = prev if rng.random() < self.sticky_p else int(rng.integers(num_paths))
                trace.append(choice)
                prev = choice
        else:
            trace = list(selection_trace[:frame_length])
            if len(trace) < frame_length:
                trace += [trace[-1]] * (frame_length - len(trace))

        # Roll forward as if online
        for t in range(frame_length):
            mask_t = self.attack_mask(rng, num_paths)
            attack[t] = mask_t
            self.observe(trace[t])

        return attack


# =============================================================================
# BASE ENVIRONMENT
# =============================================================================

class QuantumEnvironment:
    """
    Base Quantum Network Environment.
    Handles network topology, contexts (qubit allocations), and reward calculations.
    This class represents a "no attack" baseline scenario by default.
    """
    def __init__(self, qubit_capacities=(8, 10, 8, 9), frame_length=4000, 
                seed=None, entanglement_success_factor=3000, attack_rate: float = 0.25, allocator=None):
        # Add allocator support
        self.allocator = allocator
        self.attack_rate = attack_rate

        # Use allocator for initial allocation if provided
        if self.allocator:
            # Initial call with timestep=0 and empty stats
            initial_stats = {i: {'success_rate': 0.5, 'pulls': 0, 'successes': 0, 'failures': 0} 
                            for i in range(len(qubit_capacities))}
            self.qubit_capacities = self.allocator.allocate(timestep=0, route_stats=initial_stats)
            print(f"🔄 Dynamic Allocation (Initial): {self.qubit_capacities}")
        else:
            self.qubit_capacities = tuple(qubit_capacities)
            print(f"📌 Static Allocation: {self.qubit_capacities}")

        self.num_paths = len(self.qubit_capacities)
        self.frame_length = int(frame_length)
        self.rng = np.random.default_rng(seed)
        
        # This new parameter restores the correct reward calculation.
        self.entanglement_success_factor = entanglement_success_factor

        # Contexts & rewards (precomputed reward tables)
        self.contexts = self._generate_contexts()
        self.reward_list = self._calculate_path_rewards() # Route performance tracking for dynamic allocation
        self.route_stats = {i: {'pulls': 0, 'successes': 0, 'failures': 0} for i in range(self.num_paths)}


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
        for attr in attrs_to_clean:
            if hasattr(self, attr):
                delattr(self, attr)
                cleaned.append(attr)
        if verbose:
            print(f"Cleaned up in {self.__class__.__name__}: {', '.join(cleaned)}")
        gc.collect()

    def __del__(self):
        """Ensure cleanup is called when the object is destroyed."""
        self.cleanup()

    def __repr__(self):
        return self.__class__.__name__


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
    def __init__(self,
                 qubit_capacities=(8, 10, 8, 9),
                 frame_length=4000,
                 attack_rate: float = 0.25,
                seed: int | None = None,
                allocator=None):  
        
        super().__init__(qubit_capacities=qubit_capacities, frame_length=frame_length, seed=seed, allocator=allocator)
        self.attack_rate = float(attack_rate)

        # Generate the stochastic attack mask once upon initialization
        self._attack_mask = RandomAttack(attack_rate=self.attack_rate).generate(
            self.rng, self.frame_length, self.num_paths
        )
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
                 seed: int | None = None, allocator=None):
        super().__init__(qubit_capacities=qubit_capacities, frame_length=frame_length, seed=seed, allocator=allocator)
        self.attack: AttackStrategy = attack or NoAttack()

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
