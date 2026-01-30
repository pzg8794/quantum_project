from datetime import datetime
import os
import math
import json
import time
import copy
import psutil
import random, re
import warnings, gc
import numpy as np
import pandas as pd
from tqdm import tqdm
import seaborn as sns
from random import choice
import matplotlib.pyplot as plt
from abc import ABC, abstractmethod
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import pickle, traceback
from pathlib import Path
from scipy.stats import beta, multivariate_normal, norm

import pmdarima as pm  # Real ARIMA dependency
# from quantum_config import QuantumExperimentConfig

# Core Scientific Computing Libraries
warnings.filterwarnings('ignore')

# Set Style for PhD-Quality Plots
sns.set_palette("husl")
plt.style.use('seaborn-v0_8')
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['legend.fontsize'] = 12
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12
plt.rcParams['figure.figsize'] = (12, 8)

# Set Random Seeds for Reproducibility
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)

# Device Configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"PyTorch version: {torch.__version__}")
print(f"NumPy version: {np.__version__}")
print(f"Using device: {device}")

# =============================================================================
# Enhanced Common Interface for All Models
# =============================================================================

class QuantumModel(ABC):
    """
    Enhanced minimal interface that every model (policy/algorithm) in the quantum environment obeys.
    Keep methods generic so both 'step-wise' (Oracle) and 'batch' (EXPNeuralUCB) fit.
    """
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list=[], capacity=10000, mode='base', beta=0.2, gamma_factor=0.01, eta_factor=0.05, lamb=1, n_experts=4):
        super().__init__()

        # Directory structure setup
        self.resumed = False
        self.id = str(self)
        self.configs = configs
        self.is_complete = False
        self.overwrite = self.configs.overwrite
        self.alg_dir = os.path.dirname(os.path.abspath(__file__))

        self.transition_trigger = getattr(self.configs, 'transition_trigger', None)
        self.transition_interval = getattr(self.configs, 'transition_interval', 50)
        
        # Core parameters (shared across all modes)
        self.X_n = X_n
        self.attack_list = attack_list
        self.reward_list = reward_list
        self.frame_number = frame_number
        self.num_groups = len(reward_list)

        self.mode = self.configs.algorithm_configs[str(self)]['kwargs']['mode']
        self.beta = beta
        # print(self, " ", self.mode)
        # self.verbose = self.configs.verbose
        
        # EXP3 parameters (used in 'hybrid' and 'exp3' modes)
        self.capacity = int(capacity*self.configs.scale)
        self.gamma = gamma_factor
        self.eta = eta_factor
        self.state = 0

        self.component   = "model_state"
        self.key_attrs   = getattr(self.configs, "get_key_attrs", lambda: {})()
        self.save_to_dir = Path(f"{self.configs.dir}/model_state/{self.configs.day_str}/")

        mode              = self.configs.backup_mgr.mode
        component_path    = self.configs.backup_mgr.quantum_data_paths["obj"][self.component][mode]
        self.save_to_dir  = component_path / self.configs.day_str

        frame_no_str      = str(int(self.frame_number))
        self.allocator_id = str(getattr(self.configs, "allocator", "alloc"))
        self.env_id       = str(getattr(self.configs, "environment", "env"))
        self.attack_id    = str(getattr(self.configs, "attack_strategy", "None"))
        alloc_str         = " ".join(str(v) for v in self.key_attrs.get("qubit_capacities", []))  # ✅ FIX: Add .get() with default
        if "random" in str(self.configs.allocator).lower(): frame_no_str += f"_({re.sub(r'^_', '', alloc_str)})"
        self.file_name    = f"{self.id}({self.mode})_{int(self.capacity)}-{self.allocator_id}_{self.env_id }_{self.attack_id}-{frame_no_str}.pkl"


        self.thresholds = {
                'EXPNeuralUCB': {'stochastic': 0.628, 'adversarial': 0.598},
                'CPursuitNeuralUCB': {'stochastic': 0.634, 'adversarial': 0.614},
                'GNeuralUCB': {'stochastic': 0.582, 'adversarial': 0.509},  # Added; higher stochastic for grouping
                'iCPursuitNeuralUCB': {'stochastic': 0.712, 'adversarial': 0.689}
            }
        self.path_configs = {0:2, 1:2, 2:3, 3:3, 'lamb':lamb, 'beta':beta}        # Path-specific configs (per path index)

        # Resume previous evaluator state if configured
        # if getattr(self.configs, "resume", False):
        #     try:                    
        #         if self.resume(): self.state = 1
        #     except Exception as e:  print(f"⚠️ Resume failed: {e}")
    
    # def apply_testbed_configs(self):
    #     """
    #     Applies testbed parameters safely:
    #     - Only assign parameters this model already defines.
    #     - Prevents unexpected attributes from breaking other models.
    #     """
    #     # Debug print to confirm testbed application
    #     print(f"\n[TESTBED] Applying testbed params to {self}")
    #     if not hasattr(self.configs, "get_testbed_config"):
    #         return

    #     params = self.configs.get_testbed_config()
    #     current_params = self.configs.algorithm_configs.get(str(self), {})
    #     if not params:
    #         print(f"\n[TESTBED] Applying testbed params to {self}: NO PARAMS")
    #         return

    #     # Debug print to confirm testbed application
    #     print(f"\n[TESTBED] Applying testbed params to {self}: {params}")

    #     for key, value in params.items():
    #         if hasattr(self, key):
    #             print(f"[TESTBED]   • Setting {key} = {value}")   # Debug line
    #             setattr(self, key, value)
    #         else:
    #             print(f"[TESTBED]   • Skipping {key} (model does not define it)")


    def set_id(self, id):
        self.id = id
        return self.set_file_name()

    def set_file_name(self, id=None, mode=None, capacity=None, allocator_id=None, env_id=None, attack_id=None, frame_number=None):
        """
        Generates and sets a standardized file name based on model configuration.
        Allows optional override of any key components.
        Applies smart logic to avoid environment- and attack-specific filenames for reusable models.
        """
        self.id            = id or self.id
        self.mode          = mode or getattr(self, 'mode', None)
        self.capacity      = capacity or self.capacity
        self.allocator_id  = allocator_id or self.allocator_id
        self.env_id        = env_id or self.env_id
        self.attack_id     = attack_id or self.attack_id
        self.frame_number  = frame_number or self.frame_number

        # 🔁 For reusable models (e.g., NeuralUCB), omit both env and attack from the filename
        is_reusable = isinstance(self, NeuralUCB)
        env_suffix    = "" if is_reusable else f"_{self.env_id}"
        attack_suffix = "" if is_reusable else f"_{self.attack_id}"

        self.file_name = f"{self.id}({self.mode})_{self.capacity}-{self.allocator_id}{env_suffix}{attack_suffix}-{self.frame_number}.pkl"
        return True

    def __eq__(self, other):
        """Defines equality for model comparison or saved dict comparison."""
        # --- dict comparison (used in resume) ---
        if isinstance(other, dict):
            other_attrs = other.get("key_attrs", {}).copy()
            # temp fix
            if not self.configs.base_capacity:
                if 'runs' in other_attrs: del other_attrs['runs']
                if 'runs' in self.key_attrs: del self.key_attrs['runs']

            # Check main identifiers
            if (
                self.id == other.get("id") and
                self.frame_number == other.get("frame_number") and
                self.num_groups == other.get("num_groups") and
                self.capacity == other.get("capacity") and
                # getattr(self, 'mode', None) == other.get("mode") and
                self.allocator_id == other.get("allocator_id") and
                self.env_id == other.get("env_id") and
                self.attack_id == other.get("attack_id") and
                self.key_attrs == other_attrs
            ):
                return True
            
            # Debug output if no match
            # print(f"\n❌ Model comparison failed:")
            # print(f"  Class: {self.id} vs {other.get('id')}")
            # print(f"  Frames: {self.frame_number} vs {other.get('frame_number')}")
            # print(f"  Groups: {self.num_groups} vs {other.get('num_groups')}")
            # print(f"  Capacity: {self.capacity} vs {other.get('capacity')}")
            # # print(f"  Mode: {getattr(self, 'mode', None)} vs {other.get('mode')}")
            # print(f"  Allocator: {self.allocator_id} vs {other.get('allocator_id')}")
            # print(f"  Environment: {self.env_id} vs {other.get('env_id')}")
            # print(f"  Attack: {self.attack_id} vs {other.get('attack_id')}")
            # print(f"  Current attrs:\n{json.dumps(self.key_attrs, indent=2)}")
            # print(f"  Loaded attrs:\n{json.dumps(other_attrs, indent=2)}")
            return False

        # --- model instance comparison ---
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.frame_number == getattr(other, "frame_number", None) and
            self.num_groups == getattr(other, "num_groups", None) and
            self.capacity == getattr(other, "capacity", None) and
            getattr(self, 'mode', None) == getattr(other, "mode", None) and
            self.allocator_id == getattr(other, "allocator_id", None) and
            self.env_id == getattr(other, "env_id", None) and
            self.attack_id == getattr(other, "attack_id", None) and
            self.key_attrs == getattr(other, "key_attrs", None)
        )


    
    def save(self):
        # This now always writes to the config backup (safe, never corrupts data lake)
        return self.configs.save_obj(self)

    def resume(self):
        # This now always loads from the correct data lake (or backup if not found)
        if not self.resumed:
            if self.configs.resume_obj(self): self.resumed = True
        return self.resumed

            
    def get_cleanup_wait_time(self, frames_count=1000, cooldown_base=3, cooldown_scale_factor=1, cooldown_max=15):
        """
        Calculate frame-scaled cleanup wait time.
        
        Args:
            frames_count: Number of frames (if None, uses self.frames_count)
        
        Returns:
            float: Wait time in seconds
        """

        # Frame-scaled timing formula
        scale = (frames_count / 1000.0) * cooldown_scale_factor
        wait_time = cooldown_base + scale
        
        return min(wait_time, cooldown_max)
    

    @property
    def model_type(self):
        """Return 'step-wise' or 'batch' to indicate usage pattern"""
        return "step-wise"  # Default for most models
    
    @property
    def supports_batch_execution(self):
        """Return True iff subclass overrides QuantumModel.run"""
        return self.__class__.run is not QuantumModel.run
    
    def reset(self, *args, **kwargs):
        """Optional: clear internal state between runs."""
        pass
    
    @abstractmethod
    def take_action(self, *args, **kwargs):
        """Select an action (signature may vary by model)."""
        raise NotImplementedError
    

    def update(self, *args, **kwargs):
        """Optional: incorporate feedback after an action."""
        pass
    
    def run(self, *args, **kwargs):
        """Optional: batch/episode runner (e.g., EXPNeuralUCB)."""
        raise NotImplementedError(
            f"{self.__class__.__name__} is a '{self.model_type}' model. "
            f"Use take_action() and update() in a loop instead."
        )
    
    def get_results(self) -> dict:
        """Optional: standardized results payload."""
        return {}
    
    
    def get_model_info(self) -> dict:
        """Return comprehensive model metadata"""
        return {
            "name": self.__class__.__name__,
            "model_type": self.model_type,
            "supports_batch_execution": self.supports_batch_execution,
            "has_update": hasattr(self, 'update') and callable(self.update),
            "has_get_results": hasattr(self, 'get_results') and callable(self.get_results),
            "module": self.__class__.__module__
        }
    
    def cleanup(self, verbose=False, cooldown_seconds=1):
        """
        Universal cleanup for all quantum models.
        Handles neural networks, CUDA cache, and large data structures.
        
        Args:
            verbose: If True, print cleanup details
        """
        try:
            cleanup_items = []
            if cooldown_seconds > 0: time.sleep(cooldown_seconds)
            
            # 1. Neural network components (for hybrid models)
            if hasattr(self, 'algorithms'):
                for i, alg in enumerate(self.algorithms):
                    if hasattr(alg, 'neural_net'):
                        del alg.neural_net
                        cleanup_items.append(f"algorithms[{i}].neural_net")
                    if hasattr(alg, 'optimizer'):
                        del alg.optimizer
                        cleanup_items.append(f"algorithms[{i}].optimizer")
            
            # 2. Direct neural components
            for attr in ['neural_net', 'optimizer', 'net']:
                if hasattr(self, attr):
                    delattr(self, attr)
                    cleanup_items.append(attr)
            
            # 3. Neural UCB lists (EXPNeuralUCB variants)
            if hasattr(self, 'neuralucb_list'):
                for i, neural_ucb in enumerate(self.neuralucb_list):
                    if hasattr(neural_ucb, 'net'):
                        del neural_ucb.net
                    if hasattr(neural_ucb, 'optimizer'):
                        del neural_ucb.optimizer
                cleanup_items.append("neuralucb_list")
            
            # 4. Large data structures
            for attr in ['history', 'reward_history', 'action_history', 
                        'context_history', 'prob_list', 'ucb_values']:
                if hasattr(self, attr):
                    delattr(self, attr)
                    cleanup_items.append(attr)
            
            # 5. ARIMA models (for iCMAB models)
            if hasattr(self, 'arima_models'):
                self.arima_models.clear()
                cleanup_items.append("arima_models")
            
            # 6. PyTorch CUDA cleanup
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    cleanup_items.append("CUDA cache")
            except ImportError:
                pass
            
            # 7. Force garbage collection
            collected = gc.collect()
            cleanup_items.append(f"GC:{collected} objects")
            cleanup_items.append(f"cooldown:{cooldown_seconds}s")
            if cooldown_seconds > 0: time.sleep(cooldown_seconds)
            if verbose: print(f"\t✓ {self} cleaned: {', '.join(cleanup_items)}")
        except Exception as e:
            print(f"\t[WARNING] Cleanup for {self} failed: {e}")
            traceback.print_exc()

    def __del__(self):
        """Destructor to ensure cleanup on deletion."""
        try:
            self.cleanup(verbose=False)
        except Exception as e:
            print(f"\tWarning: Cleanup in destructor failed: {e}")

    def __repr__(self):
        env = self.__class__.__name__
        return env if env else "Baseline (None)"


