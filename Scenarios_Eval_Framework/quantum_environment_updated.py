from __future__ import annotations
import numpy as np
from typing import Optional, List
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
# BASE QUANTUM ENVIRONMENT
# =============================================================================

class QuantumEnvironment:
    """
    Base Quantum Network Environment
    Handles: network topology, contexts, reward tables
    """
    def __init__(self, qubit_capacities=(8, 10, 8, 9), frame_length=4000, seed: int | None = None):
        self.qubit_capacities = tuple(qubit_capacities)
        self.num_paths = len(self.qubit_capacities)
        self.frame_length = int(frame_length)
        self.rng = np.random.default_rng(seed)

        # contexts & rewards (precomputed reward tables)
        self.contexts = self._generate_contexts()
        self.reward_list = self._calculate_path_rewards()

        self._print_initialization()

    def _print_initialization(self):
        """Clean tabular initialization output"""
        print("\nQUANTUM ENVIRONMENT INITIALIZED:")
        print("=" * 50)
        print(f"| Network Paths:    | {self.num_paths:<15} |")
        print(f"| Qubit Config:     | {str(self.qubit_capacities):<15} |")
        print(f"| Frame Length:     | {self.frame_length:,}           |")
        print("=" * 50)

    def get_oracle_solution(self, attack_pattern: np.ndarray | None = None) -> dict:
        """
        Compute oracle solution for given attack pattern.
        Backward compatibility method name.
        """
        return self.oracle(attack_pattern)
    
    # Small convenience for runners/tools
    def get_environment_info(self) -> dict:
        """
        Standardized payload for ExperimentRunner:
          - contexts
          - reward_functions (alias of reward_list)
          - attack_pattern
          - config (for logging)
        """
        attack = self.generate_attack_pattern().astype(np.int8, copy=False)
        attack.setflags(write=False)
        return {
            'contexts': self.contexts,
            'reward_functions': self.reward_list,
            'attack_pattern': attack,
            'num_paths': self.num_paths,        # Add these for consistency
            'frame_length': self.frame_length,  # Add these for consistency  
            'qubit_capacities': self.qubit_capacities,  # Add these for consistency
            'config': {
                'qubit_capacities': self.qubit_capacities,
                'frame_length': self.frame_length,
                'num_paths': self.num_paths,
                'attack_strategy': "NoAttack",
                'environment_type': self.__class__.__name__  # Add for consistency
            },
        }

    def _generate_contexts(self):
        ctxs = []
        for path_idx, capacity in enumerate(self.qubit_capacities):
            if path_idx < 2:  # 2-hop
                path_ctx = [np.array([i, capacity - i]) for i in range(capacity + 1)]
            else:            # 3-hop
                path_ctx = []
                for i in range(capacity + 1):
                    for j in range(capacity + 1 - i):
                        path_ctx.append(np.array([i, j, capacity - i - j]))
            ctxs.append(np.array(path_ctx))
        return ctxs

    def _calculate_path_rewards(self):
        A = self.frame_length
        # same math as your code, just compact
        def p(pe): return 1 - (1 - pe) ** A
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
        r3 = [(1 - (1 - p1) ** c[0]) * (1 - (1 - p2) ** c[1]) * (1 - (1 - p3) ** c[2])
              for c in self.contexts[2]]
        # Path 4
        pe1, pe2, pe3 = 1.5e-4, 1.5e-4, 1.5e-4
        p1, p2, p3 = p(pe1), p(pe2), p(pe3)
        r4 = [(1 - (1 - p1) ** c[0]) * (1 - (1 - p2) ** c[1]) * (1 - (1 - p3) ** c[2])
              for c in self.contexts[3]]
        return [r1, r2, r3, r4]

    def generate_attack_pattern(self) -> np.ndarray:
        """Default: no attacks."""
        return np.ones((self.frame_length, self.num_paths), dtype=int)

    def oracle(self, attack_pattern: np.ndarray | None = None):
        """Vectorized oracle (fast)."""
        if attack_pattern is None:
            attack_pattern = self.generate_attack_pattern()
        # count frames not attacked by path
        not_attacked = attack_pattern.sum(axis=0)  # shape (num_paths,)
        best_total = -1.0
        best_path, best_action = 0, 0
        for p in range(self.num_paths):
            rewards = np.asarray(self.reward_list[p])              # (actions,)
            totals = rewards * float(not_attacked[p])              # vectorized
            a = int(np.argmax(totals))
            if totals[a] > best_total:
                best_total = float(totals[a])
                best_path, best_action = p, a
        return {"oracle_path": best_path, "oracle_action": best_action, "oracle_total_reward": best_total}

    # Optional: a read-only alias property if you want symmetry everywhere
    @property
    def reward_functions(self):
        return self.reward_list    

