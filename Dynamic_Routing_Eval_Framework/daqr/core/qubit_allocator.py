"""
    qubit_allocator.py - Dynamic Qubit Allocation Strategies
"""

import numpy as np
from typing import Dict, Tuple

# ============================================================
# Base Allocator (Fixed baseline)
# ============================================================
class QubitAllocator:
    """Fixed allocation baseline - maintains static allocation."""
    def __init__(self, total_qubits: int = 35, num_routes: int = None, num_paths: int = None, min_qubits_per_route: int = 1,
                 baseline_allocation: Tuple[int, ...] | None = None, has_uniform_base=False, testbed: str = "default", testbed_config: Dict = {}, exploration_bonus=None):
        # ✅ Accept both num_routes and num_paths parameters
        self.exploration_bonus = exploration_bonus
        if num_paths is not None:   num_routes = num_paths
        elif num_routes is None:    num_routes = 4  # Default fallback
        
        self.allocated = False
        self.num_routes = num_routes
        self.total_qubits = total_qubits
        self.min_qubits_per_route = min_qubits_per_route

        self.testbed = testbed
        self.testbed_config = testbed_config
        self.has_uniform_base = has_uniform_base
        self.baseline_allocation = baseline_allocation
    
    def _uniform_baseline(self) -> Tuple[int, ...]:
        """Uniform distribution across all routes"""
        base = self.total_qubits // self.num_routes
        rem = self.total_qubits % self.num_routes
        alloc = [base] * self.num_routes
        
        for i in range(rem): alloc[i] += 1
        alloc = [max(a, self.min_qubits_per_route) for a in alloc]
        return tuple(alloc)
    
    def _proportional_allocation(self, proportions: list) -> Tuple[int, ...]:
        """Generic proportional allocation (capacity-agnostic)."""
        total_prop = sum(proportions)
        normalized = [p / total_prop for p in proportions]
        available = self.total_qubits - (self.num_routes * self.min_qubits_per_route)
        if available <= 0:  return tuple([self.min_qubits_per_route] * self.num_routes)
        
        alloc = [self.min_qubits_per_route] * self.num_routes
        for i, prop in enumerate(normalized):   alloc[i] += int(prop * available)
        
        remainder = self.total_qubits - sum(alloc)
        if remainder > 0:
            indices = sorted(range(len(normalized)), key=lambda i: normalized[i], reverse=True)
            for i in range(remainder):  alloc[indices[i % self.num_routes]] += 1
        elif remainder < 0:
            indices = sorted(range(len(normalized)), key=lambda i: normalized[i])
            for i in range(abs(remainder)):
                idx = indices[i % self.num_routes]
                if alloc[idx] > self.min_qubits_per_route:  alloc[idx] -= 1
        return tuple(alloc)
    
    def _default_baseline(self) -> Tuple[int, ...]:
        """CAPACITY-AGNOSTIC baseline allocation."""
        # 🆕 Paper2: Return state-based capacities (don't override)
        if self.testbed == "paper2":
            # Paper2 manages its own BUSY/IDLE state transitions
            # Read current state from config if available
            current_state = self.testbed_config.get('initial_state', 'busy').lower()
            if current_state == 'busy': return (8, 10, 8, 9)  # BUSY state capacity
            elif current_state == 'idle':   return (9, 11, 11, 12)  # IDLE state capacity
            else:
                # Fallback to BUSY if state unknown
                print(f"⚠️ Unknown Paper2 state '{current_state}', defaulting to BUSY")
                return (8, 10, 8, 9)
        # Paper12: Uniform allocation
        elif self.testbed == "paper12": return self._uniform_baseline()
        # Paper7: Uniform allocation
        elif self.testbed == "paper7":  return self._uniform_baseline()
        # Default: Proportional allocation
        else:
            if self.num_routes == 4: return self._proportional_allocation([8, 10, 8, 9])
            PATTERN = [8, 10, 8, 9]
            proportions = [PATTERN[i % len(PATTERN)] for i in range(self.num_routes)]
            return self._proportional_allocation(proportions)
    
    def has_allocated(self):    return self.allocated
    
    def allocate(self, timestep: int, route_stats: Dict[int, Dict], verbose=True) -> Tuple[int, ...]:
        """Returns tuple of qubits per route."""
        self.allocated = True
        
        if self.baseline_allocation is not None:
            allocation = tuple(self.baseline_allocation)
            if len(allocation) != self.num_routes: raise ValueError(f"baseline_allocation length {len(allocation)} != num_routes {self.num_routes}")
        elif self.has_uniform_base:     allocation = self._uniform_baseline()
        else:   allocation = self._default_baseline()

        if verbose: print(f"[{self.__class__.__name__}] timestep={timestep} → allocation={allocation}")
        return allocation
    
    def get_config(self):
        return {'total_qubits': self.total_qubits, 'num_routes': self.num_routes, 'min_qubits_per_route': self.min_qubits_per_route, 'testbed': self.testbed}
    
    def __repr__(self):
        alloc = self.__class__.__name__.replace("QubitAllocator", "")
        return "Default" if not alloc else alloc.replace("Allocator", "")
    
    def __eq__(self, other):
        if not isinstance(other, QubitAllocator):   return NotImplemented
        return (type(self) is type(other) and self.num_routes == other.num_routes
            and self.total_qubits == other.total_qubits and self.min_qubits_per_route == other.min_qubits_per_route)