# =============================================================================
# Models & Policies with Enhanced Metadata
# =============================================================================

class Oracle(QuantumModel):
    """
    Oracle algorithm with perfect knowledge of reward functions and attack patterns.
    Always selects the optimal path and allocation given current attack state.
    """
    
    @property
    def model_type(self):
        return 'step-wise'
    
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)
        self.state = -1
        # self.verbose = False
        self.X_n = X_n
        self.reward_list = reward_list
        self.attack_list = attack_list
        self.frame_number = len(attack_list) if attack_list is not None else frame_number
            
        # 🎯 PAPER7 SUPPORT: Detect context-aware rewards
        use_context_aware = getattr(configs, 'use_context_rewards', False)
        # Ensure it's a proper boolean, not a numpy array
        if isinstance(use_context_aware, np.ndarray):
            use_context_aware = bool(use_context_aware.item() if use_context_aware.size == 1 else use_context_aware[0])
        else:
            use_context_aware = bool(use_context_aware)
        self.use_context_rewards = use_context_aware
        self.external_rewards = getattr(configs, 'external_rewards', None)
        
        # Pre-compute optimal actions (skip for Paper7 context-aware mode)
        # Defensive check: only pre-compute if reward_list is actually a list
        try:
            reward_list_len = len(self.reward_list) if self.reward_list is not None else 0
        except TypeError:
            reward_list_len = 0
            
        if not self.use_context_rewards and reward_list_len > 0:
            self.optimal_actions = self._compute_optimal_actions()
        else:
            self.optimal_actions = []  # Will compute dynamically if needed

        # Extract oracle path/action using ROBUST method
        self.oracle_path, self.oracle_action = self._calculate_oracle()

        # Tracking variables
        self.regret_list = []
        self.reward_list_total = []
        self.path_action_list = []
        self.total_reward = 0
        self.current_frame = 0

    # def _compute_optimal_actions(self):
    #     """Pre-compute optimal path and action for each time step"""
    #     optimal_actions = []
    #     for frame in range(self.frame_number):
    #         best_reward = -1
    #         best_path = 0
    #         best_action = 0
    #         # Check all paths
    #         for path in range(len(self.reward_list)):
    #             if self.attack_list[frame][path] > 0:  # Path not attacked
    #                 path_rewards = self.reward_list[path]
    #                 best_path_action = np.argmax(path_rewards)
    #                 path_reward = path_rewards[best_path_action] * self.attack_list[frame][path]
    #                 if path_reward > best_reward:
    #                     best_reward = path_reward
    #                     best_path = path
    #                     best_action = best_path_action
    #         optimal_actions.append((best_path, best_action, best_reward))
    #     return optimal_actions

    def _compute_optimal_actions(self):
        """
        Pre-compute optimal actions using ACTUAL data bounds.
        ✅ NOW HANDLES: NumPy arrays, lists, None attack_list, dimension mismatches
        
        Returns:
            List of (best_path, best_action, best_reward) tuples
        """
        optimal_actions = []
        
        # Defensive: Return empty if no reward data
        if not self.reward_list or len(self.reward_list) == 0:
            return []
        
        # Defensive: Handle None/missing attack_list for Paper7
        if self.attack_list is None:
            # Create synthetic all-ones attack pattern (no attacks)
            attack_list = [np.ones(len(self.reward_list)) for _ in range(min(1000, self.frame_number))]
        elif isinstance(self.attack_list, list) and len(self.attack_list) == 0:
            attack_list = [np.ones(len(self.reward_list)) for _ in range(min(1000, self.frame_number))]
        else:
            attack_list = self.attack_list
        
        # Cap iterations to prevent infinite loops
        max_frames = min(len(attack_list), 10000)
        
        for frame in range(max_frames):
            best_reward = -float('inf')
            best_path = 0
            best_action = 0
            
            # Check all available paths
            for path in range(len(self.reward_list)):
                # Defensive: Bounds check both frame and path
                if frame >= len(attack_list) or path >= len(attack_list[frame]):
                    continue
                
                # Only consider paths not attacked (convert to scalar if numpy)
                attack_value = attack_list[frame][path]
                if isinstance(attack_value, np.ndarray):
                    attack_value = attack_value.item() if attack_value.size == 1 else float(attack_value[0])
                else:
                    attack_value = float(attack_value)
                    
                if attack_value <= 0:
                    continue
                
                # Get rewards for this path (handle both list and NumPy array)
                path_rewards = self.reward_list[path]
                if isinstance(path_rewards, np.ndarray):
                    path_rewards = path_rewards.tolist()
                elif not isinstance(path_rewards, list):
                    path_rewards = list(path_rewards) if hasattr(path_rewards, '__iter__') else [path_rewards]
                
                # Find best action on this path
                if len(path_rewards) == 0:
                    continue
                
                best_path_action = path_rewards.index(max(path_rewards))
                path_reward = float(path_rewards[best_path_action]) * attack_value
                
                if path_reward > best_reward:
                    best_reward = path_reward
                    best_path = path
                    best_action = best_path_action

            optimal_actions.append((best_path, best_action, best_reward))

        return optimal_actions
    
    # def take_action(self):
    #     """Return optimal action for current frame"""
    #     if self.current_frame < len(self.optimal_actions):
    #         path, action, _ = self.optimal_actions[self.current_frame]
    #         return path, action
    #     return 0, 0
    
    def take_action(self):
        """
        Return optimal action with comprehensive bounds checking.
        Handles both pre-computed (Paper2) and dynamic (Paper7) modes.
        """
        # Paper7 dynamic mode (context-aware rewards)
        if self.use_context_rewards or len(self.optimal_actions) == 0:
            # Fallback to oracle_path/oracle_action computed at init
            return self.oracle_path, self.oracle_action
        
        # Paper2 pre-computed mode
        if self.current_frame >= len(self.optimal_actions):
            # Bounds check: return last known optimal or fallback
            if len(self.optimal_actions) > 0:
                return self.optimal_actions[-1][0], self.optimal_actions[-1][1]
            return self.oracle_path, self.oracle_action
        
        # Normal case: use pre-computed optimal action
        path, action, _ = self.optimal_actions[self.current_frame]
        return path, action

    # def update(self, path, action, reward):
    #     """Update Oracle (just tracking)"""
    #     self.total_reward += reward
    #     self.reward_list_total.append(self.total_reward)
    #     self.path_action_list.append([path, action])
    #     self.regret_list.append(0)  # Oracle has zero regret by definition
    #     self.current_frame += 1

    def update(self, path, action, reward):
        """Update with defensive frame tracking"""
        self.total_reward += reward
        self.reward_list_total.append(self.total_reward)
        self.path_action_list.append([path, action])
        self.regret_list.append(0)
        self.current_frame += 1
        
    def get_results(self):
        """Return results with metadata about actual vs expected frames"""
        return {
            'final_regret': 0,
            'regret_list': copy.deepcopy(self.regret_list),
            'final_reward': copy.deepcopy(self.total_reward),
            'reward_list': copy.deepcopy(self.reward_list_total),
            'path_action_list': copy.deepcopy(self.path_action_list),
            'state':self.state,
            'metadata': {
                'actual_frames': len(self.optimal_actions),
                'frames_processed': copy.deepcopy(self.current_frame)
            }
        }
    
    def _calculate_oracle(self):
        """
        Compute the oracle from reward_list (no attack patterns required).
        ✅ NOW HANDLES: NumPy arrays, Python lists, mixed data types
        
        Returns:
            (oracle_path, oracle_action) tuple
        """
        # Defensive: Handle empty/None reward_list
        if not self.reward_list or len(self.reward_list) == 0:
            if self.configs.verbose:
                print(f"⚠️ ORACLE DEBUG: Empty reward_list!")
            return 0, 0
        
        # Debug output for Paper7
        if self.configs.verbose or getattr(self.configs, 'use_context_rewards', False):
            print(f"📊 ORACLE._calculate_oracle() DEBUG:")
            print(f"   reward_list type: {type(self.reward_list)}")
            print(f"   reward_list length: {len(self.reward_list)}")
            if len(self.reward_list) > 0:
                first_reward = self.reward_list[0]
                print(f"   First path rewards: {first_reward}")
                print(f"   First path type: {type(first_reward)}")
                if hasattr(first_reward, '__len__'):
                    print(f"   First path length: {len(first_reward)}")
                    if len(first_reward) > 0:
                        print(f"   First action reward: {first_reward[0]}")
        
        max_graph_action = []
        oracle_graph_list = []

        for graph_index in range(len(self.reward_list)):
            path_rewards = self.reward_list[graph_index]
            
            # Convert to list if NumPy array (CRITICAL FIX for Paper7)
            if isinstance(path_rewards, np.ndarray):
                path_rewards = path_rewards.tolist()
            elif not isinstance(path_rewards, list):
                # Handle other iterables (tuples, etc.)
                try:
                    path_rewards = list(path_rewards)
                except (TypeError, ValueError):
                    # Single scalar value
                    path_rewards = [float(path_rewards)]
            
            # Safety check: empty path
            if len(path_rewards) == 0:
                max_graph_action.append(0)
                oracle_graph_list.append(0.0)
                continue
            
            # Find max reward and its action
            max_reward = max(path_rewards)
            oracle_graph_list.append(max_reward)
            max_graph_action.append(path_rewards.index(max_reward))

        # Find the path with the highest achievable reward
        if len(oracle_graph_list) == 0:
            return 0, 0
        
        oracle_path = oracle_graph_list.index(max(oracle_graph_list))
        oracle_action = max_graph_action[oracle_path]

        if self.configs.verbose:
            print("\n📊 ORACLE (REWARD-BASED) ANALYSIS:")
            print("=" * 40)
            print(f"| Paths evaluated:    | {len(oracle_graph_list):<4} |")
            print(f"| Optimal Path:       | {oracle_path:<4} |")
            print(f"| Optimal Action:     | {oracle_action:<4} |")
            print(f"| Path max rewards:   | {oracle_graph_list} |")
            print(f"| Max value:          | {max(oracle_graph_list):<4} |")
            print("=" * 40)

        return oracle_path, oracle_action


