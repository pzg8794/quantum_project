"""
Dynamic Qubit Allocation Strategies for Quantum Routing
"""
import numpy as np
from typing import Dict, Tuple


# ============================================================
# Base Allocator (Fixed baseline)
# ============================================================
class QubitAllocator:
    """Fixed allocation baseline - maintains static allocation"""
    
    def __init__(self, total_qubits: int = 35, num_routes: int = 4, min_qubits_per_route: int = 1):
        self.allocated = False
        self.num_routes = num_routes
        self.total_qubits = total_qubits
        self.min_qubits_per_route = min_qubits_per_route
    
    def has_allocated(self):
        return self.allocated

    def allocate(self, timestep: int, route_stats: Dict[int, Dict], verbose=True) -> Tuple[int, ...]:
        """Returns tuple of qubits per route."""
        self.allocated = True
        allocation = (8, 10, 8, 9)
        if verbose:
            print(f"[FixedAllocator] timestep={timestep} → allocation={allocation}")
        return allocation
    
    def get_config(self):
        """Return allocator configuration as dict"""
        return {
            'total_qubits': self.total_qubits,
            'num_routes': self.num_routes,
            'min_qubits_per_route': self.min_qubits_per_route
        }
    
    def __repr__(self):
        return self.__class__.__name__


# ============================================================
# Random Allocator with Epsilon Control
# ============================================================
class RandomQubitAllocator(QubitAllocator):
    """
    Epsilon-controlled random allocation for exploration-exploitation analysis.
    
    Parameters:
    -----------
    epsilon : float (0.0 to 1.0)
        Degree of randomness:
        - 0.0 = Fully deterministic (fixed allocation)
        - 0.5 = 50% random, 50% baseline
        - 1.0 = Fully random
    
    epsilon_decay : float (0.0 to 1.0)
        Multiplicative decay per timestep (default 1.0 = no decay)
        
    min_epsilon : float
        Minimum epsilon value after decay
    """
    
    def __init__(self, total_qubits: int = 35, num_routes: int = 4, 
                 min_qubits_per_route: int = 2, epsilon: float = 1.0,
                 epsilon_decay: float = 1.0, min_epsilon: float = 0.1,
                 seed: int = None):
        super().__init__(total_qubits, num_routes, min_qubits_per_route)
        
        # Randomness control
        self.epsilon = epsilon
        self.initial_epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        
        # Fixed baseline for epsilon=0 case
        self.baseline_allocation = (8, 10, 8, 9)
        
        # Random state
        self.rng = np.random.RandomState(seed)
        self.allocation_history = []
    
    def allocate(self, timestep: int, route_stats: Dict[int, Dict], verbose=True) -> Tuple[int, ...]:
        """
        Allocate with epsilon-controlled randomness.
        Mixes baseline allocation with random allocation based on epsilon.
        """
        # Decay epsilon over time if configured
        if timestep > 0 and self.epsilon_decay < 1.0:
            self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
        
        # Decide: random or baseline
        if self.rng.random() < self.epsilon:
            # Random allocation
            allocation = self._random_allocate()
            mode = "random"
        else:
            # Baseline allocation
            allocation = self.baseline_allocation
            mode = "baseline"
        
        self.allocation_history.append((timestep, allocation, mode))
        if verbose:
            print(f"[RandomAllocator ε={self.epsilon:.3f}] timestep={timestep} mode={mode} → allocation={allocation}")
        return allocation
    
    def _random_allocate(self) -> Tuple[int, ...]:
        """Pure random allocation using Dirichlet distribution."""
        # Reserve minimum qubits per route
        available_qubits = self.total_qubits - (self.num_routes * self.min_qubits_per_route)
        
        if available_qubits <= 0:
            return tuple([self.min_qubits_per_route] * self.num_routes)
        
        # Sample random proportions from Dirichlet(1,1,1,1)
        alpha = [1.0] * self.num_routes
        proportions = self.rng.dirichlet(alpha)
        
        # Allocate proportionally
        allocation = [self.min_qubits_per_route] * self.num_routes
        for i, prop in enumerate(proportions):
            allocation[i] += int(prop * available_qubits)
        
        # Distribute remainder
        total_allocated = sum(allocation)
        if total_allocated < self.total_qubits:
            indices = list(range(self.num_routes))
            self.rng.shuffle(indices)
            for i in range(self.total_qubits - total_allocated):
                allocation[indices[i % self.num_routes]] += 1
        
        return tuple(allocation)
    
    def get_config(self):
        """Return allocator configuration"""
        config = super().get_config()
        config.update({
            'epsilon': self.epsilon,
            'initial_epsilon': self.initial_epsilon,
            'epsilon_decay': self.epsilon_decay,
            'min_epsilon': self.min_epsilon,
            'baseline': self.baseline_allocation
        })
        return config