# ============================================================
# Random Allocator
# ============================================================
class RandomQubitAllocator(QubitAllocator):
    """Epsilon-controlled random allocation."""
    def __init__(self, total_qubits: int = 35, num_routes: int = None, num_paths: int = None, min_qubits_per_route: int = 2, epsilon: float = 1.0, 
                 epsilon_decay: float = 1.0, min_epsilon: float = 0.1, seed: int = None, testbed: str = "default", testbed_config: Dict = {}, exploration_bonus=None):
        if num_paths is not None:   num_routes = num_paths
        elif num_routes is None:    num_routes = 4
        super().__init__(total_qubits, num_routes, num_paths=None, min_qubits_per_route=min_qubits_per_route, testbed=testbed, testbed_config=testbed_config, exploration_bonus=exploration_bonus)
        
        self.epsilon = epsilon
        self.allocation_history = []
        self.initial_epsilon = epsilon
        self.min_epsilon = min_epsilon
        self.epsilon_decay = epsilon_decay
        self.rng = np.random.RandomState(seed)
        self.baseline_allocation = self._default_baseline()
    
    def allocate(self, timestep: int, route_stats: Dict[int, Dict], verbose=True) -> Tuple[int, ...]:
        if timestep > 0 and self.epsilon_decay < 1.0: self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
        
        mode = "baseline"
        allocation = self.baseline_allocation
        if self.rng.random() < self.epsilon:
            allocation = self._random_allocate()
            mode = "random"
            
        self.allocation_history.append((timestep, allocation, mode))
        if verbose: print(f"[RandomAllocator ε={self.epsilon:.3f}] timestep={timestep} mode={mode} → allocation={allocation}")
        return allocation
    
    def _random_allocate(self) -> Tuple[int, ...]:
        available_qubits = self.total_qubits - (self.num_routes * self.min_qubits_per_route)
        if available_qubits <= 0:   return tuple([self.min_qubits_per_route] * self.num_routes)
        
        alpha = [1.0] * self.num_routes
        proportions = self.rng.dirichlet(alpha)
        allocation = [self.min_qubits_per_route] * self.num_routes
        for i, prop in enumerate(proportions):  allocation[i] += int(prop * available_qubits)
        
        total_allocated = sum(allocation)
        if total_allocated < self.total_qubits:
            indices = list(range(self.num_routes))
            self.rng.shuffle(indices)
            for i in range(self.total_qubits - total_allocated):    allocation[indices[i % self.num_routes]] += 1
        return tuple(allocation)
    
    def get_config(self):
        config = super().get_config()
        config.update({'epsilon': self.epsilon, 'initial_epsilon': self.initial_epsilon, 'epsilon_decay': self.epsilon_decay,
            'min_epsilon': self.min_epsilon, 'baseline': self.baseline_allocation})
        return config


# ============================================================
# Dynamic Allocator (UCB-based)
# ============================================================
class DynamicQubitAllocator(QubitAllocator):
    """UCB based dynamic allocation."""
    def __init__(self, total_qubits: int = 35, num_routes: int = None, num_paths: int = None, min_qubits_per_route: int = 2, epsilon: float = 1.0, 
                 epsilon_decay: float = 1.0, min_epsilon: float = 0.1, seed: int = None, testbed: str = "default", testbed_config: Dict = {}, exploration_bonus=None):
        if num_paths is not None:   num_routes = num_paths
        elif num_routes is None:    num_routes = 4
        super().__init__(total_qubits, num_routes, num_paths=None, min_qubits_per_route=min_qubits_per_route, testbed=testbed, testbed_config=testbed_config, exploration_bonus=exploration_bonus)
        self.rng = np.random.RandomState(seed)
        self.allocation_history = []
    
    def allocate(self, timestep: int, route_stats: Dict[int, Dict], verbose=True) -> Tuple[int, ...]:
        if not route_stats or timestep == 0:    return self._initial_uniform_allocation(timestep, verbose)
        total_pulls = sum(stats.get('pulls', 0) for stats in route_stats.values())
        ucb_scores = []
        
        for route_id in range(self.num_routes):
            stats = route_stats.get(route_id, {'success_rate': 0.5, 'pulls': 1})
            success_rate = stats.get('success_rate', 0.5)
            pulls = max(stats.get('pulls', 1), 1)
            
            exploration_term = np.sqrt(self.exploration_bonus * np.log(max(total_pulls, 1)) / pulls)
            ucb_score = success_rate + exploration_term
            ucb_scores.append(ucb_score)
        
        result = self._allocate_by_scores(ucb_scores)
        self.allocation_history.append((timestep, result))
        if verbose: print(f"[DynamicAllocator UCB] timestep={timestep} → allocation={result}")
        return result
    
    def _initial_uniform_allocation(self, timestep: int, verbose: bool) -> Tuple[int, ...]:
        base = self.total_qubits // self.num_routes
        remainder = self.total_qubits % self.num_routes
        allocation = [base] * self.num_routes
        for i in range(remainder):  allocation[i] += 1
        result = tuple(allocation)
        
        if verbose: print(f"[DynamicAllocator] timestep={timestep} (uniform init) → allocation={result}")
        return result
    
    def _allocate_by_scores(self, scores: list) -> Tuple[int, ...]:
        scores = np.array(scores)
        scores = np.maximum(scores, 0.01)
        proportions = scores / scores.sum()
        available = self.total_qubits - (self.num_routes * self.min_qubits_per_route)
        
        allocation = [self.min_qubits_per_route] * self.num_routes
        for i, prop in enumerate(proportions):  allocation[i] += int(prop * available)
        remainder = self.total_qubits - sum(allocation)
        sorted_indices = np.argsort(scores)[::-1]
        
        for i in range(abs(remainder)):
            if remainder > 0:   allocation[sorted_indices[i % self.num_routes]] += 1
            else:
                idx = sorted_indices[-(i % self.num_routes) - 1]
                if allocation[idx] > self.min_qubits_per_route: allocation[idx] -= 1
        return tuple(allocation)
    
    def get_config(self):
        config = super().get_config()
        config.update({'exploration_bonus': self.exploration_bonus})
        return config