# Base Random Algorithm Class
# RandomAlg
class RandomAlg(QuantumModel):
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, K, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)
        self.K = K
    
    @property
    def model_type(self):
        return 'step-wise'

    def take_action(self):
        return np.random.choice(self.K)

# Upper Confidence Bound (UCB) Algorithm
class UCB(RandomAlg):
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, K, c=1, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, K, **kwargs)
        self.c = c
        self.T = 0
        self.q = np.zeros(K)
        self.N = np.zeros(K)

    def take_action(self):
        if self.T < self.K:
            action = self.T
        else:
            action = np.argmax(self.q + self.c * np.sqrt(2 * np.log(self.T) / self.N))
        self.T += 1
        return action

    def update(self, context, action, reward):
        self.q[action] = (self.q[action] * self.N[action] + reward) / (self.N[action] + 1)
        self.N[action] += 1

# Linear Upper Confidence Bound (LinUCB) Algorithm
class LinUCB(RandomAlg):
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, K=4, d=2, beta=1, lamb=1, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, K, **kwargs)
        
        K = len(self.X_n)  # Number of paths = 4
        d = max(self.X_n[i].shape[1] for i in range(K))  # Max feature dimension across all paths
        
        self.sigma_inv = lamb * np.eye(d)
        self.b = np.zeros((d, 1))
        self.beta = beta
        self.d = d
        self.K = K
        self.frame_counter = 0

    def _build_context_batch(self):
        """
        Build a context matrix from X_n by sampling one allocation per path.
        Returns shape (K, d) where K=4 paths
        """
        contexts = []
        for path_id in range(self.K):
            # Sample random allocation from this path
            sample_idx = np.random.randint(0, len(self.X_n[path_id]))
            ctx = self.X_n[path_id][sample_idx]  # shape (d_path,)
            contexts.append(ctx)
        
        # Pad to consistent dimension
        context = np.zeros((self.K, self.d))
        for i, ctx in enumerate(contexts):
            context[i, :len(ctx)] = ctx
        
        return context  # shape (K, d)

    def take_action(self, context=None):
        """Get context from X_n and select best action per path"""
        context = self._build_context_batch()  # shape (K, d)
        theta = self.sigma_inv @ self.b  # shape (d, 1)
        
        # UCB calculation: mu + beta * sqrt(uncertainty)
        ucb_scores = np.matmul(context, theta) + self.beta * np.sqrt(
            np.matmul(context @ self.sigma_inv, context.T).diagonal()[:, None]
        )
        
        action = int(np.argmax(ucb_scores))  # Pick best path (0-3)
        return action

    def update(self, context=None, action=0, reward=0):
        """Update beliefs after observing reward"""
        action = int(action)
        context = self._build_context_batch()  # Get fresh context
        selected_ctx = context[action]  # shape (d,)
        
        self.sherman_morrison_update(selected_ctx[:, None])
        self.b += selected_ctx[:, None] * reward
        self.frame_counter += 1

    def sherman_morrison_update(self, v):
        """Rank-1 update to inverse covariance"""
        numerator = self.sigma_inv @ v @ v.T @ self.sigma_inv
        denominator = 1 + v.T @ self.sigma_inv @ v
        self.sigma_inv = self.sigma_inv - (numerator / denominator)