# =============================================================================
# ADVERSARIAL ENVIRONMENT
# =============================================================================

class AdversarialQuantumEnvironment(QuantumEnvironment):
    """
    QuantumEnvironment + pluggable AttackStrategy
    Enhanced to support num_qubits and topology parameters
    """
    def __init__(self, 
                 qubit_capacities=(8, 10, 8, 9), 
                 frame_length=4000,
                 attack: AttackStrategy | None = None, 
                 seed: int | None = None,
                 # NEW: Add missing parameters that setup_environment expects
                 num_qubits: int | None = None,
                 topology: str | None = None,
                 attack_strategy: AttackStrategy | None = None):
        
        # Handle legacy parameter mapping
        if attack_strategy is not None:
            attack = attack_strategy
        
        # Handle num_qubits parameter
        if num_qubits is not None:
            self.num_qubits = int(num_qubits)
        else:
            self.num_qubits = sum(qubit_capacities) if qubit_capacities else 33
        
        # Handle topology parameter
        self.topology = topology or "mesh"
        
        # Call parent constructor
        super().__init__(qubit_capacities=qubit_capacities, frame_length=frame_length, seed=seed)
        
        # Set up attack strategy
        self.attack: AttackStrategy = attack or NoAttack()
        
        # Generate attack pattern once per environment
        self.attack_pattern = self.attack.generate(
            self.rng, self.frame_length, self.num_paths
        ).astype(np.int8, copy=False)
        
        self._print_attack_info()

    def _print_attack_info(self):
        """Clean tabular attack strategy info"""
        print("\nADVERSARIAL CONFIGURATION:")
        print("=" * 50)
        print(f"| Attack Strategy:  | {self.attack.__class__.__name__:<15} |")
        print(f"| Num Qubits:       | {self.num_qubits:<15} |")
        print(f"| Topology:         | {self.topology:<15} |")
        print(f"| Paths:            | {self.num_paths:<15} |")
        
        # Add strategy-specific parameters
        if hasattr(self.attack, 'attack_rate'):
            print(f"| Attack Rate:      | {self.attack.attack_rate:<15.2f} |")
        if hasattr(self.attack, 'k_attacks'):
            print(f"| Simultaneous:     | {self.attack.k_attacks:<15} |")
        if hasattr(self.attack, 'memory_window'):
            print(f"| Memory Window:    | {self.attack.memory_window:<15} |")
        if hasattr(self.attack, 'temperature'):
            temp = self.attack.temperature if self.attack.temperature is not None else "Greedy"
            print(f"| Selection Mode:   | {str(temp):<15} |")
            
        print("=" * 50)

    def generate_attack_pattern(self):
        return self.attack_pattern

    def regenerate(self, *, frame_length: int | None = None, seed: int | None = None,
                   attack: AttackStrategy | None = None, selection_trace: list[int] | None = None):
        """Support selection_trace for adaptive attacks and keep dtype consistency."""
        if frame_length is not None:
            self.frame_length = int(frame_length)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        if attack is not None:
            self.attack = attack

        # Recompute rewards (A changed) and re-roll attack sequence
        self.reward_list = self._calculate_path_rewards()
        self.attack_pattern = self.attack.generate(
            self.rng, self.frame_length, self.num_paths, selection_trace=selection_trace
        ).astype(np.int8, copy=False)

    def get_environment_info(self) -> dict:
        """
        Return standardized environment information with consistent, read-only
        attack pattern for downstream consumers (runners/tools).
        """
        attack = self.attack_pattern.astype(np.int8, copy=False)
        attack.setflags(write=False)  # make read-only on the payload

        return {
            'contexts': self.contexts,
            'reward_functions': self.reward_list,
            'attack_pattern': attack,
            'num_paths': self.num_paths,
            'frame_length': self.frame_length,
            'qubit_capacities': self.qubit_capacities,
            'attack_strategy': self.attack.__class__.__name__,
            'config': {
                'qubit_capacities': self.qubit_capacities,
                'frame_length': self.frame_length,
                'num_paths': self.num_paths,
                'attack_strategy': self.attack.__class__.__name__,
                'has_adaptive_attacks': hasattr(self.attack, 'observe'),
                'environment_type': self.__class__.__name__,
            },
        }

    def analyze_attacks(self):
        """ENHANCED: Comprehensive attack analysis with clean tabular output."""
        arr = self.attack_pattern
        counts = (arr == 0).sum(axis=0)
        
        analysis = {
            "total_frames": int(arr.shape[0]),
            "num_paths": int(arr.shape[1]),
            "attacks_per_path": counts.tolist(),
            "attack_rates_per_path": (counts / arr.shape[0]).astype(float).tolist(),
            "mean_attacks_per_frame": float((arr == 0).sum() / arr.shape[0]),
            "total_attack_events": int((arr == 0).sum()),
            "attack_strategy": self.attack.__class__.__name__,
            "no_attack_probability": float((arr == 1).sum() / arr.size),
            "attack_intensity": float(counts.sum() / arr.size)  # NEW: Overall intensity metric
        }
        
        # Print clean tabular analysis
        print("\nATTACK PATTERN ANALYSIS:")
        print("=" * 60)
        print(f"| Strategy:         | {analysis['attack_strategy']:<20} |")
        print(f"| Total Frames:     | {analysis['total_frames']:,}                    |")
        print(f"| Total Attacks:    | {analysis['total_attack_events']:,}                    |")
        print(f"| Attack Intensity: | {analysis['attack_intensity']:.3f}                |")
        print("-" * 60)
        print("| PATH-SPECIFIC ANALYSIS:                          |")
        print("-" * 60)
        
        for i in range(analysis['num_paths']):
            path_attacks = analysis['attacks_per_path'][i]
            path_rate = analysis['attack_rates_per_path'][i]
            print(f"| Path {i}:          | {path_attacks:>6} attacks ({path_rate:>5.1%} rate) |")
        
        print("=" * 60)
        
        return analysis

    def reset_environment(self, *, frame_length: int | None = None, seed: int | None = None,
                         attack: AttackStrategy | None = None, selection_trace: list[int] | None = None):
        """
        FIXED: Reset environment for a new experiment run.
        Now includes selection_trace support for adaptive attacks.
        """
        self.regenerate(
            frame_length=frame_length, 
            seed=seed, 
            attack=attack, 
            selection_trace=selection_trace  # Pass selection_trace
        )
        return self.get_environment_info()

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

