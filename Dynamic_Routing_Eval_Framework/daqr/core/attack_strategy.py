"""
Attack strategies for quantum network adversarial scenarios.
Extracted from network_environment.py for better separation of concerns.
"""
import numpy as np


# ============================================================================
# BASE ATTACK STRATEGY
# ============================================================================

class AttackStrategy:
    """Base class for attack strategies."""
    def __init__(self, attack_rate=0.25):
        self.attack_rate = attack_rate
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        """
        Generate attack mask.
        
        Args:
            rng: NumPy random generator
            frame_length: Number of time frames
            num_paths: Number of paths
            selection_trace: Optional trace of path selections
        
        Returns:
            Binary mask (T × P): 1 = success, 0 = failure
        """
        raise NotImplementedError

    def __del__(self):
        """Ensure cleanup is called when the object is destroyed."""
        # self.cleanup()

    def __repr__(self):
        env = self.__class__.__name__
        return env


# ============================================================================
# NO ATTACK
# ============================================================================

class NoAttack(AttackStrategy):
    """No attack - all paths always succeed."""
    def __init__(self):
        super().__init__(attack_rate=0.0)
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        return np.ones((frame_length, num_paths), dtype=int)


# ============================================================================
# RANDOM ATTACK (ENHANCED)
# ============================================================================

class RandomAttack(AttackStrategy):
    """
    Random attack with optional path-dependent rates.
    
    Args:
        attack_rate: Global attack rate (used if per_path_rates is None)
        per_path_rates: Optional array of per-path attack rates [p1, p2, ...]
    """
    def __init__(self, attack_rate=0.25, per_path_rates=None):
        super().__init__(attack_rate)
        self.per_path_rates = per_path_rates
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        if self.per_path_rates is not None:
            # Path-dependent noise (for Paper #2, etc.)
            mask = np.ones((frame_length, num_paths), dtype=int)
            for p in range(num_paths):
                rate = self.per_path_rates[p]
                mask[:, p] = (rng.random(frame_length) >= rate).astype(int)
            return mask
        else:
            # Original global rate
            mask = rng.random((frame_length, num_paths)) >= self.attack_rate
            return mask.astype(int)


# ============================================================================
# MARKOV ATTACK
# ============================================================================

class MarkovAttack(AttackStrategy):
    """
    Markov-based attack with state transitions.
    
    Args:
        attack_rate: Base attack probability
        p_stay: Probability of staying in same state
    """
    def __init__(self, attack_rate=0.25, p_stay=0.7):
        super().__init__(attack_rate)
        self.p_stay = p_stay
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        mask = np.ones((frame_length, num_paths), dtype=int)
        
        for path in range(num_paths):
            is_attacked = rng.random() < self.attack_rate
            
            for t in range(frame_length):
                if rng.random() < self.p_stay:
                    # Stay in current state
                    pass
                else:
                    # Transition
                    is_attacked = not is_attacked
                
                mask[t, path] = 0 if is_attacked else 1
        
        return mask


# ============================================================================
# ADAPTIVE ATTACK
# ============================================================================

class AdaptiveAttack(AttackStrategy):
    """
    Adaptive attack that targets frequently selected paths.
    
    Args:
        attack_rate: Base attack probability
        adaptation_window: Window size for tracking selections
        adaptation_strength: How strongly to adapt (0-1)
    """
    def __init__(self, attack_rate=0.25, adaptation_window=100, adaptation_strength=0.5):
        super().__init__(attack_rate)
        self.adaptation_window = adaptation_window
        self.adaptation_strength = adaptation_strength
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        if selection_trace is None:
            # Fallback to random if no trace provided
            return RandomAttack(self.attack_rate).generate(rng, frame_length, num_paths)
        
        mask = np.ones((frame_length, num_paths), dtype=int)
        
        for t in range(frame_length):
            # Calculate path usage in recent window
            window_start = max(0, t - self.adaptation_window)
            recent_selections = selection_trace[window_start:t]
            
            if len(recent_selections) > 0:
                # Count selections per path
                path_counts = np.bincount(recent_selections, minlength=num_paths)
                path_probs = path_counts / len(recent_selections)
                
                # Adapt attack rates based on usage
                for path in range(num_paths):
                    adapted_rate = self.attack_rate + (self.adaptation_strength * path_probs[path])
                    adapted_rate = min(adapted_rate, 0.9)  # Cap at 90%
                    mask[t, path] = 1 if rng.random() >= adapted_rate else 0
            else:
                # No history yet, use base rate
                mask[t, :] = (rng.random(num_paths) >= self.attack_rate).astype(int)
        
        return mask


# ============================================================================
# ONLINE ADAPTIVE ATTACK
# ============================================================================

class OnlineAdaptiveAttack(AttackStrategy):
    """
    Real-time adaptive attack that responds to immediate selections.
    
    Args:
        attack_rate: Base attack probability
        response_delay: Frames before attack activates
        burst_probability: Probability of burst attack
    """
    def __init__(self, attack_rate=0.25, response_delay=5, burst_probability=0.3):
        super().__init__(attack_rate)
        self.response_delay = response_delay
        self.burst_probability = burst_probability
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        if selection_trace is None:
            return RandomAttack(self.attack_rate).generate(rng, frame_length, num_paths)
        
        mask = np.ones((frame_length, num_paths), dtype=int)
        
        for t in range(frame_length):
            # Check if we should burst attack
            if rng.random() < self.burst_probability:
                # Burst: attack all paths for a short duration
                burst_length = min(10, frame_length - t)
                mask[t:t+burst_length, :] = 0
                continue
            
            # Track recently selected paths
            if t >= self.response_delay:
                recent_window = selection_trace[max(0, t - self.response_delay):t]
                if len(recent_window) > 0:
                    # Attack the most recently used path
                    last_selected = recent_window[-1]
                    mask[t, last_selected] = 0 if rng.random() < (self.attack_rate * 2) else 1
            
            # Base random attack on other paths
            for path in range(num_paths):
                if mask[t, path] == 1:  # Not already attacked
                    mask[t, path] = 1 if rng.random() >= self.attack_rate else 0
        
        return mask


# ============================================================================
# HELPER: Create attack from string
# ============================================================================

def create_attack_strategy(scenario_name, attack_rate=0.25, **kwargs):
    """
    Factory function to create attack strategy from scenario name.
    
    Args:
        scenario_name: Name of scenario ('none', 'stochastic', 'markov', etc.)
        attack_rate: Base attack rate
        **kwargs: Additional parameters for specific strategies
    
    Returns:
        AttackStrategy instance
    """
    scenario_lower = scenario_name.lower()
    
    if scenario_lower == 'none':
        return NoAttack()
    elif scenario_lower == 'stochastic':
        return RandomAttack(attack_rate=attack_rate)
    elif scenario_lower == 'markov':
        return MarkovAttack(attack_rate=attack_rate, **kwargs)
    elif scenario_lower == 'adaptive':
        return AdaptiveAttack(attack_rate=attack_rate, **kwargs)
    elif scenario_lower == 'onlineadaptive':
        return OnlineAdaptiveAttack(attack_rate=attack_rate, **kwargs)
    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")