class TS(RandomAlg):
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, K, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, K, **kwargs)
        self.alpha = np.ones(K)
        self.beta = np.ones(K)

    def take_action(self):
        p = np.zeros(self.K)
        for k in range(self.K):
            p[k] = beta.rvs(a=self.alpha[k], b=self.beta[k])
        return np.argmax(p)

    def update(self, context, action, reward):
        if reward == 0:
            self.alpha[action] += 1
        else:
            self.beta[action] += 1

class LinTS(RandomAlg):
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, K, d, beta=1, lamb=1, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, K, **kwargs)
        self.sigma_inv = lamb * np.eye(d)
        self.b = np.zeros((d, 1))
        self.beta = beta

    def take_action(self, context):
        theta = multivariate_normal.rvs(mean=(self.sigma_inv @ self.b).flatten(), cov=self.beta*self.sigma_inv)
        r_hat = np.matmul(theta[None], context[:, :, None])
        return np.argmax(r_hat)

    def update(self, context, action, reward):
        self.sherman_morrison_update(context[action, :, None])
        self.b += context[action, :, None] * reward

    def sherman_morrison_update(self, v):
        self.sigma_inv -= (self.sigma_inv @ v @ v.T @ self.sigma_inv) / (1 + v.T @ self.sigma_inv @ v)

