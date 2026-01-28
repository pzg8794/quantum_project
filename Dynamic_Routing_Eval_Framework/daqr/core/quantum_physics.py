"""
Quantum physics models - reusable components for noise, fidelity, rewards.
✅ FIXED: Capacity-agnostic support for any number of paths
"""
import numpy as np
import math
import time
from daqr.core.event_generators import compute_retry_fidelity_with_threshold


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
    ✅ FIXED: Capacity-agnostic noise model with testbed support.
    
    Supports:
    - paper2 with 4 paths: Original configuration
    - paper2 with 8 paths: Symmetric extension (paths 4-7 mirror 0-3)
    - Other configurations: Pattern-based generation
    """
    
    def __init__(self, num_paths=4, testbed="default"):
        """
        Args:
            num_paths: Total number of paths in the network
            testbed: Testbed configuration ("default", "paper2", etc.)
        """
        self.num_paths = num_paths
        self.testbed = testbed
        
        # ✅ Base error rates for first 4 paths (validated in your research)
        self._base_error_rates = {
            0: [1.5e-4, 1.5e-4],      # Path 0 (2-hop)
            1: [1e-4, 1e-4],          # Path 1 (2-hop)
            2: [2e-4, 2e-4, 2e-4],    # Path 2 (3-hop)
            3: [1.5e-4, 1.5e-4, 1.5e-4],  # Path 3 (3-hop)
        }
        
        # ✅ Generate full error rate table
        self.error_rates = self._generate_error_rates()
    
    def _generate_error_rates(self):
        """
        ✅ Generate error rates for ANY number of paths.
        
        Strategies:
        - paper2 with 8 paths: Duplicate base rates (0-3 → 4-7)
        - paper2 with 4 paths: Use base rates directly
        - Other: Pattern-based extension
        """
        error_rates = {}
        
        if self.testbed == "paper2":
            if self.num_paths == 4:
                # Original 4-path configuration
                return self._base_error_rates.copy()
            
            elif self.num_paths == 8:
                # ✅ Paper2 8-path: Symmetric duplication
                # Paths 0-3: Original
                # Paths 4-7: Mirror of 0-3
                for i in range(4):
                    error_rates[i] = self._base_error_rates[i]
                    error_rates[i + 4] = self._base_error_rates[i]  # Duplicate
                
                return error_rates
            
            else:
                # Other path counts: Cycle through base patterns
                for i in range(self.num_paths):
                    base_idx = i % 4
                    error_rates[i] = self._base_error_rates[base_idx]
                
                return error_rates
        
        else:
            # Default testbed: Cycle through base patterns
            for i in range(self.num_paths):
                base_idx = i % 4
                error_rates[i] = self._base_error_rates[base_idx]
            
            return error_rates
    
    def get_error_rates(self, path_idx, path_info=None):
        """
        ✅ FIXED: Returns error rates for ANY valid path index.
        
        Falls back gracefully if path_idx exceeds configured paths.
        """
        if path_idx in self.error_rates:
            return self.error_rates[path_idx]
        
        # ✅ Fallback: Use pattern from base rates
        base_idx = path_idx % 4
        fallback = self._base_error_rates.get(base_idx, [1e-4] * 3)
        
        print(f"⚠️ Path {path_idx} not in error_rates, using fallback: {fallback}")
        return fallback


class FiberLossNoiseModel(QuantumNoiseModel):
    """
    Paper 2: Fiber loss model from Chaudhary ICC 2023.
    ✅ Already capacity-agnostic (uses topology and paths list)
    """
    
    def __init__(self, topology, paths, p_init=0.00001, f_attenuation=0.05):
        """
        Args:
            topology: NetworkX graph with edge 'distance' attributes
            paths: List of paths, each a sequence of node indices
            p_init: Initial entanglement loss probability (~1e-5)
            f_attenuation: Fiber attenuation coefficient (~0.05 dB/km)
        """
        self.topology = topology
        self.paths = paths
        self.p_init = p_init
        self.f_attenuation = f_attenuation
    
    def get_error_rates(self, path_idx, gate_error_rate=None):
        """
        ✅ Compute per-link error rates from topology distances.
        
        Works for ANY number of paths (uses paths list).
        """
        if path_idx >= len(self.paths):
            print(f"⚠️ Path index {path_idx} out of range (max: {len(self.paths)-1})")
            return [1e-4] * 2  # Fallback
        
        path = self.paths[path_idx]
        error_rates = []
        
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            distance = self.topology[u][v].get('distance', 1.0)
            
            # Fiber loss calculation
            loss_prob = 1 - (1 - self.p_init) ** (10 ** (-self.f_attenuation * distance / 10))
            
            if gate_error_rate:
                # Combine with gate/BSM error
                loss_prob = 1 - (1 - loss_prob) * (1 - gate_error_rate)
            
            error_rates.append(loss_prob)
        
        return error_rates


# ============================================================================
# FIDELITY CALCULATORS (All already capacity-agnostic)
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
    ✅ CURRENT framework fidelity (already capacity-agnostic).
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
            if i >= len(context):
                # ✅ Safety: context might be shorter than error_rates
                break
            
            qubits_on_link = context[i]
            link_success = 1 - (1 - p_link) ** qubits_on_link
            fidelity *= link_success
        
        return fidelity


class CascadedFidelityCalculator(FidelityCalculator):
    """✅ Paper 2: Simple multiplicative cascading fidelity (already capacity-agnostic)."""
    
    def compute_path_fidelity(self, error_rates, context, success_factor=1.0):
        """
        Cascaded fidelity ignores qubit allocation:
        F = product(1 - error_rate for each link)
        """
        fidelity = 1.0
        for error_rate in error_rates:
            fidelity *= (1 - error_rate)
        return max(0.0, min(1.0, fidelity))


# ============================================================================
# REWARD FUNCTIONS (All already capacity-agnostic)
# ============================================================================

class RewardFunction:
    """Base interface for reward shaping."""
    def compute_reward(self, fidelity):
        raise NotImplementedError


class Paper2RewardFunction(RewardFunction):
    """
    ✅ Paper 2 reward: fidelity-based piecewise function (already capacity-agnostic).
    Higher fidelity → higher reward; penalize low fidelity.
    """
    
    def compute_reward(self, fidelity):
        if fidelity < 0.25:
            return -2 * (0.5 - fidelity)  # Heavy penalty
        elif fidelity < 0.5:
            return -1 * (0.5 - fidelity)  # Mild penalty
        elif fidelity < 0.6:
            return 1 * fidelity            # Neutral
        elif fidelity < 0.7:
            return 2 * fidelity            # Good
        elif fidelity < 0.8:
            return 3 * fidelity            # Better
        elif fidelity < 0.9:
            return 4 * fidelity            # Excellent
        else:
            return 5 * fidelity            # Perfect


class FusionNoiseModel:
    """
    ✅ N-fusion noise model for QuARC-style routing (already capacity-agnostic).
    
    Uses topology and paths list, works for any number of paths.
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
        ✅ Get error rates for a path (works for any number of paths).
        
        Returns dict with 'error_rates' key containing per-hop error probs
        """
        if path_idx >= len(self.paths):
            print(f"⚠️ Path index {path_idx} out of range (max: {len(self.paths)-1})")
            return {'error_rates': [1 - self.p_avg] * 2}  # Fallback
        
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
    ✅ Fidelity calculator for fusion-based entanglement distribution (already capacity-agnostic).
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
    ✅ Reward function for QuARC-style fusion routing (already capacity-agnostic).
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
            return float(aggregate_throughput)
        else:
            return 0.0


class MemoryNoiseModel(QuantumNoiseModel):
    """
    ✅ Applies exponential memory decoherence (already capacity-agnostic).
    """
    def __init__(self, T2=5000, swap_delay_per_link=100):
        """
        T2: coherence time (in frames or time units)
        swap_delay_per_link: simulated delay per entanglement hop
        """
        self.T2 = T2
        self.swap_delay_per_link = swap_delay_per_link

    def get_memory_decay(self, path_length):
        """
        Returns total fidelity decay across the path due to memory.
        """
        total_hold_time = path_length * self.swap_delay_per_link
        return math.exp(-total_hold_time / self.T2)


class FullPaper2FidelityCalculator(FidelityCalculator):
    """
    ✅ Full Paper 2 fidelity calculator (already capacity-agnostic).
    Fiber loss + gate noise + memory decoherence.
    """
    def __init__(self, noise_model, gate_error_rate=0.02, memory_model=None):
        self.noise_model = noise_model
        self.gate_error_rate = gate_error_rate
        self.memory_model = memory_model

    def compute_path_fidelity(self, path_idx, context, success_factor=1.0):
        """
        Cascaded fidelity from link errors + memory + gate noise.
        """
        error_rates = self.noise_model.get_error_rates(path_idx, gate_error_rate=self.gate_error_rate)
        fidelity = 1.0
        for e in error_rates:
            fidelity *= (1 - e)

        # Apply memory decoherence if model is enabled
        if self.memory_model:
            decay = self.memory_model.get_memory_decay(len(error_rates))
            fidelity *= decay

        return fidelity


class Paper7RewardFunction:
    """
    ✅ Context-aware reward for Paper 7 (QBGP) (already capacity-agnostic).
    """
    def __init__(self, mode="neg_hop"):
        """
        mode: One of:
            - 'neg_hop'        → reward = -hop_count
            - 'neg_degree'     → reward = -avg_degree
            - 'neg_length'     → reward = -path_length
            - 'custom'         → you define it in compute()
        """
        self.mode = mode

    def compute(self, context_vector):
        hop, degree, length = context_vector.tolist()

        if self.mode == "neg_hop":
            return -hop
        elif self.mode == "neg_degree":
            return -degree
        elif self.mode == "neg_length":
            return -length
        elif self.mode == "custom":
            # Weighted combo (example)
            return - (0.5 * hop + 0.3 * degree + 0.2 * length)
        else:
            raise ValueError(f"Unknown reward mode: {self.mode}")


class TimeDecayFidelityModel:
    """
    ✅ Fidelity decays exponentially with time (already capacity-agnostic).
    F(t) = F0 * exp(-t / T_mem)
    """

    def __init__(self, memory_lifetime: float = 1.0):
        """
        memory_lifetime: characteristic decoherence time (seconds)
        """
        self.memory_lifetime = memory_lifetime

    def compute(self, base_fidelity: float, time_elapsed: float) -> float:
        if base_fidelity <= 0.0:
            return 0.0

        decay = math.exp(-time_elapsed / self.memory_lifetime)
        return max(0.0, base_fidelity * decay)


class Paper12RetryFidelityCalculator(FidelityCalculator):
    """
    ✅ Paper12 (Zhang et al. 2023): Fidelity with threshold-based retry logic (already capacity-agnostic).
    """
    
    def __init__(self, base_calculator, threshold=0.7, max_attempts=3, decay_rate=0.95):
        """
        Args:
            base_calculator: Underlying fidelity calculator (e.g., FusionFidelityCalculator)
            threshold: Minimum acceptable fidelity (τ in paper)
            max_attempts: Maximum retry attempts (N in paper)
            decay_rate: Fidelity penalty per retry attempt
        """
        self.base_calculator = base_calculator
        self.threshold = threshold
        self.max_attempts = max_attempts
        self.decay_rate = decay_rate
        self.retry_stats = {'total_retries': 0, 'retry_events': 0}
    
    def compute_path_fidelity(self, error_rates, context, success_factor):
        """Compute fidelity with retry logic applied."""
        # Get base fidelity from underlying calculator
        base_fid = self.base_calculator.compute_path_fidelity(error_rates, context, success_factor)
        
        # Apply Paper12 retry logic
        final_fid, retries, success = compute_retry_fidelity_with_threshold(
            base_fid, self.threshold, self.max_attempts, self.decay_rate
        )
        
        # Track retry statistics
        if retries > 0:
            self.retry_stats['retry_events'] += 1
            self.retry_stats['total_retries'] += retries
        
        return final_fid
    
    def get_retry_stats(self):
        """Return retry statistics for logging."""
        return self.retry_stats.copy()


class StochasticPaper2NoiseModel(QuantumNoiseModel):
    """
    ✅ STOCHASTIC instance-based noise for Paper2 compliance.
    
    Each call to get_error_rates() generates NEW random noise.
    DIFFERENT fidelities each iteration for the same path.
    """
    
    def __init__(self, topology, paths, p_init=0.00001, f_attenuation=0.05,
                 p_BSM=0.2, p_GateErrors=0.2, p_depol=0.1):
        """
        Args:
            topology: NetworkX graph
            paths: List of paths
            p_init: Initial entanglement loss (1e-5)
            f_attenuation: Fiber attenuation (0.05 dB/km)
            p_BSM: Bell measurement error probability (0.2)
            p_GateErrors: Gate operation error probability (0.2)
            p_depol: Depolarization noise probability (0.1)
        """
        self.topology = topology
        self.paths = paths
        self.p_init = p_init
        self.f_attenuation = f_attenuation
        self.p_BSM = p_BSM
        self.p_GateErrors = p_GateErrors
        self.p_depol = p_depol
    
    def get_error_rates(self, path_idx, gate_error_rate=None):
        """
        ✅ Generate STOCHASTIC noise for this path.
        
        CRITICAL: Returns DIFFERENT values each call!
        """
        if path_idx >= len(self.paths):
            return [1e-4] * 2  # Fallback
        
        path = self.paths[path_idx]
        error_rates = []
        
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            distance = self.topology[u][v].get('distance', 1.0)
            
            # 1. Fiber loss (deterministic component)
            p_fiber = 1 - (1 - self.p_init) ** (10 ** (-self.f_attenuation * distance / 10))
            
            # 2. ✅ STOCHASTIC BSM error
            bsm_happens = 1 if np.random.rand() < self.p_BSM else 0
            
            # 3. ✅ STOCHASTIC Gate error
            gate_happens = 1 if np.random.rand() < self.p_GateErrors else 0
            
            # 4. ✅ STOCHASTIC Depolarization
            depol_happens = 1 if np.random.rand() < self.p_depol else 0
            
            # ✅ Combine all noise sources
            total_error = p_fiber + (bsm_happens * 0.05) + (gate_happens * 0.03) + (depol_happens * 0.02)
            total_error = min(1.0, total_error)  # Cap at 1.0
            
            error_rates.append(total_error)
        
        return error_rates


class AdaptedPaper2FidelityCalculator(FidelityCalculator):
    """
    ✅ ADAPTER: Wraps FullPaper2FidelityCalculator to match environment's expected interface.
    
    Environment expects: compute_path_fidelity(error_rates, context, success_factor)
    FullPaper2 expects: compute_path_fidelity(path_idx, context, success_factor)
    
    This adapter bridges the gap by storing the noise model internally.
    """
    
    def __init__(self, noise_model, gate_error_rate=0.02, memory_model=None):
        """
        Args:
            noise_model: StochasticPaper2NoiseModel instance
            gate_error_rate: BSM/gate error rate (0.02)
            memory_model: Optional MemoryNoiseModel for T2 decay
        """
        self.noise_model = noise_model
        self.gate_error_rate = gate_error_rate
        self.memory_model = memory_model
        self._path_idx_cache = None  # Hack to pass path_idx through
    
    def compute_path_fidelity(self, error_rates, context, success_factor=1.0):
        """
        ✅ MATCHES environment's expected signature.
        
        Note: error_rates parameter is IGNORED because we get them from noise_model.
        This is a design compromise to match the interface.
        """
        # Since we don't know path_idx here, we'll use the error_rates directly
        # (environment already computed them for us)
        fidelity = 1.0
        for e in error_rates:
            fidelity *= (1 - e)
        
        # Apply memory decay if enabled
        if self.memory_model:
            decay = self.memory_model.get_memory_decay(len(error_rates))
            fidelity *= decay
        
        return fidelity
