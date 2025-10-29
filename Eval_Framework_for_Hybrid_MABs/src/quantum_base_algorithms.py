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
    def __init__(self):
        super().__init__()
        self.thresholds = {
                'EXPNeuralUCB': {'stochastic': 0.628, 'adversarial': 0.598},
                'CPursuitNeuralUCB': {'stochastic': 0.634, 'adversarial': 0.614},
                'GNeuralUCB': {'stochastic': 0.582, 'adversarial': 0.509},  # Added; higher stochastic for grouping
                'iCPursuitNeuralUCB': {'stochastic': 0.712, 'adversarial': 0.689}
            }

    def get_cleanup_wait_time(self, frame_count=1000, cooldown_base=3, cooldown_scale_factor=1, cooldown_max=15):
        """
        Calculate frame-scaled cleanup wait time.
        
        Args:
            frame_count: Number of frames (if None, uses self.frame_count)
        
        Returns:
            float: Wait time in seconds
        """

        # Frame-scaled timing formula
        scale = (frame_count / 1000.0) * cooldown_scale_factor
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
        if hasattr(self, 'neural_net'):
            del self.neural_net
            cleanup_items.append("neural_net")
        if hasattr(self, 'optimizer'):
            del self.optimizer
            cleanup_items.append("optimizer")
        if hasattr(self, 'net'):
            del self.net
            cleanup_items.append("net")
        
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
            import torch
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
        if verbose: print(f"✓ {self.__class__.__name__} cleaned: {', '.join(cleanup_items)}")

    def __del__(self):
        """Destructor to ensure cleanup on deletion."""
        try:
            self.cleanup(verbose=False)
        except Exception as e:
            print(f"Warning: Cleanup in destructor failed: {e}")


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
    
    def __init__(self, X_n, reward_list, attack_list):
        self.X_n = X_n
        self.reward_list = reward_list
        self.attack_list = attack_list
        self.frame_number = len(attack_list)
        # Pre-compute optimal actions for each time step
        self.optimal_actions = self._compute_optimal_actions()
        # Tracking variables
        self.regret_list = []
        self.reward_list_total = []
        self.path_action_list = []
        self.total_reward = 0
        self.current_frame = 0

    def _compute_optimal_actions(self):
        """Pre-compute optimal path and action for each time step"""
        optimal_actions = []
        for frame in range(self.frame_number):
            best_reward = -1
            best_path = 0
            best_action = 0
            # Check all paths
            for path in range(len(self.reward_list)):
                if self.attack_list[frame][path] > 0:  # Path not attacked
                    path_rewards = self.reward_list[path]
                    best_path_action = np.argmax(path_rewards)
                    path_reward = path_rewards[best_path_action] * self.attack_list[frame][path]
                    if path_reward > best_reward:
                        best_reward = path_reward
                        best_path = path
                        best_action = best_path_action
            optimal_actions.append((best_path, best_action, best_reward))
        return optimal_actions

    def take_action(self):
        """Return optimal action for current frame"""
        if self.current_frame < len(self.optimal_actions):
            path, action, _ = self.optimal_actions[self.current_frame]
            return path, action
        return 0, 0

    def update(self, path, action, reward):
        """Update Oracle (just tracking)"""
        self.total_reward += reward
        self.reward_list_total.append(self.total_reward)
        self.path_action_list.append([path, action])
        self.regret_list.append(0)  # Oracle has zero regret by definition
        self.current_frame += 1

    def get_results(self):
        return {
            'final_regret': 0,
            'regret_list': copy.deepcopy(self.regret_list),
            'final_reward': copy.deepcopy(self.total_reward),
            'reward_list': copy.deepcopy(self.reward_list_total),
            'path_action_list': copy.deepcopy(self.path_action_list)
        }

# Base Random Algorithm Class
class RandomAlg(QuantumModel):
    @property
    def model_type(self):
        return 'step-wise'
    
    def __init__(self, K):
        self.K = K

    def take_action(self):
        return np.random.choice(self.K)

# Upper Confidence Bound (UCB) Algorithm
class UCB(RandomAlg):
    def __init__(self, K, c=1):
        super().__init__(K)
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
    def __init__(self, d, K, beta=1, lamb=1):
        super().__init__(K)
        self.sigma_inv = lamb * np.eye(d)
        self.b = np.zeros((d, 1))
        self.beta = beta

    def take_action(self, context):
        theta = self.sigma_inv @ self.b
        p = np.matmul(context[:, None, :], theta) + self.beta * np.sqrt(
            np.matmul(np.matmul(context[:, None, :], self.sigma_inv), context[:, :, None]))
        action = np.argmax(p)
        return action

    def update(self, context, action, reward):
        self.sherman_morrison_update(context[action, :, None])
        self.b += context[action, :, None] * reward

    def sherman_morrison_update(self, v):
        self.sigma_inv -= (self.sigma_inv @ v @ v.T @ self.sigma_inv) / (1 + v.T @ self.sigma_inv @ v)

class TS(RandomAlg):
    def __init__(self, K):
        super().__init__(K)
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
    def __init__(self, d, K, beta=1, lamb=1):
        super().__init__(K)
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
    def __init__(self, d, K, beta=1, lamb=1, hidden_size=128, lr=3e-4, reg=0.000625):
        super().__init__(K)
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
    def __init__(self, d, K, beta=1, lamb=1, hidden_size=128, lr=1e-4, reg=0.000625):
        super().__init__(K)
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
            p = self.net(context).cpu().numpy() + self.beta * np.sqrt(
                np.matmul(np.matmul(g[:, None, :], self.sigma_inv), g[:, :, None])[:, 0, :]
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