def print_environment_comparison():
    """Clean comparison of environment types"""
    print("\nENVIRONMENT COMPARISON:")
    print("=" * 70)
    
    # Base environment (no attacks)
    base_env = QuantumEnvironment()
    base_oracle = base_env.get_oracle_solution()
    
    print("\nBASE ENVIRONMENT RESULTS:")
    print("-" * 40)
    print(f"| Optimal Path:     | {base_oracle['oracle_path']:<15} |")
    print(f"| Optimal Action:   | {base_oracle['oracle_action']:<15} |") 
    print(f"| Oracle Reward:    | {base_oracle['oracle_total_reward']:<15.2f} |")
    print("-" * 40)
    
    # Adversarial environment (inherits everything + adds attacks)
    markov_attack = MarkovAttack(attack_rate=1.0, k_attacks=2)
    adv_env = AdversarialQuantumEnvironment(attack=markov_attack)
    adv_oracle = adv_env.get_oracle_solution()
    
    print("\nADVERSARIAL ENVIRONMENT RESULTS:")
    print("-" * 40)
    print(f"| Optimal Path:     | {adv_oracle['oracle_path']:<15} |")
    print(f"| Optimal Action:   | {adv_oracle['oracle_action']:<15} |")
    print(f"| Oracle Reward:    | {adv_oracle['oracle_total_reward']:<15.2f} |")
    print("-" * 40)
    
    # Attack analysis
    attack_stats = adv_env.analyze_attacks()
    
    # Test polymorphism - both are QuantumEnvironments
    print("\nPOLYMORPHISM TEST:")
    print("-" * 50)
    environments = [base_env, adv_env]
    for i, env in enumerate(environments):
        context_shapes = [len(ctx) for ctx in env.contexts]
        attack_shape = env.generate_attack_pattern().shape
        print(f"| Environment {i+1}:   | {type(env).__name__:<20} |")
        print(f"|   Context Sizes:  | {str(context_shapes):<20} |")
        print(f"|   Attack Shape:   | {str(attack_shape):<20} |")
        print("-" * 50)
    
    print("=" * 70)

