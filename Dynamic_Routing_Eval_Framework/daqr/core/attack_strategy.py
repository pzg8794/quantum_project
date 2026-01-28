"""
Attack strategies for quantum network adversarial scenarios.

CAPACITY-AGNOSTIC DESIGN:
------------------------
All attack strategies work with ANY number of paths (num_paths parameter).
No hardcoded path counts anywhere - supports 4, 8, 12, or more paths.

Extracted from network_environment.py for better separation of concerns.
"""
import numpy as np
from typing import Optional


# ============================================================================
# BASE ATTACK STRATEGY
# ============================================================================

class AttackStrategy:
    """
    ✅ Base class for attack strategies (capacity-agnostic).
    
    All subclasses generate attack masks for arbitrary num_paths values.
    """
    def __init__(self, attack_rate: float = 0.25):
        if not (0.0 <= attack_rate <= 1.0):
            raise ValueError(f"attack_rate must be in [0, 1], got {attack_rate}")
        self.attack_rate = attack_rate
    
    def generate(self, 
                 rng: np.random.Generator, 
                 frame_length: int, 
                 num_paths: int,
                 selection_trace: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Generate attack mask for ANY number of paths.
        
        Args:
            rng: NumPy random generator
            frame_length: Number of time frames
            num_paths: Number of paths (works with 4, 8, 12, etc.)
            selection_trace: Optional trace of path selections [T]
        
        Returns:
            Binary mask (frame_length × num_paths): 1 = success, 0 = attacked
        """
        self._validate_inputs(frame_length, num_paths)
        raise NotImplementedError
    
    def _validate_inputs(self, frame_length: int, num_paths: int):
        """Validate inputs to prevent common errors."""
        if frame_length <= 0:
            raise ValueError(f"frame_length must be > 0, got {frame_length}")
        
        if num_paths <= 0:
            raise ValueError(f"num_paths must be > 0, got {num_paths}")

    def __repr__(self):
        env = self.__class__.__name__.replace("Attack", "")
        return env


# ============================================================================
# NO ATTACK
# ============================================================================

class NoAttack(AttackStrategy):
    """✅ No attack - all paths always succeed (capacity-agnostic)."""
    def __init__(self):
        super().__init__(attack_rate=0.0)
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        self._validate_inputs(frame_length, num_paths)
        return np.ones((frame_length, num_paths), dtype=np.int8)


# ============================================================================
# RANDOM ATTACK (ENHANCED)
# ============================================================================

class RandomAttack(AttackStrategy):
    """
    ✅ Random attack with optional path-dependent rates (capacity-agnostic).
    
    Args:
        attack_rate: Global attack rate (used if per_path_rates is None)
        per_path_rates: Optional array of per-path attack rates [p1, p2, ...]
                       Must match num_paths in generate()
    """
    def __init__(self, attack_rate: float = 0.25, 
                 per_path_rates: Optional[np.ndarray] = None):
        super().__init__(attack_rate)
        self.per_path_rates = per_path_rates
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        self._validate_inputs(frame_length, num_paths)
        
        if self.per_path_rates is not None:
            # ✅ Validate per_path_rates length
            if len(self.per_path_rates) != num_paths:
                raise ValueError(
                    f"per_path_rates length {len(self.per_path_rates)} != "
                    f"num_paths {num_paths}"
                )
            
            # Path-dependent noise
            mask = np.ones((frame_length, num_paths), dtype=np.int8)
            for p in range(num_paths):
                rate = self.per_path_rates[p]
                mask[:, p] = (rng.random(frame_length) >= rate).astype(np.int8)
            return mask
        else:
            # Global rate
            mask = rng.random((frame_length, num_paths)) >= self.attack_rate
            return mask.astype(np.int8)


# ============================================================================
# MARKOV ATTACK
# ============================================================================

class MarkovAttack(AttackStrategy):
    """
    ✅ Markov-based attack with state transitions (capacity-agnostic).
    
    Works independently on each path, scales to any num_paths.
    """
    def __init__(self, attack_rate: float = 0.25, p_stay: float = 0.7):
        super().__init__(attack_rate)
        if not (0.0 <= p_stay <= 1.0):
            raise ValueError(f"p_stay must be in [0, 1], got {p_stay}")
        self.p_stay = p_stay
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        self._validate_inputs(frame_length, num_paths)
        
        mask = np.ones((frame_length, num_paths), dtype=np.int8)
        
        for path in range(num_paths):
            is_attacked = rng.random() < self.attack_rate
            
            for t in range(frame_length):
                if rng.random() < self.p_stay:
                    pass  # Stay in current state
                else:
                    is_attacked = not is_attacked
                
                mask[t, path] = 0 if is_attacked else 1
        
        return mask


# ============================================================================
# ADAPTIVE ATTACK
# ============================================================================

class AdaptiveAttack(AttackStrategy):
    """
    ✅ Adaptive attack that targets frequently selected paths (capacity-agnostic).
    
    Tracks path selection frequency and increases attack rates accordingly.
    """
    def __init__(self, attack_rate: float = 0.25, 
                 adaptation_window: int = 100,
                 adaptation_strength: float = 0.5):
        super().__init__(attack_rate)
        self.adaptation_window = adaptation_window
        if not (0.0 <= adaptation_strength <= 1.0):
            raise ValueError(f"adaptation_strength must be in [0, 1], got {adaptation_strength}")
        self.adaptation_strength = adaptation_strength
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        self._validate_inputs(frame_length, num_paths)
        
        if selection_trace is None:
            return RandomAttack(self.attack_rate).generate(rng, frame_length, num_paths)
        
        # ✅ Validate selection_trace
        if len(selection_trace) < frame_length:
            raise ValueError(
                f"selection_trace length {len(selection_trace)} < frame_length {frame_length}"
            )
        
        mask = np.ones((frame_length, num_paths), dtype=np.int8)
        
        for t in range(frame_length):
            window_start = max(0, t - self.adaptation_window)
            recent_selections = selection_trace[window_start:t]
            
            if len(recent_selections) > 0:
                # ✅ Validate path indices
                max_idx = np.max(recent_selections)
                min_idx = np.min(recent_selections)
                if max_idx >= num_paths or min_idx < 0:
                    raise ValueError(
                        f"Invalid path index in selection_trace: "
                        f"range [{min_idx}, {max_idx}], must be in [0, {num_paths})"
                    )
                
                # Count selections per path
                path_counts = np.bincount(recent_selections, minlength=num_paths)
                path_probs = path_counts / len(recent_selections)
                
                # Adapt attack rates
                for path in range(num_paths):
                    adapted_rate = self.attack_rate + (self.adaptation_strength * path_probs[path])
                    adapted_rate = min(adapted_rate, 0.9)
                    mask[t, path] = 1 if rng.random() >= adapted_rate else 0
            else:
                # No history yet
                mask[t, :] = (rng.random(num_paths) >= self.attack_rate).astype(np.int8)
        
        return mask


# ============================================================================
# ONLINE ADAPTIVE ATTACK
# ============================================================================

class OnlineAdaptiveAttack(AttackStrategy):
    """
    ✅ Real-time adaptive attack (capacity-agnostic).
    
    Responds immediately to path selections with burst attacks.
    """
    def __init__(self, attack_rate: float = 0.25, 
                 response_delay: int = 5,
                 burst_probability: float = 0.3):
        super().__init__(attack_rate)
        self.response_delay = response_delay
        if not (0.0 <= burst_probability <= 1.0):
            raise ValueError(f"burst_probability must be in [0, 1], got {burst_probability}")
        self.burst_probability = burst_probability
    
    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        self._validate_inputs(frame_length, num_paths)
        
        if selection_trace is None:
            return RandomAttack(self.attack_rate).generate(rng, frame_length, num_paths)
        
        mask = np.ones((frame_length, num_paths), dtype=np.int8)
        
        for t in range(frame_length):
            # Burst attack
            if rng.random() < self.burst_probability:
                burst_length = min(10, frame_length - t)
                mask[t:t+burst_length, :] = 0
                continue
            
            # Track recently selected paths
            if t >= self.response_delay:
                recent_window = selection_trace[max(0, t - self.response_delay):t]
                if len(recent_window) > 0:
                    last_selected = recent_window[-1]
                    
                    # ✅ Validate path index
                    if last_selected >= num_paths or last_selected < 0:
                        raise ValueError(
                            f"Invalid path index {last_selected} in selection_trace "
                            f"(must be in [0, {num_paths}))"
                        )
                    
                    # Attack most recently used path
                    mask[t, last_selected] = 0 if rng.random() < (self.attack_rate * 2) else 1
            
            # Base random attack on other paths
            for path in range(num_paths):
                if mask[t, path] == 1:
                    mask[t, path] = 1 if rng.random() >= self.attack_rate else 0
        
        return mask


# ============================================================================
# HELPER: Create attack from string
# ============================================================================

def create_attack_strategy(scenario_name: str, 
                          attack_rate: float = 0.25, 
                          **kwargs) -> AttackStrategy:
    """
    ✅ Factory function to create attack strategy (capacity-agnostic).
    
    All strategies work with any num_paths value.
    
    Args:
        scenario_name: 'none', 'stochastic', 'markov', 'adaptive', 'onlineadaptive'
        attack_rate: Base attack rate
        **kwargs: Additional parameters for specific strategies
    
    Returns:
        AttackStrategy instance that works with any num_paths
    """
    scenario_lower = scenario_name.lower()
    
    if scenario_lower == 'none':
        return NoAttack()
    elif scenario_lower == 'stochastic':
        return RandomAttack(attack_rate=attack_rate, **kwargs)
    elif scenario_lower == 'markov':
        return MarkovAttack(attack_rate=attack_rate, **kwargs)
    elif scenario_lower == 'adaptive':
        return AdaptiveAttack(attack_rate=attack_rate, **kwargs)
    elif scenario_lower == 'onlineadaptive':
        return OnlineAdaptiveAttack(attack_rate=attack_rate, **kwargs)
    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")