# ============================================================
# Dynamic Qubit Allocator (UCB-based)
# ============================================================
class DynamicQubitAllocator(QubitAllocator):
    """UCB-based dynamic allocation"""
    
    def __init__(self, total_qubits: int = 35, num_routes: int = 4,
                 min_qubits_per_route: int = 2, exploration_bonus: float = 2.0):
        super().__init__(total_qubits, num_routes, min_qubits_per_route)
        self.exploration_bonus = exploration_bonus
        self.allocation_history = []
    
    def allocate(self, timestep: int, route_stats: Dict[int, Dict], verbose=True) -> Tuple[int, ...]:
        """Allocate qubits proportional to UCB scores."""
        if not route_stats or timestep == 0:
            base = self.total_qubits // self.num_routes
            remainder = self.total_qubits % self.num_routes
            allocation = [base] * self.num_routes
            for i in range(remainder):
                allocation[i] += 1
            result = tuple(allocation)
            if verbose:
                print(f"[DynamicUCBAllocator] timestep={timestep} (initial) → allocation={result}")
            return result
        
        # Calculate UCB scores
        total_pulls = sum(stats.get('pulls', 0) for stats in route_stats.values())
        ucb_scores = []
        for route_id in range(self.num_routes):
            stats = route_stats.get(route_id, {'success_rate': 0.5, 'pulls': 1})
            success_rate = stats.get('success_rate', 0.5)
            pulls = max(stats.get('pulls', 1), 1)
            exploration_term = np.sqrt(self.exploration_bonus * np.log(max(total_pulls, 1)) / pulls)
            ucb_score = success_rate + exploration_term
            ucb_scores.append(ucb_score)
        
        # Normalize and allocate
        total_score = sum(ucb_scores)
        if total_score == 0:
            proportions = [1.0 / self.num_routes] * self.num_routes
        else:
            proportions = [s / total_score for s in ucb_scores]
        
        available_qubits = self.total_qubits - (self.num_routes * self.min_qubits_per_route)
        allocation = [self.min_qubits_per_route] * self.num_routes
        for i, prop in enumerate(proportions):
            allocation[i] += int(prop * available_qubits)
        
        total_allocated = sum(allocation)
        if total_allocated < self.total_qubits:
            sorted_indices = sorted(range(self.num_routes), key=lambda i: ucb_scores[i], reverse=True)
            for i in range(self.total_qubits - total_allocated):
                allocation[sorted_indices[i % self.num_routes]] += 1
        
        result = tuple(allocation)
        self.allocation_history.append((timestep, result))
        if verbose:
            print(f"[DynamicUCBAllocator] timestep={timestep} → allocation={result}")
        return result


# ============================================================
# Thompson Sampling Allocator
# ============================================================
class ThompsonSamplingAllocator(QubitAllocator):
    """Thompson Sampling-based allocation"""
    
    def __init__(self, total_qubits: int = 35, num_routes: int = 4,
                 min_qubits_per_route: int = 2):
        super().__init__(total_qubits, num_routes, min_qubits_per_route)
        self.alpha = [1] * num_routes
        self.beta = [1] * num_routes
        self.allocation_history = []
    
    def allocate(self, timestep: int, route_stats: Dict[int, Dict], verbose=True) -> Tuple[int, ...]:
        """Allocate based on Thompson Sampling."""
        if not route_stats or timestep == 0:
            base = self.total_qubits // self.num_routes
            remainder = self.total_qubits % self.num_routes
            allocation = [base] * self.num_routes
            for i in range(remainder):
                allocation[i] += 1
            result = tuple(allocation)
            if verbose:
                print(f"[ThompsonAllocator] timestep={timestep} (initial) → allocation={result}")
            return result
        
        samples = []
        for route_id in range(self.num_routes):
            stats = route_stats.get(route_id, {})
            successes = stats.get('successes', 0)
            failures = stats.get('failures', 0)
            self.alpha[route_id] = successes + 1
            self.beta[route_id] = failures + 1
            samples.append(np.random.beta(self.alpha[route_id], self.beta[route_id]))
        
        total_sample = sum(samples)
        proportions = [s / total_sample for s in samples] if total_sample > 0 else [1.0 / self.num_routes] * self.num_routes
        
        available_qubits = self.total_qubits - (self.num_routes * self.min_qubits_per_route)
        allocation = [self.min_qubits_per_route] * self.num_routes
        for i, prop in enumerate(proportions):
            allocation[i] += int(prop * available_qubits)
        
        total_allocated = sum(allocation)
        if total_allocated < self.total_qubits:
            sorted_indices = sorted(range(self.num_routes), key=lambda i: samples[i], reverse=True)
            for i in range(self.total_qubits - total_allocated):
                allocation[sorted_indices[i % self.num_routes]] += 1
        
        result = tuple(allocation)
        self.allocation_history.append((timestep, result))
        if verbose:
            print(f"[ThompsonAllocator] timestep={timestep} → allocation={result}")
        return result
