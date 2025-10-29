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
print(f"PyTorch version: {torch.__version__}")
print(f"NumPy version: {np.__version__}")
print(f"Using device: {device}")

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
    
    def __init__(self, X_n, reward_list, frame_number, mode='hybrid', 
                 gamma_factor=0.01, eta_factor=0.05, beta=0.2, verbose=True, capacity=24000):
        # Core parameters (shared across all modes)
        self.X_n = X_n
        self.reward_list = reward_list
        self.frame_number = frame_number
        self.num_groups = len(reward_list)
        self.mode = mode
        self.beta = beta
        self.verbose = verbose
        
        # EXP3 parameters (used in 'hybrid' and 'exp3' modes)
        self.gamma = gamma_factor
        self.eta = eta_factor
        
        # Shared tracking variables
        self.regret_list = []
        self.reward_list_total = []
        self.path_action_list = []
        self.regret = 0
        self.total_reward = 0
        
        self.capacity = capacity
        # Calculate oracle (shared across all modes)
        self.oracle_path, self.oracle_action = self._calculate_oracle()
        
        # Mode-specific initialization
        self._initialize_mode_specific_components()
        
        if  self.verbose:
            print(f"\nEXPNeuralUCB initialized in '{mode}' mode")
            self._print_mode_description()

        self.thresholds = {
                'EXPNeuralUCB': {'stochastic': 0.628, 'adversarial': 0.598},
                'CPursuitNeuralUCB': {'stochastic': 0.634, 'adversarial': 0.614},
                'GNeuralUCB': {'stochastic': 0.582, 'adversarial': 0.509},  # Added; higher stochastic for grouping
                'iCPursuitNeuralUCB': {'stochastic': 0.712, 'adversarial': 0.689}
            }
        

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
        if self.mode in ['hybrid', 'neural']:
            self.neuralucb_list = []
            cap = self.capacity
            self.neuralucb_list.append(NeuralUCB(2, len(self.X_n[0]), self.beta, lamb=1, capacity=cap)) # P1:2D
            self.neuralucb_list.append(NeuralUCB(2, len(self.X_n[1]), self.beta, lamb=1, capacity=cap)) # P2:2D
            self.neuralucb_list.append(NeuralUCB(3, len(self.X_n[2]), self.beta, lamb=1, capacity=cap)) # P3:3D
            self.neuralucb_list.append(NeuralUCB(3, len(self.X_n[3]), self.beta, lamb=1, capacity=cap)) # P4:3D
        
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
        for group_index in range(self.num_groups):
            sum_group += math.exp(self.eta * sum(self.estimate_group_reward[group_index]))
        for group_index in range(self.num_groups):
            p = (self.gamma / self.num_groups +
                 (1 - self.gamma) * math.exp(self.eta * sum(self.estimate_group_reward[group_index])) / sum_group)
            prob_array.append(p)
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
        start_time = time.time()
        
        if verbose:
            print(f"\nEXECUTION STARTING:")
            print("=" * 50)
            print(f"| Mode:    | {self.mode.upper():<10} | Frames: {self.frame_number:<6} | Paths: {self.num_groups} |")
            print("=" * 50)

        
        for frame in tqdm(range(self.frame_number), desc=f"- {self.mode.upper()} Progress"):
            selected_path, prob_array = self.select_group(frame)
            selected_action = self.select_action(selected_path)
            self.path_action_list.append([selected_path, selected_action])
            
            base_reward = self.reward_list[selected_path][selected_action]
            d_t = np.random.choice([0, 1], p=[1 - base_reward, base_reward])
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
        
        if verbose:
            self._print_experiment_results(elapsed_time)

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






class EXPUCB(EXPNeuralUCB):
    """
    Wrapper for the 'exp3' variant using EXPNeuralUCB internals with EXP3 group selection
    and Linear-UCB action selection.
    """
    def __init__(self, X_n, reward_list, frame_number,
                 gamma_factor=0.1, mode='exp3', eta_factor=0.005, beta=0.2, **kwargs):
        super().__init__(
            X_n=X_n,
            reward_list=reward_list,
            frame_number=frame_number,
            mode=mode,            # enforce correct variant
            gamma_factor=gamma_factor,
            eta_factor=eta_factor,
            beta=beta,
            **kwargs
        )


class GNeuralUCB(EXPNeuralUCB):
    """
    Wrapper for the 'neural' variant using EXPNeuralUCB internals with Simple-UCB group selection
    and NeuralUCB action selection.
    """
    def __init__(self, X_n, reward_list, frame_number, mode='neural', beta=0.2, **kwargs):
        super().__init__(
            X_n=X_n,
            reward_list=reward_list,
            frame_number=frame_number,
            mode=mode,          # enforce correct variant
            beta=beta,
            **kwargs
        )