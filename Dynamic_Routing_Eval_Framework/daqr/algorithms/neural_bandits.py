import os
import math
import time
import copy
import psutil
import random
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
from scipy.stats import beta, multivariate_normal, norm
from daqr.algorithms.base_bandit import *


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
# print(f"PyTorch version: {torch.__version__}")
# print(f"NumPy version: {np.__version__}")
# print(f"Using device: {device}")

# =============================================================================
# Enhanced Common Interface for All Models
# =============================================================================




class EXPNeuralUCB(QuantumModel):
    """
    Enhanced Unified Quantum Routing Algorithm Framework
    
    Modes:
    - 'hybrid': EXP3 + Neural UCB (Main algorithm - EXPNeuralUCB)
    - 'neural': Neural UCB + Simple group selection (GNeuralUCB equivalent)  
    - 'exp3': EXP3 + Linear UCB (EXPUCB equivalent)
    """
    
    @property
    def model_type(self):
        return 'batch'
    
    @property
    def supports_batch_execution(self):
        return True  # Override detection since we implement run
    
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, mode='hybrid', beta=0.2, gamma_factor=0.01, eta_factor=0.05, verbose=False):
        super().__init__(configs,  X_n, reward_list, frame_number, attack_list, capacity, mode, beta, gamma_factor, eta_factor)
        # Core parameters (shared across all modes)
        self.verbose = verbose
        
        # Shared tracking variables
        self.neuralucb_list = []
        self.regret_list = []
        self.reward_list_total = []
        self.path_action_list = []
        self.total_reward = 0
        self.regret = 0
        
        if self.state != 1: 
            # Calculate oracle (shared across all modes)
            self.oracle_path, self.oracle_action = self._get_oracle()
            # Mode-specific initialization
            self._initialize_mode_specific_components()
        
        if  self.verbose:
            print(f"\n\t{self} initialized in '{mode}' mode")
            self._print_mode_description()

        self.thresholds = {
                'EXPNeuralUCB': {'stochastic': 0.628, 'adversarial': 0.598},
                'CPursuitNeuralUCB': {'stochastic': 0.634, 'adversarial': 0.614},
                'GNeuralUCB': {'stochastic': 0.582, 'adversarial': 0.509},  # Added; higher stochastic for grouping
                'iCPursuitNeuralUCB': {'stochastic': 0.712, 'adversarial': 0.689}
            }
        
        # self.apply_testbed_configs()

        

    def set_capacity(self, capacity):
        self.capacity = capacity

    def _get_min_efficiency(self, model_name, env_type='stochastic') -> float:
        """Return expected minimum reward thresholds for retry decisions"""
        if model_name not in self.thresholds:
            return 0.5

        # Always retry 0% (return 0.0 if not in dict or as fallback)
        return self.thresholds[model_name].get(env_type, 0.50)  # Fallback 50%
    
    def take_action(self, *args, **kwargs):
        raise NotImplementedError(
            f"EXPNeuralUCB is a {self.model_type} model that manages actions internally. "
            f"Use run(attack_list) to execute a full experiment, not take_action()."
        )

    def _initialize_mode_specific_components(self):
        """Initialize components based on selected mode"""
        # Neural UCB components (hybrid + neural modes)
        # if self.mode in ['hybrid', 'neural']:
        self.neuralucb_list = []

        # Loop through each path and initialize a NeuralUCB instance with current (baseline) dimension logic
        for i, path_context in enumerate(self.X_n):
            # model = NeuralUCB(
            #     2 if i < 2 else 3,             # 2D for first 2 paths, 3D for others
            input_dim = len(path_context[0])  # ← ACTUAL CONTEXT DIMENSION
            # print(f"Path {i}: context shape {input_dim}")  # DEBUG PRINT
            model = NeuralUCB(
                input_dim,  # ← FIX: Use real dimension
                len(path_context),             # Current baseline logic
                self.beta,
                lamb=1,
                capacity=self.capacity,
                configs=self.configs,
                X_n=self.X_n,
                reward_list=self.reward_list,
                frame_number=self.frame_number,
                attack_list=self.attack_list
            )
            model.set_id(f"{model.id}_{i}")
            
            try: 
                if not self.configs.can_resume(self) and not self.resumed: model.resume()
            except Exception as e: print(f"[RESUME SKIPPED] {model.id}: {e}")
            self.neuralucb_list.append(model)
        
        # EXP3 components (hybrid + exp3 modes)
        if self.mode in ['hybrid', 'exp3']:
            self.estimate_group_reward = []
            for _ in range(self.num_groups):
                self.estimate_group_reward.append([0])
            self.prob_list = []
        
        # Simple group selection components (neural mode)
        if self.mode == 'neural':
            self.group_rewards = [0.0] * self.num_groups
            self.group_counts = [1] * self.num_groups  # Avoid division by zero
        
        # Linear UCB components (exp3 mode)
        if self.mode == 'exp3':
            self.linear_ucb_list = []
            for i in range(self.num_groups):
                self.linear_ucb_list.append({
                    'counts': [1] * len(self.reward_list[i]),
                    'rewards': [0.0] * len(self.reward_list[i])
                })

    def _print_mode_description(self):
        if not self.verbose: return
        print("\n" + "=" * 60)
        print("ALGORITHM CONFIGURATION")
        print("=" * 60)
        # same tabular output as before...
        if self.mode == 'hybrid':
            print("| Component          | Method                    | Properties       |")
            print("|--------------------|-----------------------------|------------------|")
            print("| Group Selection    | EXP3                       | Adversarially    |")
            print("| Action Selection   | Neural UCB                 | Nonlinear        |")
            print("| Parameters         | gamma={:.3f}, eta={:.3f}   |".format(self.gamma, self.eta))
            print("|                    | beta={:.1f}                |".format(self.beta))
        elif self.mode == 'neural':
            print("| Group Selection    | Simple UCB                 | Non-Adversarial  |")
            print("| Action Selection   | Neural UCB                 | Nonlinear        |")
            print("| Parameters         | beta={:.1f}                |".format(self.beta))
        elif self.mode == 'exp3':
            print("| Group Selection    | EXP3                       | Adversarially    |")
            print("| Action Selection   | Linear UCB                 | Linear           |")
            print("| Parameters         | gamma={:.3f}, eta={:.3f}   |".format(self.gamma, self.eta))
        print("=" * 60)

    def _calculate_oracle(self):
        """Calculate oracle with clean output"""
        max_graph_action = []
        oracle_graph_list = []
        for graph_index in range(self.num_groups):
            max_reward = max(self.reward_list[graph_index])
            oracle_graph_list.append(max_reward)
            max_graph_action.append(self.reward_list[graph_index].index(max_reward))
        oracle_path = oracle_graph_list.index(max(oracle_graph_list))
        oracle_action = max_graph_action[oracle_path]
        
        if self.verbose:
            print("\nORACLE ANALYSIS:")
            print("=" * 40)
            print(f"| Optimal Path:      | {oracle_path:<4} |")
            print(f"| Optimal Action:    | {oracle_action:<4} |")
            print(f"| Path Performance:  | {oracle_graph_list} |")
            print("=" * 40)
        
        return oracle_path, oracle_action


    def _get_oracle(self, base_model="Oracle"):
        """
        Get oracle path/action from experiment runner's Oracle instance or saved state.
        Oracle must be run first, so this should always succeed.
        """
        oracle_model = None

        # Method 1: Use base_model directly from configs (preferred)
        if isinstance(self.configs.base_model, Oracle):
            oracle_model = self.configs.base_model
            print(f"\t✓ {base_model} model loaded from configs: {oracle_model}")

        # Method 2: Try to resume from saved state (with better error reporting)
        if oracle_model is None:
            try:
                self.configs.overwrite = True
                oracle_model = Oracle(
                    configs=self.configs,
                    X_n=self.X_n,
                    reward_list=self.reward_list,
                    frame_number=self.frame_number,
                    attack_list=self.attack_list,
                    capacity=self.capacity
                )
                # FIX: Keep instance even if resume fails (it's still valid)
                if oracle_model.resume(): 
                    print(f"\t✓ {base_model} model resumed from saved state.")
                # else: oracle_model stays valid - optimal_actions already computed!
                self.configs.overwrite = self.overwrite
                
            except Exception as e:
                print(f"\t⚠️ Oracle creation failed (non-fatal): {e}")
                print(f"\t   attack_list[0] shape: {len(self.attack_list[0])}, paths: {len(self.reward_list)}")
                oracle_model = None  # Graceful fallback preserved

        # Extract first optimal decision from Oracle model
        if oracle_model and len(oracle_model.optimal_actions) > 0:
            oracle_path, oracle_action = oracle_model.optimal_actions[0][:2]
            if self.verbose:
                print(f"\n{base_model.upper()} DECISION (Frame 0):")
                print("=" * 40)
                print(f"| Optimal Path:      | {oracle_path:<4} |")
                print(f"| Optimal Action:    | {oracle_action:<4} |")
                print("=" * 40)
            return oracle_path, oracle_action

        # Fallback: Estimate manually (less precise)
        print(f"\t⚠️  {base_model} model not found, using manual fallback...")
        return self._calculate_oracle()


    def select_group(self, frame):
        if self.mode in ['hybrid', 'exp3']:
            return self._select_group_exp3(frame)
        else:
            return self._select_group_simple(frame)

    def _select_group_exp3(self, frame):
        prob_array = self._calculate_group_probabilities()
        self.prob_list.append(prob_array.copy())
        allocation_array = list(range(self.num_groups))
        selected_path = np.random.choice(allocation_array, p=prob_array)
        return selected_path, prob_array

    def _select_group_simple(self, frame):
        group_values = []
        for i in range(self.num_groups):
            avg_reward = self.group_rewards[i] / self.group_counts[i]
            confidence = np.sqrt(2 * np.log(frame + 1) / self.group_counts[i])
            group_values.append(avg_reward + self.beta * confidence)
        return np.argmax(group_values), None

    def _calculate_group_probabilities(self):
        prob_array = []
        sum_group = 0
        
        # Safely compute exponentials with overflow protection
        max_exponent = -np.inf
        exponents = []
        
        for group_index in range(self.num_groups):
            # Compute reward sum
            reward_sum = sum(self.estimate_group_reward[group_index])
            exponent = self.eta * reward_sum
            exponents.append(exponent)
            max_exponent = max(max_exponent, exponent)
        
        # Use log-sum-exp trick to avoid numerical overflow/underflow
        # Normalize by the max exponent
        try:
            for exp_val in exponents:
                sum_group += math.exp(exp_val - max_exponent)
            
            for exp_val in exponents:
                p = (self.gamma / self.num_groups +
                     (1 - self.gamma) * math.exp(exp_val - max_exponent) / max(sum_group, 1e-10))
                # Clamp probability to valid range [0, 1]
                p = max(0.0, min(1.0, p))
                prob_array.append(p)
        except (OverflowError, ValueError) as e:
            # Fallback to uniform distribution if numerical issues occur
            uniform_prob = 1.0 / self.num_groups
            prob_array = [uniform_prob] * self.num_groups
        
        # Normalize to ensure probabilities sum to 1
        prob_sum = sum(prob_array)
        if prob_sum > 0:
            prob_array = [p / prob_sum for p in prob_array]
        else:
            prob_array = [1.0 / self.num_groups] * self.num_groups
        
        return np.array(prob_array)

    def select_action(self, selected_group):
        if self.mode in ['hybrid', 'neural']:
            return self.neuralucb_list[selected_group].take_action(self.X_n[selected_group])
        else:
            return self._select_action_linear(selected_group)

    def _select_action_linear(self, selected_group):
        action_values = []
        total_group_count = sum(self.linear_ucb_list[selected_group]['counts'])
        for action in range(len(self.reward_list[selected_group])):
            count = self.linear_ucb_list[selected_group]['counts'][action]
            avg_reward = self.linear_ucb_list[selected_group]['rewards'][action] / count
            confidence = np.sqrt(2 * np.log(total_group_count) / count)
            action_values.append(avg_reward + self.beta * confidence)
        return np.argmax(action_values)

    def update_algorithms(self, selected_path, selected_action, base_reward, attack_list, frame):
        if attack_list[frame][selected_path] > 0:
            if self.mode in ['hybrid', 'neural']:
                self.neuralucb_list[selected_path].update(
                    self.X_n[selected_path], selected_action, base_reward
                )
            elif self.mode == 'exp3':
                self.linear_ucb_list[selected_path]['counts'][selected_action] += 1
                self.linear_ucb_list[selected_path]['rewards'][selected_action] += base_reward

    def update_group_selection(self, selected_path, observed_reward, prob_array=None):
        if self.mode in ['hybrid', 'exp3']:
            for group_index in range(self.num_groups):
                if group_index == selected_path:
                    safe_p = max(float(prob_array[selected_path]), 1e-12)
                    self.estimate_group_reward[group_index].append(observed_reward / safe_p)
                else:
                    self.estimate_group_reward[group_index].append(0)
        elif self.mode == 'neural':
            self.group_rewards[selected_path] += observed_reward
            self.group_counts[selected_path] += 1

    def run(self, attack_list, verbose=None):
        """Enhanced batch/episode runner with clean progress output"""
        if verbose is None: verbose = self.verbose
        
        # Try to resume from saved state
        if self.overwrite or (not self.resumed and self.resume()):
            if verbose: print(f"\n\t✓ {self}: Resuming from saved state - skipping execution")
            return  True

        start_time = time.time()
        
        if verbose:
            print(f"\nEXECUTION STARTING:")
            print("=" * 50)
            print(f"| Mode:    | {self.mode.upper():<10} | Frames: {self.frame_number:<6} | Paths: {self.num_groups} |")
            print("=" * 50)

        # FIX: Add disable parameter
        for frame in tqdm(range(self.frame_number), desc=f"- {self.mode.upper()} Progress", disable=not verbose):  # Now respects verbose parameter
        
            if self.transition_trigger and frame > 0 and frame % self.transition_interval == 0:
                new_contexts, new_rewards = self.transition_trigger()
                if new_contexts is not None:
                    self.X_n = new_contexts
                    self.reward_list = new_rewards            
            
            selected_path, prob_array = self.select_group(frame)
            selected_action = self.select_action(selected_path)
            self.path_action_list.append([selected_path, selected_action])
            
            base_reward = self.reward_list[selected_path][selected_action]
            # Clamp reward to [0, 1] for probability usage (Paper7 has rewards > 1.0)
            base_reward_prob = np.clip(base_reward, 0.0, 1.0)
            d_t = np.random.choice([0, 1], p=[1 - base_reward_prob, base_reward_prob])
            dt = d_t * attack_list[frame][selected_path]
            observed_reward = base_reward * attack_list[frame][selected_path]
            
            self.update_algorithms(selected_path, selected_action, base_reward, attack_list, frame)
            self.update_group_selection(selected_path, dt, prob_array)
            
            oracle_reward = (self.reward_list[self.oracle_path][self.oracle_action] *
                            attack_list[frame][self.oracle_path])
            oracle_regret = oracle_reward - observed_reward
            if oracle_regret < 0:
                oracle_regret = 0
            
            self.regret += np.abs(oracle_regret)
            self.total_reward += observed_reward
            
            self.regret_list.append(self.regret)
            self.reward_list_total.append(self.total_reward)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        if verbose: self._print_experiment_results(elapsed_time)
        if self.overwrite: self.save()

    def _print_experiment_results(self, elapsed_time):
        """Clean tabular results output"""
        if not self.verbose: return
        print(f"\nEXECUTION COMPLETED:")
        print("=" * 50)
        print(f"| Execution Time:   | {elapsed_time:.2f} sec |")
        print(f"| Final Regret:     | {self.regret:.2f} |")
        print(f"| Final Reward:     | {self.total_reward:.2f} |")
        mem = psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2
        print(f"| Memory Usage:     | {mem:.2f} MB |")
        print("=" * 50)

    def get_results(self):
        results = {
            'regret_list': copy.deepcopy(self.regret_list),
            'reward_list': copy.deepcopy(self.reward_list_total),
            'path_action_list': copy.deepcopy(self.path_action_list),
            'final_regret': copy.deepcopy(self.regret),
            'final_reward': copy.deepcopy(self.total_reward),
            'oracle_path': copy.deepcopy(self.oracle_path),
            'oracle_action': copy.deepcopy(self.oracle_action),
            'mode': copy.deepcopy(self.mode)
        }
        if self.mode in ['hybrid', 'exp3']:
            results['prob_list'] = copy.deepcopy(self.prob_list)
        return results
    
    def cleanup(self, verbose=False):
        """Override for EXP-specific cleanup"""
        if verbose is None: verbose = self.verbose
        # Custom cleanup
        if hasattr(self, 'prob_list'):
            del self.prob_list
        
        # Call parent cleanup
        super().cleanup(verbose)

    def save(self):
        """Save EXPNeuralUCB model + all associated NeuralUCB submodels."""
        # 1) Save EXPNeuralUCB itself
        try:
            super().save()
            if self.verbose:    print(f"\tSaved EXPNeuralUCB main model: {self.file_name}")
        except Exception as e:  print(f"⚠️ Could not save main EXPNeuralUCB model: {e}")

        # 2) Save each NeuralUCB instance
        if not hasattr(self, "neuralucb_list"): return True

        for i, neu_model in enumerate(self.neuralucb_list):
            try:
                neu_model.save()
                if self.verbose:    print(f"\tSaved NeuralUCB[{i}] → {neu_model.file_name}")
            except Exception as e:  print(f"\t⚠️ Could not save NeuralUCB[{i}]: {e}")
        return True



class EXPUCB(EXPNeuralUCB):
    """
    Wrapper for the 'exp3' variant using EXPNeuralUCB internals with EXP3 group selection
    and Linear-UCB action selection.
    """
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, mode='exp3', beta=0.2, gamma_factor=0.1, eta_factor=0.005, **kwargs):
        super().__init__(
            configs=configs,
            X_n=X_n,
            reward_list=reward_list,
            frame_number=frame_number,
            attack_list=attack_list,
            capacity=capacity,
            mode=mode,          # enforce correct variant
            beta=beta,
            gamma_factor=gamma_factor,
            eta_factor=eta_factor,
            **kwargs
        )


class GNeuralUCB(EXPNeuralUCB):
    """
    Wrapper for the 'neural' variant using EXPNeuralUCB internals with Simple-UCB group selection
    and NeuralUCB action selection.
    """
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, mode='neural', beta=0.2, **kwargs):
        super().__init__(
            configs=configs,
            X_n=X_n,
            reward_list=reward_list,
            frame_number=frame_number,
            attack_list=attack_list,
            capacity=capacity,
            mode=mode,          # enforce correct variant
            beta=beta,
            **kwargs
        )