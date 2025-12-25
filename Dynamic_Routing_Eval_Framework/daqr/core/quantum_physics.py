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

class FusionNoiseModel:
    """
    N-fusion noise model for QuARC-style routing
    
    In fusion-based protocols, n qubits undergo n-fusion with success prob q^n.
    This differs from swapping where 2-qubit operations have success prob q.
    """
    
    def __init__(self, topology, paths, fusion_prob=0.9, entanglement_prob=0.6):
        """
        Args:
            topology: NetworkX graph
            paths: List of paths (list of node sequences)
            fusion_prob: q (fusion success probability)
            entanglement_prob: p (link generation success probability)
        """
        self.topology = topology
        self.paths = paths
        self.q = fusion_prob
        self.p_avg = entanglement_prob
        
        # Compute per-edge entanglement probs from average
        self._compute_edge_probs()
        
    def _compute_edge_probs(self):
        """Compute per-edge entanglement generation probabilities"""
        self.edge_probs = {}
        
        for u, v in self.topology.edges():
            # Edge-dependent p based on distance
            dist = self.topology[u][v].get('distance', 1.0)
            # Exponential decay: p = p_avg * exp(-alpha * distance)
            alpha = 0.16  # QuARC paper default
            p_edge = self.p_avg * np.exp(-alpha * dist)
            self.edge_probs[(u, v)] = p_edge
            self.edge_probs[(v, u)] = p_edge  # Symmetric
            
    def get_error_rates(self, path_idx):
        """
        Get error rates for a path (for compatibility with your framework)
        
        Returns dict with 'error_rates' key containing per-hop error probs
        """
        if path_idx >= len(self.paths):
            raise IndexError(f"Path index {path_idx} out of range")
        
        path = self.paths[path_idx]
        error_rates = []
        
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            p_link = self.edge_probs.get((u, v), self.p_avg)
            # Error rate = 1 - success rate
            error_rates.append(1 - p_link)
        
        return {'error_rates': error_rates}
    
    def get_fusion_success_prob(self, n_qubits):
        """Get success probability for n-qubit fusion"""
        return self.q ** n_qubits


class FusionFidelityCalculator:
    """
    Fidelity calculator for fusion-based entanglement distribution
    
    Unlike cascaded fidelity (multiplicative), fusion-based protocols
    maintain fidelity through GHZ states and single-qubit corrections.
    """
    
    def compute_path_fidelity(self, error_rates, context, fusion_prob=0.9):
        """
        Compute end-to-end fidelity for fusion-based routing
        
        Args:
            error_rates: Per-hop error rates (from noise model)
            context: Path context (hop count, etc.)
            fusion_prob: q value
            
        Returns:
            fidelity (0-1)
        """
        # For fusion protocols, fidelity depends on:
        # 1. Link generation success across path
        # 2. Fusion success at intermediate nodes
        
        num_hops = len(error_rates['error_rates'])
        
        # Probability all links succeed
        p_links = np.prod([1 - err for err in error_rates['error_rates']])
        
        # Probability all fusions succeed (n-1 fusions for n hops)
        p_fusions = fusion_prob ** (num_hops - 1)
        
        # Combined success probability as fidelity proxy
        fidelity = p_links * p_fusions
        
        return fidelity


class QuARCRewardFunction:
    """
    Reward function for QuARC-style fusion routing
    
    Rewards based on successful entanglement distribution, not fidelity.
    QuARC optimizes throughput (requests/timeslot) over fidelity.
    """
    
    def compute_reward(self, success, aggregate_throughput=1):
        """
        Args:
            success: Boolean, whether entanglement succeeded
            aggregate_throughput: Number of parallel entanglements (if any)
            
        Returns:
            reward (float)
        """
        if success:
            # Reward = 1 for success, can scale by aggregate throughput
            return float(aggregate_throughput)
        else:
            return 0.0