# NN pieces (not themselves "environment models"; keep as-is)
class NeuralBanditModel(nn.Module):
    def __init__(self, input_size, hidden_size, out_size):
        super().__init__()
        self.affine1 = nn.Linear(input_size, hidden_size)
        self.affine2 = nn.Linear(hidden_size, out_size)

    def forward(self, x):
        x = F.relu(self.affine1(x))
        return self.affine2(x)

class ReplayBuffer:
    def __init__(self, d, capacity):
        self.buffer = {'context': np.zeros((capacity, d)), 'reward': np.zeros((capacity, 1))}
        self.capacity = capacity
        self.size = 0
        self.pointer = 0

    def add(self, context, reward):
        self.buffer['context'][self.pointer] = context
        self.buffer['reward'][self.pointer] = reward
        self.size = min(self.size + 1, self.capacity)
        self.pointer = (self.pointer + 1) % self.capacity

    def sample(self, n):
        idx = np.random.randint(0, self.size, size=n)
        return self.buffer['context'][idx], self.buffer['reward'][idx]

class NeuralTS(RandomAlg):
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, K, d, beta=1, lamb=1, hidden_size=128, lr=3e-4, reg=0.000625, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, K, **kwargs)
        self.T = 0
        self.reg = reg
        self.beta = beta
        self.net = NeuralBanditModel(d, hidden_size, 1)
        self.hidden_size = hidden_size
        self.net.to(device)
        self.optimizer = optim.Adam(self.net.parameters(), lr=lr)
        self.numel = sum(w.numel() for w in self.net.parameters() if w.requires_grad)
        self.sigma_inv = lamb * np.eye(self.numel, dtype=np.float32)
        self.device = device
        self.theta0 = torch.cat([w.flatten() for w in self.net.parameters() if w.requires_grad])
        self.replay_buffer = ReplayBuffer(d, 10000)

    def take_action(self, context):
        context = torch.tensor(context, dtype=torch.float32).to(self.device)
        g = np.zeros((self.K, self.numel), dtype=np.float32)
        for k in range(self.K):
            g[k] = self.grad(context[k]).cpu().numpy()
        with torch.no_grad():
            p = norm.rvs(
                loc=self.net(context).cpu().numpy(),
                scale=self.beta * np.sqrt(
                    np.matmul(np.matmul(g[:, None, :], self.sigma_inv), g[:, :, None])[:, 0, :]
                ),
            )
        action = np.argmax(p)
        return action

    def grad(self, x):
        y = self.net(x)
        self.optimizer.zero_grad()
        y.backward()
        return torch.cat(
            [w.grad.detach().flatten() / np.sqrt(self.hidden_size) for w in self.net.parameters() if w.requires_grad]
        ).to(self.device)

    def update(self, context, action, reward):
        context = torch.tensor(context, dtype=torch.float32).to(self.device)
        self.sherman_morrison_update(self.grad(context[action, None]).cpu().numpy()[:, None])
        self.replay_buffer.add(context[action].cpu().numpy(), reward)
        self.T += 1
        self.train()

    def sherman_morrison_update(self, v):
        self.sigma_inv -= (self.sigma_inv @ v @ v.T @ self.sigma_inv) / (1 + v.T @ self.sigma_inv @ v)

    def train(self):
        if self.T > self.K and self.T % 1 == 0:
            for _ in range(2):
                x, y = self.replay_buffer.sample(64)
                x = torch.tensor(x, dtype=torch.float32).to(self.device)
                y = torch.tensor(y, dtype=torch.float32).to(self.device).view(-1, 1)
                y_hat = self.net(x)
                loss = F.mse_loss(y_hat, y)
                loss += self.reg * torch.norm(
                    torch.cat([w.flatten() for w in self.net.parameters() if w.requires_grad]) - self.theta0
                ) ** 2
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()