# ============================================================
# Thompson Sampling Allocator
# ============================================================
class ThompsonSamplingAllocator(QubitAllocator):
    """Thompson Sampling based dynamic allocation."""
    def __init__(self, total_qubits: int = 35, num_routes: int = None, num_paths: int = None, min_qubits_per_route: int = 2,
                 alpha_prior: float = 1.0, beta_prior: float = 1.0, seed: int = None, testbed: str = "default", testbed_config: Dict = {}, exploration_bonus=None):
        if num_paths is not None:   num_routes = num_paths
        elif num_routes is None:    num_routes = 4
        super().__init__(total_qubits, num_routes, num_paths=None, min_qubits_per_route=min_qubits_per_route, testbed=testbed, testbed_config=testbed_config, exploration_bonus=exploration_bonus)
        
        self.allocation_history = []
        self.beta_prior = beta_prior
        self.alpha_prior = alpha_prior
        self.rng = np.random.RandomState(seed)
        self.beta_posterior = np.ones(self.num_routes) * beta_prior
        self.alpha_posterior = np.ones(self.num_routes) * alpha_prior
    
    def allocate(self, timestep: int, route_stats: Dict[int, Dict], verbose=True) -> Tuple[int, ...]:
        if not route_stats or timestep == 0:    return self._initial_uniform_allocation(timestep, verbose)
        
        for route_id in range(self.num_routes):
            failures = stats.get('failures', 0)
            stats = route_stats.get(route_id, {})
            successes = stats.get('successes', 0)
            self.beta_posterior[route_id] = self.beta_prior + failures
            self.alpha_posterior[route_id] = self.alpha_prior + successes
        
        result = self._allocate_by_samples(samples)
        self.allocation_history.append((timestep, result))
        samples = self.rng.beta(self.alpha_posterior, self.beta_posterior)
        if verbose: print(f"[ThompsonAllocator] timestep={timestep} → allocation={result}")
        return result
    
    def _initial_uniform_allocation(self, timestep: int, verbose: bool) -> Tuple[int, ...]:
        remainder = self.total_qubits % self.num_routes
        base = self.total_qubits // self.num_routes
        allocation = [base] * self.num_routes

        for i in range(remainder):  allocation[i] += 1
        result = tuple(allocation)
        if verbose: print(f"[ThompsonAllocator] timestep={timestep} (uniform init) → allocation={result}")
        return result
    
    def _allocate_by_samples(self, samples: np.ndarray) -> Tuple[int, ...]:
        proportions = samples / samples.sum()
        allocation = [self.min_qubits_per_route] * self.num_routes
        available = self.total_qubits - (self.num_routes * self.min_qubits_per_route)
        
        for i, prop in enumerate(proportions):  allocation[i] += int(prop * available)
        remainder = self.total_qubits - sum(allocation)
        sorted_indices = np.argsort(samples)[::-1]
        
        for i in range(abs(remainder)):
            if remainder > 0:   allocation[sorted_indices[i % self.num_routes]] += 1
            else:
                idx = sorted_indices[-(i % self.num_routes) - 1]
                if allocation[idx] > self.min_qubits_per_route: allocation[idx] -= 1
        return tuple(allocation)
    
    def get_config(self):
        config = super().get_config()
        config.update({'beta_prior': self.beta_prior, 'alpha_prior': self.alpha_prior, 'beta_posterior': self.beta_posterior.tolist(), 'alpha_posterior': self.alpha_posterior.tolist()})
        return config