def demonstrate_attack_strategies():
    """Demonstrate different attack strategy configurations"""
    print("\nATTACK STRATEGY DEMONSTRATIONS:")
    print("=" * 60)
    
    strategies = [
        ("No Attack", NoAttack()),
        ("Random (25%)", RandomAttack(attack_rate=0.25)),
        ("Markov Chain", MarkovAttack(k_attacks=1, attack_rate=0.8)),
        ("Adaptive", AdaptiveAttack(memory_window=30, attack_rate=0.9)),
        ("Online Adaptive", OnlineAdaptiveAttack(k=2, temperature=0.5))
    ]
    
    for name, strategy in strategies:
        env = AdversarialQuantumEnvironment(
            frame_length=1000, 
            attack=strategy,
            seed=42
        )
        
        oracle_result = env.oracle()
        print(f"\n{name.upper()} STRATEGY:")
        print("-" * 40)
        print(f"| Oracle Path:      | {oracle_result['oracle_path']:<15} |")
        print(f"| Oracle Reward:    | {oracle_result['oracle_total_reward']:<15.2f} |")
        
        # Quick attack stats
        attacks = (env.attack_pattern == 0).sum()
        intensity = attacks / env.attack_pattern.size
        print(f"| Attack Events:    | {attacks:<15} |")
        print(f"| Attack Intensity: | {intensity:<15.3f} |")
        print("-" * 40)

# if __name__ == "__main__":
#     print("QUANTUM ENVIRONMENT TESTING")
#     print("=" * 70)
    
#     print_environment_comparison()
#     demonstrate_attack_strategies()

# # =============================================================================
# # USAGE EXAMPLES
# # =============================================================================

# if __name__ == "__main__":
#     print("Testing inheritance structure:\n")
    
#     # Base environment (no attacks)
#     base_env = QuantumEnvironment()
#     base_oracle = base_env.get_oracle_solution()
#     print(f"Base Oracle: Path {base_oracle['oracle_path']}, Reward: {base_oracle['oracle_total_reward']:.2f}")
    
#     print("\n" + "="*50)
    
#     # Adversarial environment (inherits everything + adds attacks)
#     adv_env = AdversarialQuantumEnvironment(attack_type='markov', attack_intensity=1.0)
#     adv_oracle = adv_env.get_oracle_solution()
#     print(f"Adversarial Oracle: Path {adv_oracle['oracle_path']}, Reward: {adv_oracle['oracle_total_reward']:.2f}")
    
#     # Test polymorphism - both are QuantumEnvironments
#     environments = [base_env, adv_env]
#     for i, env in enumerate(environments):
#         print(f"Environment {i+1}: {type(env).__name__}")
#         print(f"  Contexts shape: {[len(ctx) for ctx in env.contexts]}")
#         print(f"  Attack pattern shape: {env.generate_attack_pattern().shape}")