class NeuralUCB(RandomAlg):
    def __init__(self, d, K, beta=1, lamb=1, hidden_size=128, lr=1e-4, reg=0.000625, capacity=24000, configs=None, X_n=[], reward_list=[], frame_number=0, attack_list=[]):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, K)
        self.T = 0
        self.reg = reg
        self.beta = beta
        self.net = NeuralBanditModel(d, hidden_size, 1)
        self.hidden_size = hidden_size
        self.net.to(device)
        self.optimizer = optim.Adam(self.net.parameters(), lr=lr)
        self.numel = sum(w.numel() for w in self.net.parameters() if w.requires_grad)
        self.sigma_inv = lamb * np.eye(self.numel, dtype=np.float32)
        self.device = device
        # self.capacity = capacity*2
        self.theta0 = torch.cat([w.flatten() for w in self.net.parameters() if w.requires_grad])
        self.replay_buffer = ReplayBuffer(d, self.capacity)

    def take_action(self, context):
        context = torch.tensor(context, dtype=torch.float32).to(self.device)
        g = np.zeros((self.K, self.numel), dtype=np.float32)
        for k in range(self.K):
            g[k] = self.grad(context[k]).cpu().numpy()
        with torch.no_grad():
            p = self.net(context).cpu().numpy() + self.beta * np.sqrt(
                np.matmul(np.matmul(g[:, None, :], self.sigma_inv), g[:, :, None])[:, 0, :]
            )
        # Clamp to ensure non-negative values for probability calculations
        p = np.maximum(p, 0.0)
        action = np.argmax(p)
        return action

    def grad(self, x):
        y = self.net(x)
        self.optimizer.zero_grad()
        y.backward()
        return torch.cat(
            [w.grad.detach().flatten() / np.sqrt(self.hidden_size) for w in self.net.parameters() if w.requires_grad]
        ).to(self.device)

    def update(self, context, action, reward):
        context = torch.tensor(context, dtype=torch.float32).to(self.device)
        self.sherman_morrison_update(self.grad(context[action, None]).cpu().numpy()[:, None])
        self.replay_buffer.add(context[action].cpu().numpy(), reward)
        self.T += 1
        self.train()

    def sherman_morrison_update(self, v):
        self.sigma_inv -= (self.sigma_inv @ v @ v.T @ self.sigma_inv) / (1 + v.T @ self.sigma_inv @ v)

    def train(self):
        if self.T > self.K and self.T % 1 == 0:
            for _ in range(2):
                x, y = self.replay_buffer.sample(64)
                x = torch.tensor(x, dtype=torch.float32).to(self.device)
                y = torch.tensor(y, dtype=torch.float32).to(self.device).view(-1, 1)
                y_hat = self.net(x)
                loss = F.mse_loss(y_hat, y)
                loss += self.reg * torch.norm(
                    torch.cat([w.flatten() for w in self.net.parameters() if w.requires_grad]) - self.theta0
                ) ** 2
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

    def __eq__(self, other):
        """Defines equality for model comparison or saved dict comparison."""

        # --- dict comparison (used in resume) ---
        if isinstance(other, dict):
            other_attrs = other.get("key_attrs", {}).copy()
            # 🔹 Ignore keys for reusable models (shared across attacks & envs)
            ignore_keys = {"actk_type", "attack", "env_type", "runs"}
            filtered_other_attrs = {k: v for k, v in other_attrs.items() if k not in ignore_keys}
            filtered_self_attrs = {k: v for k, v in self.key_attrs.items() if k not in ignore_keys}

            # ⚙️ Drop env & attack only for reusable models
            skip_env_attack = isinstance(self, NeuralUCB)

            if (
                self.id == other.get("id") and
                self.frame_number == other.get("frame_number") and
                self.num_groups == other.get("num_groups") and
                self.capacity == other.get("capacity") and
                # getattr(self, 'mode', None) == other.get("mode") and
                self.allocator_id == other.get("allocator_id") and
                (skip_env_attack or self.env_id == other.get("env_id")) and
                (skip_env_attack or self.attack_id == other.get("attack_id")) and
                filtered_self_attrs == filtered_other_attrs
            ):
                return True

            # 🔍 Debug output if no match
            # print(f"\n❌ Model comparison failed:")
            # print(f"  Class: {self.id} vs {other.get('id')}")
            # print(f"  Frames: {self.frame_number} vs {other.get('frame_number')}")
            # print(f"  Groups: {self.num_groups} vs {other.get('num_groups')}")
            # print(f"  Capacity: {self.capacity} vs {other.get('capacity')}")
            # # print(f"  Mode: {getattr(self, 'mode', None)} vs {other.get('mode')}")
            # print(f"  Allocator: {self.allocator_id} vs {other.get('allocator_id')}")
            if not skip_env_attack:
                print(f"  Environment: {self.env_id} vs {other.get('env_id')}")
                print(f"  Attack: {self.attack_id} vs {other.get('attack_id')}")
            # print(f"  Filtered Current attrs:\n{json.dumps(filtered_self_attrs, indent=2)}")
            # print(f"  Filtered Loaded attrs:\n{json.dumps(filtered_other_attrs, indent=2)}")
            return False

        # --- model instance comparison ---
        if not isinstance(other, self.__class__):
            return NotImplemented

        skip_env_attack = isinstance(self, NeuralUCB)

        return (
            self.frame_number == getattr(other, "frame_number", None) and
            self.num_groups == getattr(other, "num_groups", None) and
            self.capacity == getattr(other, "capacity", None) and
            getattr(self, 'mode', None) == getattr(other, "mode", None) and
            self.allocator_id == getattr(other, "allocator_id", None) and
            (skip_env_attack or self.env_id == getattr(other, "env_id", None)) and
            (skip_env_attack or self.attack_id == getattr(other, "attack_id", None)) and
            self.key_attrs == getattr(other, "key_attrs", None)
        )

