"""
Quantum physics models - reusable components for noise, fidelity, rewards.
Extracted from network_environment.py to enable composition.
"""
import numpy as np

# ============================================================================
# NOISE MODELS
# ============================================================================

class QuantumNoiseModel:
    """Base interface for quantum noise models."""
    def get_error_rates(self, path_idx, path_info=None):
        """
        Args:
            path_idx: Index of the path (0-based)
            path_info: Optional dict with path details (hops, distances, etc.)
        Returns:
            List of per-link error rates (e.g., [1.5e-4, 1.5e-4])
        """
        raise NotImplementedError


class DefaultNoiseModel(QuantumNoiseModel):
    """
    CURRENT framework noise model (extracted from _calculate_path_rewards).
    Uses fixed per-path error rates.
    """
    def __init__(self):
        # Extracted from your existing hardcoded values
        self.error_rates = {
            0: [1.5e-4, 1.5e-4],      # Path 1 (2-hop)
            1: [1e-4, 1e-4],          # Path 2 (2-hop)
            2: [2e-4, 2e-4, 2e-4],    # Path 3 (3-hop)
            3: [1e-4, 1e-4, 1e-4],    # Path 4 (3-hop)
        }
    
    def get_error_rates(self, path_idx, path_info=None):
        return self.error_rates.get(path_idx, [1e-4] * 3)


class FiberLossNoiseModel(QuantumNoiseModel):
    """
    Paper #2 (Chaudhary ICC 2023) FiberLoss.m logic.
    Computes error rates from physical topology.
    """
    def __init__(self, topology, paths, p_init=0.00001, f_attenuation=0.05):
        """
        Args:
            topology: NetworkX graph with 'distance' edge attributes
            paths: List of paths (each path = list of node indices)
            p_init: Initial entanglement loss probability
            f_attenuation: Fiber attenuation coefficient (dB/km)
        """
        self.topology = topology
        self.paths = paths
        self.p_init = p_init
        self.f_attenuation = f_attenuation
    
    def get_error_rates(self, path_idx, path_info=None):
        """Compute per-link error rates from topology distances."""
        path = self.paths[path_idx]
        error_rates = []
        
        for i in range(len(path) - 1):
            distance = self.topology[path[i]][path[i+1]]['distance']
            # FiberLoss.m formula
            loss_prob = 1 - (1 - self.p_init) * (10 ** (-self.f_attenuation * distance / 10))
            error_rates.append(loss_prob)
        
        return error_rates


# ============================================================================
# FIDELITY CALCULATORS
# ============================================================================

class FidelityCalculator:
    """Base interface for fidelity calculation."""
    def compute_path_fidelity(self, error_rates, context, success_factor):
        """
        Args:
            error_rates: Per-link error rates
            context: Qubit allocation (e.g., [3, 5])
            success_factor: A parameter
        Returns:
            Fidelity (success probability)
        """
        raise NotImplementedError


class DefaultFidelityCalculator(FidelityCalculator):
    """
    CURRENT framework fidelity (extracted from _calculate_path_rewards).
    Per-link success probabilities multiplied across hops.
    """
    def compute_path_fidelity(self, error_rates, context, success_factor):
        """
        Current logic:
        p(pe) = 1 - (1 - pe)^A
        fidelity = product over links: (1 - (1 - p_link)^qubits_link)
        """
        A = success_factor
        
        # Convert error rates to per-link success probs
        link_probs = [1 - (1 - pe) ** A for pe in error_rates]
        
        # Compose across hops
        fidelity = 1.0
        for i, p_link in enumerate(link_probs):
            qubits_on_link = context[i]
            link_success = 1 - (1 - p_link) ** qubits_on_link
            fidelity *= link_success
        
        return fidelity


class CascadedFidelityCalculator(FidelityCalculator):
    """
    Paper #2 CascadedFidelity.m logic.
    Simple multiplicative cascading (ignores qubit allocation).
    """
    def compute_path_fidelity(self, error_rates, context, success_factor):
        """
        Cascaded fidelity = product of (1 - error_rate) for each link.
        """
        fidelity = 1.0
        for error_rate in error_rates:
            fidelity *= (1 - error_rate)
        
        return max(0.0, min(1.0, fidelity))


# ============================================================================
# REWARD FUNCTIONS
# ============================================================================

class RewardFunction:
    """Base interface for reward shaping."""
    def compute_reward(self, fidelity):
        raise NotImplementedError


class Paper2RewardFunction(RewardFunction):
    """
    Paper #2 Environment_QCNetwork.m reward function.
    Piecewise fidelity-based rewards.
    """
    def compute_reward(self, fidelity):
        if fidelity < 0.25:
            return -2 * (0.5 - fidelity)
        elif fidelity < 0.5:
            return -1 * (0.5 - fidelity)
        elif fidelity < 0.6:
            return 1 * fidelity
        elif fidelity < 0.7:
            return 2 * fidelity
        elif fidelity < 0.8:
            return 3 * fidelity
        elif fidelity < 0.9:
            return 4 * fidelity
        else:
            return 5 * fidelity
