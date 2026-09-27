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
    mask_capability = "undeclared"
    uses_rng = True

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

    def validate_execution(self):
        if self.mask_capability == "static":
            return
        if self.mask_capability not in {"selection_history", "online_selection_history"} or not callable(getattr(self, "availability_at", None)):
            raise ValueError("HOLD: strategy has no supported causal execution interface")

    def open_session(self, rng, frames, routes):
        from daqr.core.scenario_execution import ScenarioSession
        return ScenarioSession(self, rng, frames, routes)

    def __repr__(self):
        env = self.__class__.__name__.replace("Attack", "")
        return env


# ============================================================================
# NO ATTACK
# ============================================================================

class NoAttack(AttackStrategy):
    """✅ No attack - all paths always succeed (capacity-agnostic)."""
    mask_capability = "static"
    uses_rng = False

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
    mask_capability = "static"

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
    mask_capability = "static"

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
    mask_capability = "selection_history"

    def __init__(self, attack_rate: float = 0.25, 
                 adaptation_window: int = 100,
                 adaptation_strength: float = 0.5):
        super().__init__(attack_rate)
        self.adaptation_window = adaptation_window
        if not (0.0 <= adaptation_strength <= 1.0):
            raise ValueError(f"adaptation_strength must be in [0, 1], got {adaptation_strength}")
        self.adaptation_strength = adaptation_strength
    
    def availability_at(self, frame, history, state, rng, num_paths, frames):
        if len(history) != frame:
            raise ValueError("Adaptive strategy requires exact prior selection history")
        recent = history[max(0,frame-self.adaptation_window):frame]
        if not recent:
            return (rng.random(num_paths) >= self.attack_rate).astype(np.int8)
        if min(recent) < 0 or max(recent) >= num_paths:
            raise ValueError("Invalid path index in selection history")
        counts = np.bincount(recent, minlength=num_paths)
        probabilities = counts / len(recent)
        return np.array([int(rng.random() >= min(self.attack_rate + self.adaptation_strength*p, 0.9))
                         for p in probabilities],dtype=np.int8)

    def validate_execution(self):
        super().validate_execution()
        if type(self.adaptation_window) is not int or self.adaptation_window < 1:
            raise ValueError("Positive adaptation window required")

    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        self._validate_inputs(frame_length, num_paths)
        self.validate_execution()
        if selection_trace is None or len(selection_trace) < frame_length:
            raise ValueError("Adaptive strategy requires selection history; no random fallback")
        return np.array([self.availability_at(t,tuple(selection_trace[:t]),{},rng,num_paths,frame_length)
                         for t in range(frame_length)],dtype=np.int8)


# ============================================================================
# ONLINE ADAPTIVE ATTACK
# ============================================================================

class OnlineAdaptiveAttack(AttackStrategy):
    """
    ✅ Real-time adaptive attack (capacity-agnostic).
    
    Responds immediately to path selections with burst attacks.
    """
    mask_capability = "online_selection_history"

    def __init__(self, attack_rate: float = 0.25, 
                 response_delay: int = 5,
                 burst_probability: float = 0.3):
        super().__init__(attack_rate)
        self.response_delay = response_delay
        if not (0.0 <= burst_probability <= 1.0):
            raise ValueError(f"burst_probability must be in [0, 1], got {burst_probability}")
        self.burst_probability = burst_probability
    
    def availability_at(self, frame, history, state, rng, num_paths, frames):
        if len(history) != frame:
            raise ValueError("Online strategy requires exact prior selection history")
        # Preserve the existing algorithm exactly, including its burst carry-over:
        # a later targeted-path assignment can overwrite a pending burst zero.
        row = np.full(num_paths, int(frame >= state.get("burst_until",0)), dtype=np.int8)
        if rng.random() < self.burst_probability:
            state["burst_until"] = min(frame+10,frames)
            return np.zeros(num_paths,dtype=np.int8)
        if frame >= self.response_delay:
            recent = history[max(0,frame-self.response_delay):frame]
            if recent:
                selected = recent[-1]
                if selected < 0 or selected >= num_paths:
                    raise ValueError("Invalid path index in selection history")
                row[selected] = 0 if rng.random() < self.attack_rate*2 else 1
        for path in range(num_paths):
            if row[path] == 1:
                row[path] = 1 if rng.random() >= self.attack_rate else 0
        return row

    def validate_execution(self):
        super().validate_execution()
        if type(self.response_delay) is not int or self.response_delay < 1:
            raise ValueError("Positive response delay required for causal online execution")

    def generate(self, rng, frame_length, num_paths, selection_trace=None):
        self._validate_inputs(frame_length, num_paths)
        self.validate_execution()
        if selection_trace is None or len(selection_trace) < frame_length:
            raise ValueError("Online strategy requires selection history; no random fallback")
        state = {}
        return np.array([self.availability_at(t,tuple(selection_trace[:t]),state,rng,num_paths,frame_length)
                         for t in range(frame_length)],dtype=np.int8)


# ============================================================================
# HELPER: Create attack from string
# ============================================================================

STRATEGY_REGISTRY = {
    "none": NoAttack, "random": RandomAttack, "stochastic": RandomAttack,
    "markov": MarkovAttack, "adaptive": AdaptiveAttack, "onlineadaptive": OnlineAdaptiveAttack,
}


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
    if scenario_lower not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    cls = STRATEGY_REGISTRY[scenario_lower]
    # The existing factory's no-attack call takes no rate argument.
    parameters = {} if cls is NoAttack else {"attack_rate": attack_rate, **kwargs}
    return cls(**parameters)
